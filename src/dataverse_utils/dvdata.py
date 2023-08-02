'''
Dataverse studies and files
'''

import tempfile
import hashlib
import os
import logging
import traceback

import requests

TIMEOUT = 100
LOGGER = logging.getLogger(__name__)

class Study(dict): #pylint: disable=too-few-public-methods
    '''
    Dataverse record. Dataverse study records are pure metadata so this
    is represented with a dictionary.
    '''
    def __init__(self, pid: str,
                 url:str, key:str,
                 **kwargs):
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
        self['timeout'] = kwargs.get('timeout',TIMEOUT)
        if not self['orig_json']:
            self['orig_json'] = self._orig_json()
        self['upload_json'] = self._upload_json
        self['file_info'] = self['orig_json']['files']
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
                               timeout = self['timeout'])
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

class File(dict):
    '''
    Class representing a file on a Dataverse instance
    '''
    def __init__(self, url:str, key:str,
                 **kwargs):
        '''
        url : str
            Base URL to host Dataverse instance
        key : str
            Dataverse API key with downloader privileges
        id : int or str
            File identifier; can be a file ID or PID
        args : list
        kwargs : dict

        To initialize correctly, pass a value from Study['file_info'].

        Eg: File('https://test.invalid', 'ABC123', **Study_instance['file_info'][0])

        '''
        self['url'] = url
        self['key'] = key
        self['downloaded'] = False
        self['downloaded_file_name'] = None
        self['downloaded_checksum'] = None
        self['verified'] = None
        #self['dv_file_metadata'] = None
        #    if not self['dv_file_metadata']:
        #        self['dv_file_metadata'] = self._get_file_metadata()
        for keey, val in kwargs.items():
            self[keey] = val
        self['timeout'] = kwargs.get('timeout', TIMEOUT)

    def download_file(self):
        '''
        Downloads the file to a temporary location. Data will be in the ORIGINAL format,
        not Dataverse-processed TSVs
        '''
        if not self['downloaded'] or not os.path.exists(self.get('downloaded_file_name', '')):
            try:
                #curl "$SERVER_URL/api/access/datafile/:persistentId/?persistentId=$PERSISTENT_ID"
                dwnld = requests.get(self['url']+'/api/access/datafile/'+
                                                str(self['dataFile']['id']),
                                     headers={'X-Dataverse-key': self['key']},
                                     params = {'format':'original'},
                                     timeout=self['timeout'])
                with tempfile.NamedTemporaryFile(delete=False) as fil:
                    self['downloaded_file_name'] = fil.name
                    fil.write(dwnld.content)
                self['downloaded'] = True
                return True

            except requests.exceptions.HTTPError as err:
                LOGGER.exception(err)
                LOGGER.exception(traceback.format_exc())
                self['downloaded'] = False
                return False
        return None

    def del_tempfile(self):
        '''
        Delete tempfile if it exists
        '''
        if os.path.exists(self['downloaded_file_name']):
            os.remove(self['downloaded_file_name'])
            self['downloaded'] = False
            self['downloaded_file_name'] = None
            self['verified'] = None

    def produce_digest(self, prot: str = 'md5', blocksize: int = 2**16) -> str:
        '''
        Returns hex digest for object

            fname : str
               Path to a file object

            prot : str
               Hash type. Supported hashes: 'sha1', 'sha224', 'sha256',
                  'sha384', 'sha512', 'blake2b', 'blake2s', 'md5'.
                  Default: 'md5'

            blocksize : int
               Read block size in bytes
        '''
        if not self['downloaded_file_name']:
            return None
        ok_hash = {'sha1' : hashlib.sha1(),
                   'sha224' : hashlib.sha224(),
                   'sha256' : hashlib.sha256(),
                   'sha384' : hashlib.sha384(),
                   'sha512' : hashlib.sha512(),
                   'blake2b' : hashlib.blake2b(),
                   'blake2s' : hashlib.blake2s(),
                   'md5': hashlib.md5()}
        with open(self['downloaded_file_name'], 'rb') as _fobj:
            try:
                _hash = ok_hash[prot]
            except (UnboundLocalError, KeyError) as err:
                message = ('Unsupported hash type. Valid values are '
                           f'{list(ok_hash)}.' )
                LOGGER.exception(err)
                LOGGER.exception(message)
                LOGGER.exception(traceback.format_exc())
                raise

            fblock = _fobj.read(blocksize)
            while fblock:
                _hash.update(fblock)
                fblock = _fobj.read(blocksize)
            return _hash.hexdigest()

    def verify(self)->None:
        '''
        Compares checksum with stated checksum
        '''
        if not self.get('downloaded_file_name') or not self.get('downloaded'):
            LOGGER.error('File has not been downloaded')
            self['verified'] = None
            self['downloaded_checksum'] = None
            return None
        _hash = self.produce_digest(self['dataFile']['checksum']['type'].lower())
        if _hash == self['dataFile']['checksum']['value']:
            self['verified'] = True
            self['downloaded_checksum'] = hash
            return True
        LOGGER.error('Checksum mismatch in %s', self.get('label'))
        self['verified'] = False
        self['downloaded_checksum'] = _hash
        return False
