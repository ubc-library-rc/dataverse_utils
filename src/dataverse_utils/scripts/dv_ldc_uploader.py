'''
Auto download/upload LDC metadata and files.

python3 uploadme.py LDC20201S01 . . . LDC2021T21 apikey

'''
import argparse
import sys
import dataverse_utils as du
from dataverse_utils import ldc

def parse() -> argparse.ArgumentParser():
    '''
    Parses the arguments from the command line.

    Returns argparse.ArgumentParser
    '''
    description = ('Linguistic Data Consortium metadata uploader for Dataverse.\n'
                   'This utility will scrape the metadata from the '
                   'LDC website (https://catalog.ldc.upenn.edu) and '
                   'upload data based on a TSV manifest.\n\n'
                   'Please note that this utility was built with the Abacus '
                   'repository (https://abacus.library.ubc.ca) in mind, '
                   'so many of the defaults are specific to that Dataverse '
                   'installation.')
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('studies', nargs='+',
                        help=('LDC Catalogue numbers to process, '
                              'separated by spaces. eg. "LDC2012T19 LDC2011T07". '
                              'Case is ignored, so "ldc2012T19" will also work.'))
    parser.add_argument('-u', '--url', default='https://abacus.library.ubc.ca',
                        help=('Dataverse installation base URL. '
                              'Defaults to "https://abacus.library.ubc.ca"'))
    parser.add_argument('-k', '--key', required=True,
                        help='API key')
    parser.add_argument('-d', '--dvs',
                        help=('Short name of target Dataverse collection (eg: ldc). '
                              'Defaults to "ldc"'),
                        default='ldc')
    parser.add_argument('-t', '--tsv',
                        help=('Manifest tsv file for uploading and metadata. '
                              'If not supplied, only metadata will be uploaded. '
                              'Using this option '
                              'requires only one positional *studies* argument'),
                        default=None)
    parser.add_argument('-r', '--no-restrict', action='store_false', dest='rest',
                        help="Don't restrict files after upload.")
    parser.add_argument('-n', '--cname',
                        help=('Study contact name. '
                              'Default: "Abacus support"'),
                        default='Abacus Support')
    parser.add_argument('-c', '--certchain',
                        help=('Certificate chain PEM: use if SSL issues '
                              'are present. The PEM chain must be downloaded '
                              'with a browser. '
                              'Default: None'),
                        default=None)
    parser.add_argument('-e', '--email',
                        help=('Dataverse study contact email address. '
                              'Default: abacus-support@lists.ubc.ca'),
                        default='abacus-support@lists.ubc.ca')
    parser.add_argument('-v', '--verbose',
                        help='Verbose output',
                        action='store_true')
    parser.add_argument('--version', action='version',
                        version=du.script_ver_stmt(parser.prog),
                        help='Show version number and exit')
    return parser

def upload_meta(ldccat: str, url: str, key: str,#pylint: disable = too-many-arguments, too-many-positional-arguments
                dvs: str, verbose: bool = False,
                certchain: str = None) -> str:
    '''
    Uploads metadata to target dataverse collection. Returns persistentId.

    Parameters
    ----------
    ldccat : str
        Linguistic Data Consortium catalogue number
    url : str
        URL to base instance of Dataverse installation
    key : str
        API key
    dvs : str
        Target Dataverse collection short name
    certchain : str
        Path to LDC .PEM certificate chain
    '''
    stud = ldc.Ldc(ldccat, cert=certchain)
    stud.fetch_record()
    if verbose:
        print(f'Uploading {stud.ldc} metadata')
    info = stud.upload_metadata(url=url, key=key, dv=dvs)
    return info['data']['persistentId']

def main() -> None:
    '''
    Uploads metadata and data to Dataverse collection/study respectively
    '''
    parser = parse()
    args = parser.parse_args()
    ldc.ds.constants.DV_CONTACT_EMAIL = args.email
    ldc.ds.constants.DV_CONTACT_NAME = args.cname
    #print(args)
    if args.tsv:
        if len(args.studies) > 1:
            print('Error: Only one LDC study may be processed with the -t/--tsv option')
            sys.exit()
        pid = upload_meta(args.studies[0], args.url, args.key,
                          args.dvs, args.verbose, args.certchain)
        if args.verbose:
            print(f'Uploading files to {pid}')
        with open(args.tsv, encoding='utf-8', newline='') as fil:
            du.upload_from_tsv(fil, hdl=pid,
                               dv=args.url, apikey=args.key,
                               trunc='',
                               rest=args.rest)

        sys.exit()

    for stud in args.studies:
        pid = upload_meta(stud, args.url, args.key,
                          args.dvs, args.verbose, args.certchain)
        if args.verbose:
            print(pid)

if __name__ == '__main__':
    main()
