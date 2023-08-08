'''
Copies an entire record and migrates it *including the data*
'''
import argparse
import textwrap
import sys
import requests
import dataverse_utils
import dataverse_utils.dvdata

VERSION = (0, 4, 1)
__version__ = '.'.join([str(x) for x in VERSION])

def parsley() -> argparse.ArgumentParser():
    '''
    Parses the arguments from the command line.

    Returns argparse.ArgumentParser
    '''
    description=textwrap.dedent('''
                Record migrator for Dataverse.

                This utility will take the most recent version of a study
                from one Dataverse installation and copy the metadata
                and records to another, completely separate dataverse installation.

                You could also use it to copy records from one collection to another.
                ''')
    replac = textwrap.dedent('''
                             Replace data in these target PIDs with data from the
                             source PIDS. Number of PIDs listed here must match
                             the number of PID arguments to follow. That is, the number
                             of records must be equal. Records will be matched on a
                             1-1 basis in order. For example:
                             [rest of command] -r doi:123.34/etc hdl:12323/AB/SOMETHI
                             will replace the record with identifier 'doi' with the data from 'hdl'.

                             Make sure you don't use this as the penultimate switch, because 
                             then it's not possible to disambiguate PIDS from this argument
                             and positional arguments.
                             ie, something like dv_study_migrator -r blah blah -s http//test.invalid etc.
                             ''')
    pidhelp = textwrap.dedent('''
                              PID(s) of original Dataverse record(s) in source Dataverse
                              separated by spaces. eg. "hdl:11272.1/AB2/JEG5RH
                              doi:11272.1/AB2/JEG5RH".
                              Case is ignored.
                              ''')
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('pids',
                        help=pidhelp[1:],
                        nargs='+'
                       )
    parser.add_argument('-s', '--source_url', default='https://abacus.library.ubc.ca',
                        help=('Source Dataverse installation base URL.'),
                        required=True)
    parser.add_argument('-a', '--source_key', required=True,
                        help='API key for source Dataverse installation.')
    parser.add_argument('-t', '--target_url', default=None,
                        help=('Source Dataverse installation base URL.'),
                        required=True)
    parser.add_argument('-b', '--target_key', required=True,
                        help='API key for target Dataverse installation.')
    parser.add_argument('-o', '--timeout', default=100,
                        help='Request timeout in seconds. Default 100.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-c', '--collection',
                        help=('Short name of target Dataverse collection (eg: dli).'),
                        )
    group.add_argument('-r', '--replace',
                       nargs='+',
                       help=replac[1:]
                        )
    parser.add_argument('-v','--version', action='version',
                        version='%(prog)s '+__version__,
                        help='Show version number and exit')
    return parser

def upload_file_to_target(indict:dict, pid,#pylint: disable = too-many-arguments
                          source_url, source_key,
                          target_url, target_key):
    '''
    Uploads a single file with metadata to a dataverse record
    '''
    file = dataverse_utils.dvdata.File(source_url, source_key, **indict)
    file.download_file()
    file.verify()
    label = file['dataFile'].get('originalFileName',
                file['dataFile'].get('filename', file['label']))
    mimetype=file['dataFile'].get('originalFileFormat',
                file['dataFile'].get('contentType','application/octet-stream'))
    if file['verified']:
        dataverse_utils.upload_file(fpath=file['downloaded_file_name'],
                                    dv=target_url,
                                    mimetype=mimetype,
                                    apikey=target_key,
                                    hdl=pid,
                                    rest=file.get('restricted'),
                                    label=label,
                                    dirlabel=file.get('directoryLabel', ''),
                                    descr=file.get('description', ''),
                                    tags=file.get('categories')
                                    )

def remove_target_files(record:dataverse_utils.dvdata.Study, timeout:int=100):
    '''
    Removes all files from a dataverse record.
        record: dataverse_utils.dvdata.Study
        timeout: int
            Timeout in seconds
    '''
    for badfile in record['file_ids']:
        #I know, let's have two APIs for no reason!
        badf = requests.delete((f'{record["url"]}/dvn/api/data-deposit/'
                                f'v1.1/swordv2/edit-media/file/{badfile}'),
                               auth=(record['key'],''),
                               timeout=timeout)
        try:
            badf.raise_for_status()
        except requests.exceptions.HTTPError:
            print(f'File delete error for {record["pid"]}, fileid: {badfile}: Exiting',
                  file = sys.stderr)
            sys.exit()



def main():
    '''
    Run this, obviously
    '''
    args = parsley().parse_args()
    args.source_url = args.source_url.strip('/ ')
    args.target_url = args.target_url.strip('/ ')

    studs = [dataverse_utils.dvdata.Study(x, args.source_url, args.source_key)
             for x in args.pids]
    for stud in studs:
        stud.set_version(args.target_url)

    if args.collection:
        for stud in studs:
            upload = requests.post(f'{args.target_url}/api/dataverses/{args.collection}/datasets',
                                   json=stud['upload_json'],
                                   headers={'X-Dataverse-key': args.target_key},
                                   timeout=args.timeout)
            try:
                upload.raise_for_status()
            except requests.exceptions.HTTPError:
                print(f'Study upload error for {stud["pid"]}: Exiting',
                      file = sys.stderr)
                print(upload.json())
                sys.exit()
            doi = upload.json()['data']['persistentId']
            for fil in stud['file_info']:
                upload_file_to_target(fil, doi,
                                      args.source_url, args.source_key,
                                      args.target_url, args.target_key)
    if args.replace:
        if len(args.replace) != len(args.pids):
            print('Number of replacements must match number of input records',
                  file=sys.stderr)
            sys.exit()
        for rec in zip(args.replace, studs):
            oldrec = dataverse_utils.dvdata.Study(rec[0], args.target_url,
                                                args.target_key)
            remove_target_files(oldrec, args.timeout)
            #  payload = {'metadataBlocks': _output_json(record)['datasetVersion']\
            # ['metadataBlocks']}

            upload = requests.put(f'{args.target_url}/api/datasets/:persistentId/versions/:draft',
                                   json={'metadataBlocks': rec[1]['upload_json']\
                                                           ['datasetVersion']['metadataBlocks']},
                                   headers={'X-Dataverse-key' : args.target_key},
                                   params={'persistentId' : rec[0]},
                                   timeout=args.timeout)
            try:
                upload.raise_for_status()
            except requests.exceptions.HTTPError:
                print(f'Study upload error for {rec[0]} / {rec[1]["pid"]}: Exiting',
                      file = sys.stderr)
                sys.exit()
            for fil in rec[1]['file_info']:
                #doi = upload.json()['data']['persistentId']
                upload_file_to_target(fil, rec[0],
                                      args.source_url, args.source_key,
                                      args.target_url, args.target_key)

if __name__ == '__main__':
    main()
