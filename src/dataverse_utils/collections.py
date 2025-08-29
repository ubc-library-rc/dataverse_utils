'''
Utilities for recursively analysing a Dataverse collection
'''

import logging
import requests
from urllib3.util import Retry

LOGGER = logging.getLogger(__name__)
RETRY = Retry(total=10,
                       status_forcelist=[429, 500, 502, 503, 504],
                       allowed_methods=['HEAD', 'GET', 'OPTIONS',
                                         'POST', 'PUT'],
                       backoff_factor=1)

class MetadataError(Exception):
    '''
    MetadataError
    '''

class DvCollection:
    '''
    Metadata for an *entire* dataverse collection, recursively.
    '''
    #pylint: disable=too-many-instance-attributes
    def __init__(self, url:str, coll:str, key=None, **kwargs):
        '''
        All you need to start recursively crawling.
        --------------------
        coll : str
            short collection name or id number
        url : str
            base URL of Dataverse collection.
            eg: https://borealisdata.ca
                borealisdata.ca
        key : str
            API key (optional, only use if you want to see hidden material)

        Optional kwargs:
            timeout : int
                retry timeout in seconds
        --------------------
        '''
        self.coll = coll
        self.url = self.__clean_url(url)
        self.headers = None
        self.key = key
        if self.key:
            self.headers = {'X-Dataverse-key': self.key}
        if not kwargs.get('retry'):
            self.retry_strategy = RETRY
        else:
            self.retry_strategy = kwargs['retry']
        self.session = requests.Session()
        self.session.mount('https://',
                           requests.adapters.HTTPAdapter(max_retries=self.retry_strategy))
        self.collections = None
        self.studies = None
    
    def __clean_url(self, badurl:str):
        '''
        Sanitize URL
        --------
        badurl: str
            URL

        -------
        '''
        clean = badurl.strip().strip('/')
        if not clean.startswith('https://'):
            clean = f'https://{clean}'
        return clean

    def __get_shortname(self, dvid):
        '''
        Get collection short name
        '''
        shortname = self.session.get(f'{self.url}/api/dataverses/{dvid}')
        shortname.raise_for_status()
        return shortname.json()['data']['alias']

    def get_collections(self, coll:str=None, output=None, **kwargs):
        '''
        Get a listing of all dataverses in a collection
        So difficult
        --------------------
        coll : str
            Collection short name or id
        
        --------------------
        
        '''
        if not output:
            output = []
        if not coll:
            coll = self.coll
        x = self.session.get(f'{self.url}/api/dataverses/{coll}/contents',
                                 headers=self.headers) if self.headers\
            else self.session.get(f'{self.url}/api/dataverses/{coll}/contents')
        x.raise_for_status()
        data = x.json().get('data')
        dvs =  [(_['title'], self.__get_shortname(_['id'])) for _ in data if _['type']=='dataverse']
        #breakpoint()
        if not dvs:
            dvs = []
        output.extend(dvs)
        for dv in dvs:
            LOGGER.debug('%s/api/dataverses/%s/contents', self.url, dv[1])
            LOGGER.debug('recursive')
            #breakpoint()
            self.get_collections(dv[1], output)
        self.collections = output
        return output

    def get_studies(self, root:str=None):
        '''
        return [(pid, title)..(pid_n, title_n)] of a collection
        --------------------
        root : str
            Short name or id of *top* level of tree. Default self.coll
        --------------------
        '''
        all_studies = []
        if not root:
            root=self.coll
        all_studies = self.get_collection_listing(root)
        #collections = self.get_collections(root, self.url)
        collections = self.get_collections(root)
        for collection in collections:
            all_studies.extend(self.get_collection_listing(collection[1]))
        self.studies = all_studies
        return all_studies

    def get_collection_listing(self, coll_id):
        '''
        return a listing of studies in a collection, with pid
        --------------------
        coll_id : str
            Short name or id of a dataverse collection
        --------------------
        '''
        cl = self.session.get(f'{self.url}/api/dataverses/{coll_id}/contents',
                                  headers={'X-Dataverse-key':self.key}) if self.headers\
             else self.session.get(f'{self.url}/api/dataverses/{coll_id}/contents')
        cl.raise_for_status()
        #pids = [z['persistentUrl'] for z in cl.json()['data'] if z['type'] == 'dataset']
        pids = [f"{z['protocol']}:{z['authority']}/{z['identifier']}"
                for z in cl.json()['data'] if z['type'] == 'dataset']
        out = [(self.get_study_info(pid), pid) for pid in pids]
        for _ in out:
            _[0].update({'pid': _[1]})
        return [x[0] for x in out]

    def get_study_info(self, pid):
        '''
        Would it be to much to ask to be able to get info out of
        dataverse without this much crap?
        --------------------
        pid : str
            Persistent ID of a Dataverse study
        --------------------
        '''
        if not self.key:
            meta = self.session.get(f'{self.url}/api/datasets/:persistentId',
                                params={'persistentId': pid})
        else:
            meta = self.session.get(f'{self.url}/api/datasets/:persistentId',
                                params={'persistentId': pid},
                                headers={'X-Dataverse-key':self.key})
        meta.raise_for_status()
        LOGGER.debug(pid)
        return StudyMetadata(study_meta=meta.json())

