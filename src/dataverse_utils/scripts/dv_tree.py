'''
Dataverse collection tree view
'''

import argparse
import sys
import textwrap
import dataverse_utils as du
import dataverse_utils.collections as dvc

def parse()->argparse.ArgumentParser:
    '''
    Argument parser
    '''
    description = textwrap.fill(textwrap.dedent(
                   '''
                   Produce a tree view of collection, given a top-level collection.
                   Outputs studies and collections in a view similar to that
                   of the **tree** command. Like **tree**, prints to terminal.

                   To save to a file, use a redirect, ie ">".
                   '''))

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-u', '--url',
                        default='https://borealisdata.ca',
                        help=('URL of Dataverse instance. Default: '
                              'https://borealisdata.ca'))
    parser.add_argument('-k', '--key',
                        help='API key',
                        required=True)
    parser.add_argument('collection',
                        help='Dataverse short name of collection to traverse',
                        nargs='?')
    parser.add_argument('-v', '--version',
                        action='version',
                        version=du.script_ver_stmt(parser.prog),
                        help='Show version number and exit')

    return parser

def main():
    '''
    Obviously
    '''
    args = parse().parse_args()
    if not args.collection:
        sys.exit()
    top = dvc.DvCollection(url=args.url, coll=args.collection, key=args.key)
    try:
        tree = top.tree()
        print(tree.read(), file=sys.stdout)
    except (KeyError, ValueError, IndexError, dvc.requests.HTTPError) as exc:
        print(f'Error {exc}',  file=sys.stderr)
        sys.exit()

if __name__ == '__main__':
    main()
