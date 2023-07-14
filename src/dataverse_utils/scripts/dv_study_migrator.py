import argparse
import textwrap
import sys
import dataverse_utils
import dataverse_utils.dvdata

VERSION = (0, 1, 0)
__version__ = '.'.join([str(x) for x in VERSION])

def parsley() -> argparse.ArgumentParser():
    '''
    Parses the arguments from the command line.

    Returns argparse.ArgumentParser
    '''
    description=textwrap.dedent('''
                Record migrator for Datverse.

                This utility will take the most recent version of a study
                from one Dataverse installation and copy the metadata
                and records to another, completely separate dataverse installation.

                You could also use it to copy records from one collection to another.
                ''')

    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('pids',
                        help=('PID(s) of original Dataverse record(s) in source Dataverse '
                              'separated by spaces. eg. "hdl:11272.1/AB2/JEG5RH '
                              'doi:11272.1/AB2/JEG5RH". '
                              'Case is ignored'),
                        nargs='+'
                       )
    parser.add_argument('-s', '--source_url', default='https://abacus.library.ubc.ca',
                        help=('Source Dataverse installation base URL. '),
                        required=True)
    parser.add_argument('-a', '--source_key', required=True,
                        help='API key for source Dataverse installation')
    parser.add_argument('-t', '--target_url', default=None,
                        help=('Source Dataverse installation base URL. '),
                        required=True)
    parser.add_argument('-b', '--tkey', required=True,
                        help='API key for target Dataverse installation')
    parser.add_argument('-o', '--timeout', default=100,
                        help='Request timeout in seconds. Default 100')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-c', '--collection',
                        help=('Short name of target Dataverse collection (eg: dli).'),
                        )
    group.add_argument('-r', '--replace',
                        help=('Replace metadata and data in record with this PID'),
                        )
    parser.add_argument('-v','--version', action='version',
                        version='%(prog)s '+__version__,
                        help='Show version number and exit')
    return parser
#create record

def upload_file_to_target(indict:dict, pid,
                          source_url, source_key,
                          target_url, target_key):
    file = dataverse_utils.dvdata.File(source_url, source_key, **indict)
    file.download_file() 
    file.verify()
    if file['verified']:
        dataverse_utils.upload_file(fpath=file['downloaded_file_name']
                                    dv=target_url,
                                    mimetype=file['dataFile'].get('contentType',
                                                                  'application/octet-stream'),
                                    apikey=target_key,
                                    hdl=pid,
                                    rest=file.get('restricted')
                                    ) 

def main():
    '''
    Run this, obviously
    '''
    args = parsley().parse_args()
    args.source_url = args.source_url.strip('/ ')
    args.target_url = args.target_url.strip('/ ')
    for pid in args.pids:
        stud = dataverse_utils.dvdata.Study(pid, args.source_url,
                                            args.source_key)
        if args.collection:
            upload = requests.post(f'{args.target_url}/api/dataverses/{args.collection}/datasets',
                                   json=stud['upload_json'],
                                   headers={'X-Dataverse-key': args.tkey},
                                   timeout=args.timeout)
            try:
                upload.raise_for_status()
            except requests.exceptions.HTTPError:
                print('Study upload error')
                sys.exit()
            doi = upload.json()['data']['persistentId']
            for fil in stud['file_info']:
                upload_file_to_target(fil)
                                    

def main2():
    '''
    Testing
    '''
    args = parsley().parse_args()
    args.source_url = args.source_url.strip('/ ')
    args.target_url = args.target_url.strip('/ ')
    print(args)
    

#Upload file
if __name__ == '__main__':
    main2()

