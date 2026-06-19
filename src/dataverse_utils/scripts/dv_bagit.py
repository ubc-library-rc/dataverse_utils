'''
Create a Bagit archive of either the current version of a study *or* all versions of a study.
'''

import argparse
import textwrap

import tqdm

import dataverse_utils
import dataverse_utils.collections as dvc
import dataverse_utils.archive as dva

def parse()->argparse.ArgumentParser:
    '''Argument parser'''
    description = textwrap.fill(textwrap.dedent(
                   '''
                   Downloads a Dataverse study given by persistentID(s),
                   ie, DOI or handle, then downloads files and metadata
                   and creates Bagit archive.

                   Archives are stored in directories with the name
                   [protocol]-[authority]_[identifier], where slashes are
                   replaced by underscores.

                   For full details on the Bagit specification, please see
                   https://datatracker.ietf.org/doc/html/rfc8493
                   '''), 80)
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-u', '--url', default='https://abacus.library.ubc.ca',
                        help=('Dataverse installation base url. '
                              'defaults to "https://abacus.library.ubc.ca"'))
    parser.add_argument('-v', '--version', action='version',
                        version=dataverse_utils.script_ver_stmt(parser.prog),
                        help='Show version number and exit')
    parser.add_argument('-k', '--key', required=True,
                        help='API key', default=None)
    parser.add_argument('-a','--all-versions',
                        help='Include *all** versions, not just the current version',
                        action='store_true')
    parser.add_argument('-t', '--target-dir',
                        help='Target directory for bag. Default: current directory',
                        default='.')
    parser.add_argument('-c', '--compress',
                        help='Compress Bagit archive into a zip file',
                        action='store_true')
    parser.add_argument('--contact-email',
                        help=('Bag contact email. Defaults to datasetContactEmail '
                              'if present. Optional'))
    parser.add_argument('--contact-phone',
                        help='Bag contact telephone number. Optional')
    parser.add_argument('pids',
                        help='Dataverse study persistent identifier(s) (DOI/handle)',
                        nargs='+')
    return parser

def main():
    '''
    Create a bag
    '''
    args = parse().parse_args()
    for pid in tqdm.tqdm(args.pids,
                         desc='Studies',
                         unit='study',
                         bar_format=dvc.BAR_FORMAT):
        pargs = args.__dict__.copy()
        del pargs['pids']
        pargs['pid'] = pid
        bag = dva.Archive(**pargs)
        bag.write_metadata()
        bag.process_files()
        bag.bagit_meta()
        bag.refresh_bag()
        if args.compress:
            bag.compress_bag(expunge=True)


    #print(args, file=sys.stdout)

if __name__ == '__main__':
    main()
