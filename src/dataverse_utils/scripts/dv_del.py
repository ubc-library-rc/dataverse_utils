'''Dataverse Bulk Deleter
Deletes unpublished studies at the command line
'''

import argparse
#import json
import sys
import time
import requests
import dataverse_utils

def delstudy(dvurl, key, pid):
    '''
    Deletes Dataverse study
    
    Parameters
    ----------
    dvurl : str
        Dataverse installation base URL
    key : str
        Dataverse user API key
    pid : str
        Dataverse collection study persistent identifier
    '''
    try:
        deler = requests.delete(f'{dvurl}/api/datasets/:persistentId/versions/:draft',
                                headers=make_header(key),
                                params={'persistentId':pid},
                                timeout=60)
        if deler.status_code == 200:
            print(deler.json())
            return f'Deleted {pid}'
        deler.raise_for_status()
        return None
    except requests.exceptions.HTTPError:
        return f'Failed to delete {pid}. \n Message: {deler.text}'

def conf(tex):
    '''
    Confirmation dialogue checker. Returns true if "Y" or "y"
    '''
    yes = input(f'Delete {tex}? ')
    if yes.lower() == 'y':
        return True
    return False

def getsize(dvurl, pid, key):
    '''
    Returns size of Dataverse study. Mostly here for debugging.

    Parameters
    ----------
    dvurl : str
        Dataverse installation base URL
    pid : str
        Dataverse collection study persistent identifier
    key : str
        Dataverse user API key
    '''
    try:
        sizer = requests.get(f'{dvurl}/api/datasets/:persistentId/storagesize',
                             headers=make_header(key),
                             params={'persistentId':pid},
                             timeout=10)
        text = sizer.json()['data']['message']
        text = text[text.rfind(':')+2 : -6]
        text = text.split(',')
        size = int(''.join(text))
        sleeptime = text//1024//1024/10 # sleep for 1/10th sec per megabyte
        return (size, sleeptime)
    except requests.exceptions.HTTPError:
        return (0, 0)

def parsley()->argparse.ArgumentParser:
    '''
    Argument parser as separate function
    '''
    parser = argparse.ArgumentParser(description='Delete draft studies from a Dataverse collection')
    parser.add_argument('-k', '--key', help='Dataverse user API key', required=True, dest='key')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--dataverse',
                       help=('Dataverse collection short name from which '
                             'to delete all draft records. eg. "ldc"'),
                       dest='dataverse')
    group.add_argument('-p', '--persistentId',
                       help='Handle or DOI to delete in format hdl:11272.1/FK2/12345',
                       dest='pid')
    parser.add_argument('-i', '--interactive',
                        help="Confirm each study deletion",
                        action='store_true', dest='conf')
    parser.add_argument('-u', '--url', help='URL to base Dataverse installation',
                        default='https://abacus.library.ubc.ca', dest='dvurl')
    parser.add_argument('-v','--version', action='version',
                        version=dataverse_utils.script_ver_stmt(parser.prog),
                        help='Show version number and exit')
    return parser

def make_header(key:str)->dict:
    '''
    Make a proper header with user agent

    Parameters
    ----------
    key : str
        API key
    '''
    out = {'X-Dataverse-key' : key}
    out.update(dataverse_utils.UAHEADER)
    return out

def main():
    '''
    Command line bulk deleter
    '''
    args = parsley().parse_args()
    args.dvurl = args.dvurl.strip('/')

    if args.dataverse:
        info = requests.get(f'{args.dvurl}/api/dataverses/{args.dataverse}/contents',
                            headers=make_header(args.key), timeout=10).json()
        #Protocol key only present in a dataset, not in a sub-collection listing
        pids = [f'{x["protocol"]}:{x["authority"]}/{x["identifier"]}'
                for x in info['data'] if x.get('protocol')]
        if not pids:
            print(f'Dataverse collection {args.dataverse} empty')
        for count, pid in enumerate(pids):
            #Reduce timeouts by waiting between requests
            if count !=0 and not count%10:
                time.sleep(5)
            try:
                if args.conf:
                    if conf(pid):
                        print(delstudy(args.dvurl, args.key, pid))
                        continue

                    print(f'Skipping {pid}')
                    continue

                print(delstudy(args.dvurl, args.key, pid))
                #time.sleep(getsize(pid, args.key)[1])#Will this stop the server crash?
            except KeyboardInterrupt:
                print('Aborted by user')
                sys.exit()

    if args.pid:
        if args.conf:
            if conf(args.pid):
                print(delstudy(args.dvurl, args.key, args.pid))
            else:
                print(f'Aborting delete of {args.pid}')

        else:
            print(delstudy(args.dvurl, args.key, args.pid))

if __name__ == '__main__':
    main()
