'''
Uploads data sets to a dataverse installation from the 
contents of a TSV (tab separated value)
file. Metadata, file tags, paths, etc are all read
from the TSV.
'''

import argparse

import dataverse_utils as du

VERSION = (0, 1, 0)
__version__ = '.'.join([str(x) for x in VERSION])

def parse() -> argparse.ArgumentParser():
    '''
    Parses the arguments from the command line.

    Returns argparse.ArgumentParser
    '''
    description = ('Uploads data sets to an *existing* Dataverse study '
                   'from the contents of a TSV (tab separated value) '
                   'file. Metadata, file tags, paths, etc are all read '
                   'from the TSV. '
                   'JSON output from the Dataverse API is printed to stdout during '
                   'the process.')
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('tsv', help='TSV file to upload',
                        nargs='?')
    parser.add_argument('-p', '--pid',
                        help='Dataverse study persistent identifier (DOI/handle)',
                        required=True)
    parser.add_argument('-k', '--key', required=True,
                        help='API key')
    parser.add_argument('-u', '--url', default='https://abacus.library.ubc.ca',
                        help=('Dataverse installation base URL. '
                              'Defaults to "https://abacus.library.ubc.ca"'))
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
    print(args)
    with open(args.tsv) as fil:
        du.upload_from_tsv(fil, hdl=args.pid,
                           dv=args.url, apikey=args.key)

if __name__ == '__main__':
    main()
