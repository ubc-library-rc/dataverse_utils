#!python
'''
Creates a file manifest in tab separated value format
which can be used with other dataverse_util library utilities
and functions to upload files complete with metadata.
'''

import argparse
import os
import pathlib
#pathlib new for Python 3.5
#https://docs.python.org/3/library/pathlib.html
import re
import sys


import dataverse_utils as du

VERSION = (0, 5, 0)
__version__ = '.'.join([str(x) for x in VERSION])

def parse() -> argparse.ArgumentParser():
    '''
    Parses the arguments from the command line.

    Returns argparse.ArgumentParser
    '''
    description = ('Creates a file manifest in tab separated value format '
                   'which can then be edited and used for file uploads to '
                   'a Dataverse collection. Files can be edited to add file descriptions '
                   'and comma-separated tags that will be automatically '
                   'attached to metadata using products using the dataverse_utils '
                   'library. '
                   'Will dump to stdout unless -f or --filename is used. '
                   'Using the command and a dash (ie, "dv_manifest_gen.py -" '
                   'produces full paths for some reason.')
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('files', help=('Files to add to manifest. Leaving it '
                                       'blank will add all files in the current '
                                       'directory. If using -r will recursively '
                                       'show all.'),
                        nargs='*', default=None)
    parser.add_argument('-f', '--filename',
                        help='Save to file instead of outputting to stdout',
                        default=None)
    parser.add_argument('-t', '--tag',
                        help=('Default tag(s). Separate with comma and '
                              'use quotes if there are spaces. '
                              'eg. "Data, June 2021". '
                              'Defaults to "Data"'),
                        default='Data')
    parser.add_argument('-x', '--no-header',
                        help=('Don\'t include header in output. Useful if '
                              'creating a complex tsv using redirects (ie, ">>").'),
                        action='store_false',
                        dest='inc_header')
    parser.add_argument('-r', '--recursive',
                        help=('Recursive listing.'),
                        action='store_true')
    parser.add_argument('-q', '--quote',
                        help=('Quote type. Cell value quoting parameters. '
                              'Options: none (no quotes), min (minimal, '
                              'ie. special characters only )'
                              'nonum (non-numeric), all (all cells). '
                              'Default: min'
                              ),
                        default='min')
    parser.add_argument('-a', '--show-hidden',
                        help=('Include hidden files.'),
                        action='store_true')
    parser.add_argument('-m', '--mime',
                        help=('Include autodetected mimetypes'),
                        action='store_true')
    parser.add_argument('-p', '--path',
                        help=('Include an optional path column for custom file paths'),
                        action='store_true')
    parser.add_argument('--version', action='version',
                        version='%(prog)s '+__version__,
                        help='Show version number and exit')
    return parser

def quotype(quote: str)-> int:
    '''
    Parse quotation type for csv parser.

    returns csv quote constant.
    '''
    vals = {'min'  : 0,
            'all' : 1,
            'nonum' : 2,
            'none' : 3}
    return vals.get(quote.lower(), -1)

def main() -> None:
    '''
    The main function call
    '''
    parser = parse()
    args = parser.parse_args()
    args.quote = quotype(args.quote)
    if  args.quote == -1:
        parser.error('Invalid quotation type')
    f_list = []

    if not args.files:
        args.files = [str(x) for x in pathlib.Path('./').glob('*')]
    if args.show_hidden:
        args.files +=  [str(x) for x in pathlib.Path('./').glob('.*')]
    for fil in args.files:
        finder = pathlib.Path(fil).expanduser()
        if args.recursive and finder.is_dir():
            f_list += list(finder.rglob('*'))
        else:
            f_list += list(finder.parent.glob(finder.name))
    #Set comprehension strips out duplicates
    #Strip out hidden files and directories
    if args.show_hidden:
        f_list = {str(x) for x in f_list if x.is_file()}
    else:
        f_list = {str(x) for x in f_list if x.is_file() and not re.search(r'^\.[Aa9-Zz9]*', str(x))}
    if not f_list:
        print('Nothing matching these criteria. No manifest generated')
        sys.exit()
    if args.filename:
        du.dump_tsv(os.getcwd(), filename=args.filename,
                    in_list=f_list,
                    def_tag=args.tag,
                    inc_header=args.inc_header,
                    quotype=args.quote,
                    mime=args.mime,
                    path=args.path)
    else:
        print(du.make_tsv(os.getcwd(), in_list=f_list,
                          def_tag=args.tag,
                          inc_header=args.inc_header,
                          quotype=args.quote,
                          mime=args.mime,
                          path=args.path))

if __name__ == '__main__':
    main()
