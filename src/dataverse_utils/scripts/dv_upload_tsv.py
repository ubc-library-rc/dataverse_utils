#!python
'''
Uploads data sets to a dataverse installation from the
contents of a TSV (tab separated value)
file. Metadata, file tags, paths, etc are all read
from the TSV.
'''

import argparse
import sys
import textwrap

import dataverse_utils as du

VERSION = (0, 4, 2)
__version__ = '.'.join([str(x) for x in VERSION])

def parse() -> argparse.ArgumentParser():
    '''
    Parses the arguments from the command line.

    Returns argparse.ArgumentParser
    '''
    description = textwrap.dedent(
                   '''
                   Uploads data sets to an *existing* Dataverse study
                   from the contents of a TSV (tab separated value)
                   file. Metadata, file tags, paths, etc are all read
                   from the TSV.

                   JSON output from the Dataverse API is printed to stdout during
                   the process.

                   By default, files will be unrestricted but the utility will ask
                   for confirmation before uploading.
                   ''')
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('tsv', help='TSV file to upload')
    parser.add_argument('-p', '--pid',
                        help='Dataverse study persistent identifier (DOI/handle)',
                        required=True)
    parser.add_argument('-k', '--key', required=True,
                        help='API key')
    parser.add_argument('-u', '--url', default='https://abacus.library.ubc.ca',
                        help=('Dataverse installation base url. '
                              'defaults to "https://abacus.library.ubc.ca"'))
    parser.add_argument('-r', '--restrict', action='store_true', dest='rest',
                        help='Restrict files after upload.')
    parser.add_argument('-n', '--no-confirm', action='store_true', dest='nc',
                        help='Don\'t confirm non-restricted status')
    parser.add_argument('-t', '--truncate', default='',
                        help=textwrap.dedent(
                            '''
                            Left truncate file path. As Dataverse studies
                            can retain directory structure, you can set
                            an arbitrary starting point by removing the
                            leftmost portion. Eg: if the TSV has a file
                            path of /home/user/Data/file.txt, setting
                            --truncate to "/home/user" would have file.txt
                            in the Data directory in the Dataverse study.
                            The file is still loaded from the path in the
                            spreadsheet.

                            Defaults to no truncation.
                            '''))
    parser.add_argument('--version', action='version',
                        version='%(prog)s '+__version__,
                        help='Show version number and exit')
    return parser

def main() -> None:
    '''
    Uploads data to an already existing Dataverse study
    '''
    parser = parse()
    args = parser.parse_args()
    if not args.nc and not args.rest:
        conf = input('File will be unrestricted. Continue (y/n)? ')
        if conf.lower() == 'n' or conf.lower() == 'no':
            print('Transfer aborted')
            sys.exit()

    with open(args.tsv, newline='', encoding='utf-8') as fil:
        du.upload_from_tsv(fil, hdl=args.pid,
                           dv=args.url, apikey=args.key,
                           trunc=args.truncate, rest=args.rest)

if __name__ == '__main__':
    main()
