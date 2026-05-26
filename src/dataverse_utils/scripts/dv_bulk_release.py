'''Dataverse bulk releaser 
Publish studies at the command line either by PID or by collections
'''

import argparse
#import json
import sys
import textwrap
import time
import requests
import dataverse_utils

DESCRIPTION = '''
              Bulk publish an entire Dataverse collection or just a single study.

              Failure to publish (for whatever reason) results in a console message,
              as does success.
              
              By default, publishing version is "major" unless specified, subject to
              the inbuilt limitations of a Dataverse installation.

              Note that the owning **collection** must be published first. It is not
              possible to publish studies when their containers are not yet published.
              '''

def relstudy(dvurl, key, pid, majmin:str='major')->str:
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
    majmin : str
        
    '''
    if majmin.lower() not in ['major', 'minor']:
        raise ValueError('type must be "major" or "minor"')
    try:
        reler = requests.post(f'{dvurl}/api/datasets/:persistentId/actions/:publish',
                                headers=make_header(key),
                              params={'persistentId':pid, 'type':majmin},
                                timeout=60)
        if reler.status_code == 200:
            return f'Published {pid}: reler.json()["message"]'
        try:
            msg = reler.json()
            if msg.get('status', '') == 'ERROR':
                return f'Failed to publish {pid}: {msg["message"]}'
        except (KeyError, TypeError) as exp:
            return f'Failed to publish {pid}: Error in {exp}'
        reler.raise_for_status()
        return ''
    except requests.exceptions.HTTPError:
        return f'Failed to publish {pid}. \n Message: {reler.text}'

def conf(tex):
    '''
    Confirmation dialogue checker. Returns true if "Y" or "y"
    '''
    yes = input(f'Delete {tex} (y/n)? ')
    if yes.lower()[0] == 'y':
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
    parser = argparse.ArgumentParser(description=textwrap.fill(
                                                 textwrap.dedent(DESCRIPTION)).strip())
    parser.add_argument('-k', '--key', help='Dataverse user API key', required=True, dest='key')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-c', '--collection',
                       help=('Dataverse collection short name from which '
                             'contains draft records. eg. "ldc"'),
                       dest='collection')
    group.add_argument('-p', '--persistentId',
                       help='Handle or DOI to publish in format hdl:11272.1/FK2/12345',
                       dest='pid')
    parser.add_argument('-i', '--interactive',
                        help="Confirm each study publication",
                        action='store_true', dest='conf')
    parser.add_argument('-u', '--url', help=('URL to base Dataverse installation. '
                                             'Default: https://borealisdata.ca'),
                        default='https://borealisdata.ca', dest='dvurl')
    parser.add_argument('-m', '--major-minor',
                        help=('Keyword indicating major or minopublished. "major" or "minor". '
                              'Default: major'),
                        default='major', dest='majmin')
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
    args.majmin = args.majmin.lower()
    args.dvurl = args.dvurl.strip('/')

    if args.collection:
        info = requests.get(f'{args.dvurl}/api/dataverses/{args.collection}/contents',
                            headers=make_header(args.key), timeout=10).json()
        #Protocol key only present in a dataset, not in a sub-collection listing
        pids = [f'{x["protocol"]}:{x["authority"]}/{x["identifier"]}'
                for x in info['data'] if x.get('protocol')]
        if not pids:
            print(f'Dataverse collection {args.collection} empty')
        for count, pid in enumerate(pids):
            #Reduce timeouts by waiting between requests
            if count !=0 and not count%10:
                time.sleep(5)
            try:
                if args.conf:
                    if conf(pid):
                        print(relstudy(args.dvurl, args.key, pid, args.majmin))
                        continue

                    print(f'Skipping {pid}')
                    continue
                print(relstudy(args.dvurl, args.key, pid, args.majmin))
                #time.sleep(getsize(pid, args.key)[1])#Will this stop the server crash?
            except KeyboardInterrupt:
                print('Aborted by user')
                sys.exit()

    if args.pid:
        if args.conf:
            if conf(args.pid):
                print(relstudy(args.dvurl, args.key, args.pid, args.majmin))
            else:
                print(f'Aborting publish of {args.pid}')

        else:
            print(relstudy(args.dvurl, args.key, args.pid))

if __name__ == '__main__':
    main()
