'''
Recursively parses a dataverse collection and
outputs study metadata for the latest version
'''
import argparse
import io
import csv
import textwrap
import dataverse_utils.collections as dvc
from dataverse_utils import VERSION

def parse() -> argparse.ArgumentParser():
    '''
    Parses the arguments from the command line.

    Returns argparse.ArgumentParser
    '''
    description = textwrap.dedent(
                   '''
                   Recursively parses a dataverse collection and
                   outputs study metadata for the latest version.

                   If analyzing publicly available collections, a
                   dataverse API key for the target system is not
                   required.
                   ''')
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-u', '--url', default='https://abacus.library.ubc.ca',
                        help=('Dataverse installation base url. '
                              'defaults to "https://abacus.library.ubc.ca"'))
    parser.add_argument('-c', '--collection',
                        help=('Dataverse collection shortname or id at the '
                             'top of the tree'),
                        required=True)
    parser.add_argument('-k', '--key', required=False,
                        help='API key', default=None)
    parser.add_argument('-d', '--delimiter', required=False,
                        help='Delimiter for output spreadsheet. Default: tab (\\t)',
                        default='\t')
    parser.add_argument('-f', '--fields',
                        help=('Record metadata fields to output. '
                              'For all fields, use "all". '
                              'Default: title, author.' ),
                        nargs='*',
                        default=['title', 'author'])
    parser.add_argument('-o', '--output', help='Output file name.',
                       required=False)
    parser.add_argument('--verbose', help='Verbose output. See what\'s happening.',
                        action='store_true',)
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s ' +
                                '.'.join([str(x) for x in VERSION]),
                        help='Show version number and exit')
    return parser

def main():
    '''
    You know what this is
    '''
    args = parse().parse_args()
    coll_me  = dvc.DvCollection(args.url, args.collection, args.key)
    coll_me.get_collections()
    coll_me.get_studies(verbose=args.verbose)
    if 'all' in [x.lower() for x in args.fields]:
        fieldnames = sorted(list(set(q for x in coll_me.studies for q in x.keys())))
    else:
        fieldnames = args.fields
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out,
                            fieldnames=fieldnames,
                            delimiter=args.delimiter,
                            quoting=csv.QUOTE_MINIMAL,
                            extrasaction='ignore')
    writer.writeheader()
    for row in coll_me.studies:
        #instant data cleanup. Why is this even in the metadata?
        writer.writerow({k:v.replace('\t',' ').replace('\r\n', ' ').replace('\n',' ')
                         for k, v in row.items()})
    out.seek(0)
    if args.output:
        with open(args.output, mode='w', encoding='utf-8', newline='') as f:
            f.write(out.read())
            return
    else:
        print(out.read())

if __name__ == '__main__':
    main()
