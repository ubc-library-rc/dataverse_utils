'''
Dataverse studies and files
'''

import tempfile
import hashlib
import os
import logging
import pathlib
import traceback

import requests
from dataverse_utils import UAHEADER

TIMEOUT = 100
LOGGER = logging.getLogger(__name__)

class Study(dict): #pylint:  disable=too-few-public-methods
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
        self.__key = key
        self['orig_json'] = None
        self['timeout'] = kwargs.get('timeout',TIMEOUT)
        if not self['orig_json']:
            self['orig_json'] = self._orig_json()
        self['upload_json'] = self._upload_json
        self['file_info'] = self['orig_json']['files']
        self['file_ids'] = [x['dataFile'].get('id') for x in self['orig_json']['files']]
        self['file_persistentIds'] = self._get_file_pids()
        self['source_version'] = Study.get_version(url)
        self['target_version'] = None
        if not self['target_version']:
            self['target_version'] = Study.get_version(url)

    @classmethod
    def get_version(cls, url:str, timeout:int=100)->float:
        '''
        Returns a float representing a Dataverse version number.
        Floating point value composed of:
        float(f'{major_version}.{minor_verson:03d}{patch:03d}')
        ie, version 5.9.2 would be 5.009002
        url : str
            URL of base Dataverse instance. eg: 'https://abacus.library.ubc.ca'
        timeout : int
            Request timeout in seconds
        '''
        ver = requests.get(f'{url}/api/info/version',
                           headers=UAHEADER,
                           #headers = {'X-Dataverse-key' : key},
                           timeout = timeout)
        try:
            ver.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            LOGGER.error(r'Error getting version for {url}')
            LOGGER.exception(exc)
            LOGGER.exception(traceback.format_exc())
            raise requests.exceptions.HTTPError
        #Scholars Portal version is formatted as v5.13.9-SP, so. . .
        verf = ver.json()['data']['version'].strip('v ').split('.')
        verf = [x.split('-')[0] for x in verf]
        verf =[int(b)/10**(3*a) for a,b in enumerate(verf)]
        #it's 3*a in case for some reason we hit, say v5.99.99 and there's more before v6.
        verf = sum(verf)
        return verf

    def set_version(self, url:str, timeout:int=100)->None:
        '''
        Sets self['target_version'] to appropriate integer value *AND*
        formats self['upload_json'] to correct JSON format

        url : str
            URL of *target* Dataverse instance
        timeout : int
            request timeout in seconds
        '''
        self['target_version'] = Study.get_version(url, timeout)
        # Now fix the metadata to work with various versions
        if self['target_version'] >= 5.010:
            self.fix_licence()
        if self['target_version'] >= 5.013:
            self.production_location()

    def _orig_json(self) -> dict:
        '''
        Latest study version record JSON. Retrieved from
        Dataverse installation so an internet connection
        is required.
        '''
        #curl -H "X-Dataverse-key:$API_TOKEN" /
        #$SERVER_URL/api/datasets/:persistentId/?persistentId=$PERSISTENT_IDENTIFIER
        headers = {'X-Dataverse-key' : self.__key}
        headers.update(UAHEADER)
        getjson = requests.get(self['url']+'/api/datasets/:persistentId',
                               headers=headers,
                               params = {'persistentId': self['pid']},
                               timeout = self['timeout'])
        getjson.raise_for_status()
        return getjson.json()['data']['latestVersion']

    def __add_email(self, upjson):
        '''
        Adds contact information if it's not there. Fills with dummy data
        '''
        #pylint: disable=possibly-used-before-assignment
        for n, v in enumerate((upjson['datasetVersion']
                              ['metadataBlocks']['citation']['fields'])):
            if v['typeName'] == 'datasetContact':
                contact_no = n
        for _x in (upjson['datasetVersion']['metadataBlocks']
                  ['citation']['fields'][contact_no]['value']):
            if not _x.get('datasetContactEmail'):
                _x['datasetContactEmail'] = {'typeName':'datasetContactEmail',
                                              'multiple': False,
                                              'typeClass':'primitive',
                                              'value': 'suppressed_value@test.invalid'}
        return upjson

    @property
    def _upload_json(self)->dict:
        '''
        A Dataverse JSON record with with PIDs and other information stripped
        suitable for upload as a new Dataverse study record.
        '''
        upj = {'datasetVersion': {'license': self['orig_json']['license'],
                                     'termsOfUse': self['orig_json'].get('termsOfUse',''),
                                     'metadataBlocks': self['orig_json']['metadataBlocks']
                                     }
                  }
        return self.__add_email(upj)

    @property
    def _oldupload_json(self)->dict:
        '''
        A Dataverse JSON record with with PIDs and other information stripped
        suitable for upload as a new Dataverse study record.
        '''
        return {'datasetVersion': {'license': self['orig_json']['license'],
                                     'termsOfUse': self['orig_json'].get('termsOfUse',''),
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

    ######
    #JSON metdata fixes for different versions
    ######
    def fix_licence(self)->None:
        '''
        With Dataverse v5.10+, a licence type of 'NONE' is now forbidden.
        Now, as per <https://guides.dataverse.org/en/5.14/api/sword.html\
        ?highlight=invalid%20license>,
        non-standard licences may be replaced with None.

        This function edits the same Study object *in place*, so returns nothing.
        '''
        if self['upload_json']['datasetVersion']['license'] == 'NONE':
            self['upload_json']['datasetVersion']['license'] = None

        if not self['upload_json']['datasetVersion']['termsOfUse']:
            #This shouldn't happen, but UBC has datasets from the early 1970s
            self['upload_json']['datasetVersion']['termsOfUse'] = 'Not available'

    def production_location(self)->None:
        '''
        Changes "multiple" to True where typeName == 'productionPlace' in
        Study['upload_json'] Changes are done
        *in place*.
        This change came into effect with Dataverse v5.13
        '''
        #{'typeName': 'productionPlace', 'multiple': True, 'typeClass': 'primitive',
        #'value': ['Vancouver, BC', 'Ottawa, ON']}

        # get index
        indy = None
        for ind, val in enumerate(self['upload_json']['datasetVersion']\
                                      ['metadataBlocks']['citation']['fields']):
            if val['typeName'] == 'productionPlace':
                indy = ind
                break

        if indy and not self['upload_json']['datasetVersion']['metadataBlocks']\
                ['citation']['fields'][indy]['multiple']:
            self['upload_json']['datasetVersion']['metadataBlocks']\
                ['citation']['fields'][indy]['multiple'] = True
            self['upload_json']['datasetVersion']['metadataBlocks']\
                ['citation']['fields'][indy]['value'] = [self['upload_json']['datasetVersion']\
                                                         ['metadataBlocks']['citation']\
                                                         ['fields'][indy]['value']]

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
        self.__key = key
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

            headers = headers={'X-Dataverse-key':self.__key}
            headers.update(UAHEADER)
            try:
                #curl "$SERVER_URL/api/access/datafile/:persistentId/?persistentId=$PERSISTENT_ID"
                dwnld = requests.get(self['url']+'/api/access/datafile/'+
                                                str(self['dataFile']['id']),
                                     headers=headers,
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

class FileInfo(dict):
    '''

    An object representing all of a dataverse study's files.
    Easily parseable as a dict.

    data_chunk : dict
        Metadata block;  the JSON output of a call to
        [server]/api/datasets/:persistentId/versions
    server: str
        Base URL of dataverse server (like 'https://abacus.library.ubc.ca')
    '''
    #Should this be incorporated into the above class? Probably.
    def __init__(self, **kwargs)->None:
        '''
        Required keyword parameters:

        url : str
            Base URL of dataverse installation
        pid : str
            Handle or DOI of study

        Optional keyword parameters:

        apikey : str
            Dataverse API key; required for DRAFT or restricted material
        timeout : int
            Optional timeout in seconds
        '''
        self.kwargs = kwargs
        self['version_list'] = []
        self.dv = None
        self._get_json()
        self._get_all_files()
        self['headers'] = list(self[self['current_version']][0].keys())

    def _get_json(self) -> None:
        '''
        Get study file json
        '''
        try:
            headers={'X-Dataverse-key' : self.kwargs.get('apikey')}
            headers.update(UAHEADER)
            params = {'persistentId': self.kwargs['pid']}
            self.dv = requests.get(f'{self.kwargs["url"]}/api/datasets/:persistentId/versions',
                                   params=params,
                                   timeout=self.kwargs.get('timeout', 100),
                                   headers=headers)
            self.dv.raise_for_status()
        except (requests.exceptions.RequestException,
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
                requests.exceptions.TooManyRedirects,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.Timeout,
                requests.exceptions.JSONDecodeError,
                requests.exceptions.InvalidSchema) as err:

            err.add_note(f'Connection error: {"\n".join((str(x) for x in err.args))}')
            msg = '\n'.join(getattr(err, '__notes__', []))
            LOGGER.critical(msg)
            raise err

    def _get_all_files(self):
        '''
        Iterates over self.data_chunk. to produce a list of files
        in self['files']
        '''
        try:
            for num, version in enumerate(self.dv.json()['data']):
                self._get_version_files(version, current=num)

        except AttributeError as err:
            err.add_note('No JSON present')
            #LOGGER.exception('FileInfo AttributeError: %s', err)
            #LOGGER.exception(traceback.format_exc())
            raise err

        except KeyError as err:
            err.add_note(f'JSON parsing error: {err}')
            err.add_note('Offending JSON:')
            err.add_note(f'{self.dv.json()}')
            msg = '\n'.join(getattr(err, '__notes__', []))
            LOGGER.exception('FileInfo KeyError: %s', msg)
            #LOGGER.exception(traceback.format_exc())
            raise err
    def _get_version_files(self, flist: list, current=1)->None:
        '''
        Set version number and assign file info a version key

        flist : list
            list of file metadata for a particular version
        current: int
            Value of zero represents most current version

        '''
        if flist['versionState'] == 'DRAFT':
            ver_info='DRAFT'
        else:
            ver_info = f"{flist['versionNumber']}.{flist['versionMinorNumber']}"
        if current == 0:
            self['current_version'] = ver_info
        self['version_list'].append(ver_info)
        self[ver_info] = []
        for fil in flist['files']:
            self[ver_info].append(self._get_file_info(fil,
                                                     ver_info=ver_info,
                                                     state_info=flist['versionState']))

    def _get_file_info(self, file:dict, **kwargs)->dict:
        '''
        Returns a dict of required info from a chunk of dataverse study
        version metadata

        file : dict
            The dict containing one file's metadata
        ---
        Keyword arguments
        version_info: str
            Version info string
        state_info : str
            Publication state
        '''
        # headers = ['file', 'description', 'pidURL','downloadURL', 'version', 'state']
        file_name = file['dataFile'].get('originalFileName', file['label'])
        filepath = pathlib.Path(file.get('directoryLabel', ''), file_name)
        description = file.get('description', '')
        try:
            pid_url = file['dataFile']['pidURL']
        except KeyError:
            pid_url = f'{self.kwargs["url"]}/file.xhtml?fileId={file["dataFile"]["id"]}'
        fid = file['dataFile']['id']
        download_url = f'{self.kwargs["url"]}/api/access/datafile/{fid}?format=original'
        out = {'file': str(filepath).strip(),
               'description': description.strip(),
               'pid_url': pid_url, 'download_url':download_url,
               'version': kwargs['ver_info'],
               'state' : kwargs['state_info']}
        return out
