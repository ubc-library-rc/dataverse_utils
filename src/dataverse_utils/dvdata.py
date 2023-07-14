'''
Dataverse studies and files
'''

import tempfile
import requests

TIMEOUT = 100

class Study(dict): #pylint: disable=too-few-public-methods
    '''
    Dataverse record. Dataverse study records are pure metadata so this
    is represented with a dictionary.
    '''
    def __init__(self, pid: str,
                 url:str, key:str):
        '''
        pid : str
            Record persistent identifier: hdl or doi
        url : str
            Base URL to host Dataverse instance
        key : str
            Dataverse API key with downloader privileges
        '''
        self['pid'] = pid
        self['url'] = url
        self['key'] = key
        self['orig_json'] = None
        if not self['orig_json']:
            self['orig_json'] = self._orig_json()
        self['upload_json'] = self._upload_json
        self['file_ids'] = [x['dataFile'].get('id') for x in self['orig_json']['files']]
        self['file_persistentIds'] = self._get_file_pids()

    def _orig_json(self) -> dict:
        '''
        Latest study version record JSON. Retrieved from
        Dataverse installation so an internet connection
        is required.
        '''
        #curl -H "X-Dataverse-key:$API_TOKEN" /
        #$SERVER_URL/api/datasets/:persistentId/?persistentId=$PERSISTENT_IDENTIFIER
        getjson = requests.get(self['url']+'/api/datasets/:persistentId',
                               headers={'X-Dataverse-key':self['key']},
                               params = {'persistentId': self['pid']},
                               timeout = TIMEOUT)
        getjson.raise_for_status()
        return getjson.json()['data']['latestVersion']

    @property
    def _upload_json(self)->dict:
        '''
        A Dataverse JSON record with with PIDs and other information stripped
        suitable for upload as a new Dataverse study record.
        '''
        return {'datasetVersion': {'license': self['orig_json']['license'],
                                     'termsOfUse': self['orig_json']['termsOfUse'],
                                     'metadataBlocks': self['orig_json']['metadataBlocks']
                                     }
                  }

    def _get_file_pids(self)->list:
        '''
        Returns a list of file ids representing the file
        objects in dataverse record
        '''
        pids = [x['dataFile'].get('persistentId') for x in self['orig_json']['files']]
        if not all(pids):
            return None
        return pids

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
