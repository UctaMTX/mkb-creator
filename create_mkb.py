#!/usr/bin/env python3
#
# (C) 2001-2012 Marmalade. All Rights Reserved.
#
# (C) 2024 cronium Inc.
# Adapted for Python 3 by cronium
#
# This document is protected by copyright, and contains information
# proprietary to Marmalade.
#
# This file consists of source code released by Marmalade under
# the terms of the accompanying End User License Agreement (EULA).
# Please do not use this program/source code before you have read the
# EULA and have agreed to be bound by its terms.
#
'''
This is a tool for creating new MKB project files. It
can take as its input a source tree, an .sln project file
or a .dsp project file.

The output is an mkb file with the same name of as
the file or directory operated on.
'''

import os
import sys
import stat
import re
from optparse import OptionParser

includepaths = {}

keywords = ["define", "test", "file", "subproject", "option"]

def run():
    print("MKB Project Creator")
    print("Copyright (C) 2006-2012 Ideaworks3D, Ltd.")

    parser = OptionParser() # usage="%prog [options] mkb_file", version="%%prog %s" % __version__)
    parser.add_option("-l", "--lib", action="store_true", dest="lib", help="build a library mkb")

    options, args = parser.parse_args()

    root = '.'
    if args:
        root = args[0]

    name = os.path.abspath(root)
    basename = os.path.splitext(os.path.basename(name))[0]

    if len(args) > 1:
        basename = args[1]

    # Are we processing an SLN file or a directory tree?
    if os.path.splitext(root)[1].lower() == '.sln':
        # Get the files from within the SLN
        parsing_sln = True
        # Replace the SLN with MKB
        filename = os.path.splitext(name)[0] + ".mkb"
    else:
        # Traverse the directory tree for the file list
        parsing_sln = False
        # Add .mkb to the directory name
        filename = os.path.join(name, basename + ".mkb")

    if os.path.exists(filename):
        print(f"ERROR: target mkb already exists: {filename}")
        sys.exit(1)

    print(f"Writing mkb file: {filename}")

    with open(filename, 'w') as outfile:
        outfile.write(f'''\
#!/usr/bin/env mkb
# Automatically generated by '{' '.join(sys.argv)}'
''')

        if options.lib:
            outfile.write('''\

platform S3E_LIB
''')
            if basename.startswith("lib"):
                outfile.write(f'''\
target "{basename[:3]}"
''')

        outfile.write('''\

files
{
''')

        if parsing_sln:
            parse_sln(root, name, outfile)
        else:
            traverse_directories(root, name, outfile)

        outfile.write('}\n')

        outfile.write('''
subproject iwutil

includepath .

\n''')

        paths = sorted(includepaths.keys())
        for inc in paths:
            outfile.write(f'includepath {os.path.normpath(inc)}\n')

    mode = os.stat(filename).st_mode
    os.chmod(filename, mode | stat.S_IEXEC)


# Make an mkb just by looking for c, cpp and h files in all directories
def traverse_directories(root, name, outfile):
    extensions = ['.h', '.cpp', '.hpp', '.c', '.cc', '.inl', '.m', '.mm', '.S']
    olddir = os.getcwd()
    os.chdir(root)

    for root, dirs, files in os.walk("."):
        first = True
        files.sort()

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in extensions:
                if first:
                    dirname = os.path.normpath(root).replace("\\", "/")
                    if not os.path.normpath(root) == ".":
                        outfile.write(f'\t["{dirname}"]\n')
                    parts = dirname.split('/')
                    for keyword in keywords:
                        if keyword in parts or keyword + 's' in parts:
                            dirname = f'"{dirname}"'
                            break
                    outfile.write(f"\t({dirname})\n")
                    first = False
                quote = any(not c.isalnum() and c not in ['_', '-'] for c in os.path.splitext(file)[0])
                if quote:
                    outfile.write(f'\t"{file}"\n')
                else:
                    outfile.write(f'\t{file}\n')

                if ext in ['.h', '.hpp', '.inl']:
                    includepaths[root] = 1
        if not first:
            outfile.write('\n')

    os.chdir(olddir)


# Make an mkb from a dev studio 8 solution
def parse_sln(sln_name, name, outfile):
    with open(sln_name, 'r') as infile:
        # Make a regular expression for finding project names
        # It finds the project name in dev studio and the relative pathname of the vcproj
        proj_re = re.compile(r'Project\("{(?:[^"]+)}"\) = "([^"]+)", "([^"]+)"')

        # And regular expression for finding files within projects
        proj_file_re = re.compile(r'\s*RelativePath="([^"]+)"')

        for line in infile:
            projname = proj_re.match(line)
            if projname:
                # We've found a project, let's find its files
                print(f"Project: {projname.group(1)} in {projname.group(2)}")

                # Open and parse the project file
                projfilename = os.path.join(os.path.dirname(os.path.abspath(sln_name)), projname.group(2))
                with open(projfilename, 'r') as projfile:
                    first = True
                    previous_projfilename_dir = ''

                    for projline in projfile:
                        projfilename_result = proj_file_re.match(projline)
                        if projfilename_result:
                            # Let's make one section name per project
                            if first:
                                outfile.write(f'\n\t[{projname.group(1)}]\n')
                                first = False

                            # This is the name of a file in the project, relative to where we are now
                            projfilename = os.path.normpath(os.path.join(os.path.split(projname.group(2))[0], projfilename_result.group(1)))

                            # This is the path component of the filename above
                            projfilename_dir = os.path.split(projfilename)[0]
                            if projfilename_dir == '':
                                projfilename_dir = '.'

                            projfilename_filename = os.path.split(projfilename)[1]

                            if projfilename_dir != previous_projfilename_dir:
                                # This file is in a different directory.
                                outfile.write(f'\n\t({projfilename_dir})\n')
                                previous_projfilename_dir = projfilename_dir

                            # And then let's finally dump the filename itself.
                            outfile.write(f'\t{projfilename_filename}\n')

                            # What about include directories?
                            if os.path.splitext(projfilename_filename)[1].lower() == '.h':
                                includepaths[projfilename_dir] = 1


if __name__ == '__main__':
    run()