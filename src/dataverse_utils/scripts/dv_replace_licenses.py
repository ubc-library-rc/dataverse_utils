'''
Replace all licence in a study with one read from an external
markdown file. This requires using a different API, the
"semantic metadata api"
https://guides.dataverse.org/en/5.6/developers/
dataset-semantic-metadata-api.html

'''
import argparse
import json
import markdown
import requests

VERSION = (0, 1, 0)
__version__ = '.'.join([str(x) for x in VERSION])

def parsley() -> argparse.ArgumentParser() :
    '''
    parse the command line
    '''
    description = ('Replaces the license text in a '
                  'Dataverse study and republishes it '
                  'as the same version. '
                  'Superuser privileges are required for '
                  'republishing as the version is not incremented.'
                  'This software requires the Dataverse installation '
                  'to be running Dataverse software version >= 5.6.')
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('studies', nargs='+', help='Persistent IDs of studies')
    parser.add_argument('-u', '--url',
                        help=('Base URL of Dataverse installation'
                              'Defaults to "https://abacus.library.ubc.ca"'),
                        default='https://abacus.library.ubc.ca')
    parser.add_argument('-l', '--license', help='License file in Markdown format',
                        required=True, dest='lic')
    parser.add_argument('-k', '--key', help='Dataverse API key',
                        required=True)
    parser.add_argument('-r', '--republish',
                        help='Republish study without incrementing version',
                        action='store_true')
    parser.add_argument('--version', action='version',
                        version='%(prog)s '+__version__,
                        help='Show version number and exit')
    return parser

def replace_licence(hdl, lic, key,
                    url='https://abacus.library.ubc.ca'):
    '''
    Replace the licence for a dataverse study with
    persistent ID hdl.

    ---
    hdl : str
        Dataverse persistent ID
    lic : str
        License text in markdown format
    key : str
        Dataverse API key
    url : str
        Dataverse installation base URL
    '''

    headers={'X-Dataverse-key' : key,
             'Content-Type': 'application/ld+json'}
    params = {'persistentId': hdl, 'replace': 'true'}
    data = {'dvcore:termsOfUse' : markdown.markdown(lic),
            '@context' : {'dvcore' : 'https://dataverse.org/schema/core#'}}
    req = requests.put(f'{url}/api/datasets/:persistentId/metadata',
                       headers=headers, params=params,
                       json=data)
    try:
        req.raise_for_status()
        return req.json()
    except requests.exceptions.HTTPError:
        return {'status': 'ERROR',
                'data': {'ErrorType' : f'{req.status_code}: {req.reason}'}}

def republish(hdl, key, url='https://abacus.library.ubc.ca'):
    '''
    Republish study without updating version

    ---
    hdl : str
        Persistent Id
    key : str
        Dataverse API key
    url : str
        Dataverse installation base URL
    '''
    headers = {'X-Dataverse-key' : key}
    params = {'persistentId' : hdl, 'type':'updatecurrent'}
    req = requests.post(f'{url}/api/datasets/:persistentId/actions/:publish',
                        headers=headers, params=params)
    try:
        req.raise_for_status()
        return req.json()
    except requests.exceptions.HTTPError:
        try:
            req.json()
        except json.decoder.JSONDecodeError:
            return {'status': 'ERROR',
                    'data': {'ErrorType' : f'{req.status_code}: {req.reason}'}}
        return req.json()

def print_stat(rjson):
    '''
    Prints error status to stdout
    '''
    print(rjson.get('status',''))
    print(rjson.get('data',''))
    print(rjson.get('message',''))

def main():
    '''
    Main script function
    '''
    parse = parsley()
    args = parse.parse_args()
    args.url = args.url.strip('/ ')
    with open(args.lic) as fil:
        newlic = fil.read()
    for pid in args.studies:
        print(f'Changing license for {pid}')
        rep = replace_licence(pid, newlic, args.key, args.url)
        print_stat(rep)
        if args.republish:
            print(f'Republishing {pid}')
            pub = republish(pid, args.key, args.url)
            print_stat(pub)

if __name__ == '__main__':
    main()
