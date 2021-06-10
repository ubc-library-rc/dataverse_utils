'''Dataverse Bulk Deleter
Deletes unpublished studies at the command line
'''

import argparse
#import json
import sys
import requests

def delstudy(dvurl, key, pid):
    '''
    Deletes datavesrse study

    dvurl : str
        Dataverse base URL
    key : str
        Dataverse API key
    pid : str
        Dataverse study persistent identifier
    '''
    try:
        deler = requests.delete(f'{dvurl}/api/datasets/:persistentId/versions/:draft',
                                headers={'X-Dataverse-key':key},
                                params={'persistentId':pid},
                                timeout=30)
        if deler.status_code == 200:
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
    dvurl : str
        Dataverse base URL
    pid : str
        Dataverse study persistent identifier
    key : str
        Dataverse API key
    '''
    try:
        sizer = requests.get(f'{dvurl}/api/datasets/:persistentId/storagesize',
                             headers={'X-Dataverse-key':key},
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

def main():
    '''
    Command line bulk deleter
    '''
    parser = argparse.ArgumentParser(description='Delete draft studies from dataverse')
    parser.add_argument('-k', '--key', help='Dataverse API key', required=True, dest='key')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--dataverse', help='Dataverse from which to delete all draft records',
                       dest='dataverse')
    group.add_argument('-p', '--persistentId',
                       help='Handle or DOI to delete in format hdl:11272.1/FK2/12345',
                       dest='pid')
    parser.add_argument('-i', '--interactive',
                        help="Confirm each study deletion",
                        action='store_true', dest='conf')
    parser.add_argument('-u', '--url', help='URL to base Dataverse instance',
                        default='https://soroban.library.ubc.ca', dest='dvurl')
    args = parser.parse_args()
    #print(args)
    args.dvurl = args.dvurl.strip('/')
    #if args.dvurl.endswith('/'): args.dvurl = args.dvurl[:-1]

    if args.dataverse:
        info = requests.get(f'{args.dvurl}/dataverses/{args.dataverse}/contents',
                            headers={'X-Dataverse-key': args.key}, timeout=10).json()
        pids = [f'{x["protocol"]}:{x["authority"]}/{x["identifier"]}' for x in info['data']]
        if not pids:
            print(f'Dataverse {args.dataverse} empty')
        for pid in pids:
            try:
                if args.conf:
                    if conf(pid):
                        print(delstudy(args.dvurl, args.key, pid))
                        continue

                    else:
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
            print(f'Autodelete of individual {args.pid} here')
            print(delstudy(args.dvurl, args.key, args.pid))

if __name__ == '__main__':
    main()
