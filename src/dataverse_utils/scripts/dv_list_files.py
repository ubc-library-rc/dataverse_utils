'''
Utility to dump [selected] file information for a particular dataverse record.
'''
import argparse
import csv
import io
import json
import textwrap
from dataverse_utils.dvdata import FileInfo

VERSION  = (0, 1, 0)
__version__ = '.'.join([str(x) for x in VERSION])

def parse() -> argparse.ArgumentParser():
    '''
    Parses the arguments from the command line.

    Returns argparse.ArgumentParser
    '''
    description = textwrap.dedent(
                   '''
                   This will parse a Dataverse record and show the path, filename, descriptions
                   and download information for a Dataverse record. An API key is required
                   for DRAFT versions.
                   ''')
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('pid',
                        help='Dataverse study persistent identifier (DOI/handle)',
                        )
    parser.add_argument('-u', '--url', default='https://abacus.library.ubc.ca',
                        help=('Dataverse installation base url. '
                              'Defaults to "https://abacus.library.ubc.ca"'))
    parser.add_argument('-o', '--output', dest='out',
                        help='Output format. One of  csv, tsv, or json. Default tsv because '
                        'descriptions often contain commas',
                        default='tsv',
                        choices = ['csv', 'tsv', 'json'],
                        type=str.lower)
    parser.add_argument('-a', '--all', required=False,
                        dest='all_files',
                        action='store_true',
                        help='Show info for *all* versions, not just most current')
    parser.add_argument('-k', '--key', required=False,
                        default=None,
                        help='API key; required for restricted or draft data sets')
    parser.add_argument('-f', '--file',
                        help='Dump output to FILE')
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s '+__version__,
                        help='Show version number and exit')
    return parser

def main()->None:
    '''
    The primary function
    '''
    sepchar = {'tsv' : '\t',
               'csv' : ','}
    args = parse().parse_args()
    file_information = FileInfo(url=args.url, pid=args.pid, apikey=args.key)
    #breakpoint()
    output = io.StringIO(newline='')
    if args.out != 'json':
        writer = csv.DictWriter(output, delimiter=sepchar[args.out],
                                quoting=csv.QUOTE_MINIMAL,
                                fieldnames=file_information['headers'],
                                extrasaction='ignore')
        writer.writeheader()
        if not args.all_files:
            for row in file_information[file_information['current_version']]:
                writer.writerow(row)

        else:
            for vers in file_information['version_list']:
                for row in file_information[vers]:
                    writer.writerow(row)
    else:
        output.write(json.dumps(file_information))
    output.seek(0)
    if args.file:
        with open(args.file, 'w', encoding='utf-8') as outie:
            outie.write(output.read())
        return

    #stdout
    print(output.read())
    return

if __name__ == '__main__':
    main()
