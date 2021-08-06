#!python
'''Dataverse Bulk Deleter
Deletes unpublished studies at the command line
'''

import argparse
#import json
import sys
import requests
VERSION = (0, 2, 0)
__version__ = '.'.join([str(x) for x in VERSION])

def delstudy(dvurl, key, pid):
    '''
    Deletes datavesrse study

    dvurl : str
        Dataverse installation base URL
    key : str
        Dataverse user API key
    pid : str
        Dataverse collection study persistent identifier
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
        Dataverse installation base URL
    pid : str
        Dataverse collection study persistent identifier
    key : str
        Dataverse user API key
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
                        default='https://soroban.library.ubc.ca', dest='dvurl')
    parser.add_argument('--version', action='version',
                        version='%(prog)s '+__version__,
                        help='Show version number and exit')
    args = parser.parse_args()
    args.dvurl = args.dvurl.strip('/')

    if args.dataverse:
        info = requests.get(f'{args.dvurl}/dataverses/{args.dataverse}/contents',
                            headers={'X-Dataverse-key': args.key}, timeout=10).json()
        pids = [f'{x["protocol"]}:{x["authority"]}/{x["identifier"]}' for x in info['data']]
        if not pids:
            print(f'Dataverse collection {args.dataverse} empty')
        for pid in pids:
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
            print(f'Autodelete of individual {args.pid} here')
            print(delstudy(args.dvurl, args.key, args.pid))

if __name__ == '__main__':
    main()
