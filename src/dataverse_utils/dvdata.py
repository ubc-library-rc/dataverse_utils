'''
Dataverse studies and files
'''

import tempfile
import requests

TIMEOUT = 100

class Study:
    '''
    Dataverse record
    '''
    def __init__(self, pid: str,
                 url:str, key:str,
                 *args, **kwargs):
        '''
        pid : str
            Record persistent identifier: hdl or doi
        url : str
            Base URL to host Dataverse instance
        key : str
            Dataverse API key with downloader privileges
        '''
        self.pid = pid
        self.url = url
        self.key = key

    @property
    def orig_json(self) -> dict:
        '''
        Latest study version record JSON. Retrieved from
        Dataverse installation so an internet connection
        is required.
        '''
        #curl -H "X-Dataverse-key:$API_TOKEN" /
        #$SERVER_URL/api/datasets/:persistentId/?persistentId=$PERSISTENT_IDENTIFIER
        getjson = requests.get(self.url+'/api/datasets/:persistentId',
                               headers={'X-Dataverse-key':self.key},
                               params = {'persistentId': self.pid},
                               timeout = TIMEOUT)
        getjson.raise_for_status()
        return getjson.json()['data']['latestVersion']

    @property
    def upload_json(self)->dict:
        '''
        A Dataverse JSON record with with PIDs and other information stripped
        suitable for upload as a new Dataverse study record.
        '''
        return {'datasetVersion': {'license': self.orig_json['license'],
                                     'termsOfUse': self.orig_json['termsOfUse'],
                                     'metadataBlocks': self.orig_json['metadataBlocks']
                                     }
                  }

    def get_file_ids(self, rec_json: dict)->list:
        '''
        Returns a list of file ids representing the file
        objects in dataverse record
        '''

class File:
    '''
    Class representing a file on a Dataverse instance
    '''
    def __init__(self, url:str, key:str,
                 in_json:dict,
                 *args, **kwargs):
        '''
        url : str
            Base URL to host Dataverse instance
        key : str
            Dataverse API key with downloader privileges
        in_json : dict
            Dataverse study metadata record JSON as Python dict
        '''
        self.url = url
        self.key = key
        self.in_json = in_json
        self.downloaded_file = None