class StudyMetadata(dict):
    '''
    The metadata container for a single study
    '''
#    def __init__(self, study_meta:dict):
#        '''
#        Takes the requests.json() output of a call to {url}/api/datasets/:persistentId.
#
#        The result is a dict with only one level, instead of 13.
#        ---
#        study_meta : dict
#            Dataverse Native JSON from API call
#        ---
#        '''
#        self.study_meta  = study_meta
#        self.extract_metadata()
#        self.__files = None

    def __init__(self, **kwargs):
        '''
        kwargs: At least one of:

            study_meta: dict
                The dataverse study metadata JSON
        
            OR
            
            url:  str
                Base URL to dataverse instance
            pid: str
                Persistent ID of a study

            Optionally:
                key: str
                Dataverse instance API key (needed for unpublished studies)
            
        '''
        self.kwargs = kwargs
        self.study_meta  = kwargs.get('study_meta')
        self.url = kwargs.get('url')
        self.pid = kwargs.get('pid')
        if not (('study_meta' in kwargs) or ('url' in kwargs and 'pid' in kwargs)):
            raise TypeError('At least one of a URL/pid combo (url, pid) or '
            'study metadata json (study_meta) is required.')
        if not self.study_meta:
            self.study_meta = self.__obtain_metadata()
        try:
            self.extract_metadata()
        except KeyError as e:
            raise MetadataError(f'Unable to parse study metadata. Do you need an API key?\n'
                           f'{e} key not found.\n'
                           f'Offending JSON: {self.study_meta}') from e
        self.__files = None

    def __obtain_metadata(self):
        '''
        Obtain study metadata as required
        '''
        headers = {'X-Dataverse-key':self.kwargs.get('key')}
        params = {'persistentId': self.pid}
        self.session = requests.Session()
        self.session.mount('https://',
                           requests.adapters.HTTPAdapter(max_retries=RETRY))
        self.url = self.url.strip('/')
        if not self.url.startswith('https://'):
            self.url = f'https://{self.url}'
        data = self.session.get(f'{self.url}/api/datasets/:persistentId',
                                headers=headers, params=params)
        return data.json()


    def extract_metadata(self):
        '''
        Convenience function for parsing the study metadata of the latest version.

        results are written to DvCollection.ez as a dict.
        '''

        for v in self.study_meta['data']['latestVersion']['metadataBlocks'].values():
            for field in v['fields']:
                self.extract_field_metadata(field)
        self.__extract_licence_info()
        self.__version()
        #['data']['latestVersion']['versionNumber']
        #['data']['latestVersion']['versionMinorNumber']

    def extract_field_metadata(self, field):
        '''
        Extract the metadata from a single field and make it into a human-readable dict.
        Output updates self.ez
        '''
        #pylint: disable=too-many-branches, too-many-nested-blocks
        #typeClass: compound = dict, primitive = string
        #multiple: false= one thing, true=list
        # so typeClass:compound AND multiple:true = a list of dicts.
        # also, typeClass can be "controlledVocabulary" because reasons.
        #is this crap recursive or is one level enough?
        #[[x['typeName'], x['typeClass'], x['multiple']] for x in citation['fields']]
        # {('primitive', False), ('compound', True), ('compound', False),
        # ('primitive', True), ('controlledVocabulary', True)}
        if not field['multiple']:
            if field['typeClass']=='primitive':
                self.update({field['typeName']: field['value']})
            if field['typeClass'] == 'compound':
                #breakpoint()
                for v2 in field['value']:
                    #breakpoint()
                    self.extract_field_metadata(field['value'][v2])
        if field['multiple']:
            if field['typeClass'] == 'compound':
                #produce a list of similar values concatenated
                for v3 in field['value']:
                    interim = {}
                    for insane_dict in field['value']:
                        for v3 in insane_dict.values():
                            #breakpoint()
                            if interim.get(v3['typeName']):
                                interim.update({v3['typeName']:
                                                interim[v3['typeName']]+ [v3['value']]})
                            else:
                                #sometimes value is None because reasons.
                                interim[v3['typeName']] = [v3.get('value', [] )]
                            LOGGER.debug(interim)
                for k9, v9 in interim.items():
                    self.update({k9: '; '.join(v9)})

            if field['typeClass'] == 'primitive':
                self.update({field['typeName'] :  '; '.join(field['value'])})

        if field['typeClass'] == 'controlledVocabulary':
            if isinstance(field['value'], list):
                self.update({field['typeName'] : '; '.join(field['value'])})
            else:
                self.update({field['typeName'] : field['value']})
        # And that should cover every option!
    @property
    def files(self):
        '''
        Return a list of of dicts with file metadata
        '''
        if not self.__files:
            self.__extract_files()
        return self.__files

    def __extract_files(self):
        '''
        Extract file level metadata
        '''
        #Note: ALL other dict values for this object are single values,
        #but files would (usually) be an arbitrary number of files.
        #That bothers me on an intellectual level. Therefore, it will be attribute.
        #Iterate over StudyMetadata.files if you want to know the contents
        if not self.__files:
            outie = []
            for v in self.study_meta['data']['latestVersion']['files']:
                innie = {}
                innie['filename'] = v['dataFile'].get('originalFileName', v['dataFile']['filename'])
                innie['file_label'] = v.get('label')
                innie['description'] = v.get('description')
                innie['filesize_bytes'] = v['dataFile'].get('originalFileSize',
                                                             v['dataFile']['filesize'])
                innie['chk_type'] = v['dataFile']['checksum']['type']
                innie['chk_digest'] =v['dataFile']['checksum']['value']
                innie['id'] = v['dataFile']['id']
                innie['pid'] = v['dataFile'].get('persistentId')
                innie['has_tab_file'] = v['dataFile'].get('tabularData', False)
                innie['study_pid'] = (f"{self.study_meta['data']['protocol']}:"
                                     f"{self.study_meta['data']['authority']}/"
                                     f"{self.study_meta['data']['identifier']}")
                outie.append(innie)
            self.__files = outie

    def __extract_licence_info(self):
        '''
        Extract all the licence information fields and add them *if present*
        '''
        lic_fields = ('termsOfUse',
                      'confidentialityDeclaration',
                      'specialPermissions',
                      'restrictions',
                      'citationRequirements',
                      'depositorRequirements',
                      'conditions',
                      'disclaimer',
                      'dataAccessPlace',
                      'originalArchive',
                      'availabilityStatus',
                      'contactForAccess',
                      'sizeOfCollection',
                      'studyCompletion',
                      'fileAccessRequest')
        for field in self.study_meta['data']['latestVersion']:
            if field in lic_fields:
                self[field] = self.study_meta['data']['latestVersion'][field]
        common_lic = self.study_meta['data']['latestVersion'].get('license')
        if isinstance(common_lic, str) and common_lic != 'NONE':
            self['licence'] = common_lic
        elif isinstance(common_lic, dict):
            self['licence'] = self.study_meta['data']['latestVersion']['license'].get('name')
            link = self.study_meta['data']['latestVersion']['license'].get('uri')
            if link:
                self['licence_link'] = link

    def __version(self):
        '''
        Obtain the current version and add it to self
        '''
        if self.study_meta['data']['latestVersion']['versionState'] == 'RELEASED':
            self['study_version'] = (f"{self.study_meta['data']['latestVersion']['versionNumber']}."
                           f"{self.study_meta['data']['latestVersion']['versionMinorNumber']}")
            return
        self['study_version'] = self.study_meta['data']['latestVersion']['versionState']
        return

if __name__ == '__main__':
    #set(q for x in x.studies for q in x.keys())
    # with open('dv_output_test.tsv', mode='w', newline='\n', encoding='utf-8') as w:
    #     writer=csv.DictWriter(w, fieldnames=sorted(list(set(q for x in x.studies
    #                                                         for q in x.keys()))),
    #delimiter='\t', quoting=csv.QUOTE_MINIMAL)
    #     writer.writeheader()
    #     writer.writerows(x.studies)
    pass
