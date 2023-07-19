'''
Copies a dataverse record to collection
OR copies a record to an existing PID.

That way all you have to do
is edit a few fields in the GUI instead of
painfully editing JSON or painfully using the
Dataverse GUI.
'''
import argparse
import requests

VERSION = (0, 1, 1)
__version__ = '.'.join([str(x) for x in VERSION])
TIMEOUT = 100

def parsley() -> argparse.ArgumentParser():
    '''
    Parses the arguments from the command line.

    Returns argparse.ArgumentParser
    '''
    description = ('Record duplicator for Dataverse.\n'
                   'This utility will download a Dataverse record '
                   'And then upload the study level metadata into a new '
                   'record in a user-specified collection.\n\n'
                   'Please note that this utility was built with the Abacus '
                   'repository (https://abacus.library.ubc.ca) in mind, '
                   'so many of the defaults are specific to that Dataverse '
                   'installation.')
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('pid',
                        help=('PID of original dataverse record'
                              'separated by spaces. eg. "hdl:11272.1/AB2/NOMATH hdl:11272.1/AB2/HANDLE". '
                              'Case is ignored, so "hdl:11272.1/ab2/handle" will also work.'))
    parser.add_argument('-u', '--url', default='https://abacus.library.ubc.ca',
                        help=('Dataverse installation base URL. '
                              'Defaults to "https://abacus.library.ubc.ca"'))
    parser.add_argument('-k', '--key', required=True,
                        help='API key')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-c', '--collection',
                        help=('Short name of target Dataverse collection (eg: ldc). '
                              'Defaults to "ldc"'),
                        )
    group.add_argument('-r', '--replace',
                        help=('Replace metadata data in record with this PID'),
                        )
    parser.add_argument('-v','--version', action='version',
                        version='%(prog)s '+__version__,
                        help='Show version number and exit')
    return parser

def _download_original(url: str, pid : str, key: str) -> dict:
    '''
    Downloads the original metadata record to be copied

    Returns the latest version of the metadata as dict.
    '''
    #curl -H "X-Dataverse-key:$API_TOKEN" /
    #$SERVER_URL/api/datasets/:persistentId/?persistentId=$PERSISTENT_IDENTIFIER
    getjson = requests.get(url+'/api/datasets/:persistentId',
                           headers={'X-Dataverse-key':key},
                           params = {'persistentId': pid},
                           timeout = TIMEOUT)
    getjson.raise_for_status()
    return getjson.json()['data']['latestVersion']

def _output_json(injson : dict)->dict:
    '''
    Takes a json representation of a downloaded dataset version
    and returns properly formatted dict for upload to a new
    Dataverse record.
    '''
    return {'datasetVersion': {'license': injson['license'],
                                 'termsOfUse': injson['termsOfUse'],
                                 'metadataBlocks': injson['metadataBlocks']
                                 }
              }

def main():
    '''
    You know what this does
    '''
    parser = parsley()
    args = parser.parse_args()
    args.url = args.url.strip('/ ')
    record = _download_original(args.url, args.pid, args.key)
    if args.collection:
        upload = requests.post(f'{args.url}/api/dataverses/{args.collection}/datasets',
                               json=_output_json(record),
                               headers={'X-Dataverse-key': args.key},
                               timeout=TIMEOUT)
    else:
        payload = {'metadataBlocks': _output_json(record)['datasetVersion']['metadataBlocks']}
        upload = requests.put(f'{args.url}/api/datasets/:persistentId/versions/:draft',
                               json=payload,
                               headers={'X-Dataverse-key' : args.key},
                               params={'persistentId' : args.replace},
                               timeout=TIMEOUT)

    upload.raise_for_status()

if __name__ == '__main__':
    main()
