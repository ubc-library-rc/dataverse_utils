'''
Utilities for recursively analysing a Dataverse collection
'''

import logging
import requests
from urllib3.util import Retry

LOGGER = logging.getLogger(__name__)
USELESS_KEYS = ['verbose']

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
            self.retry_strategy = Retry(total=10,
                       status_forcelist=[429, 500, 502, 503, 504],
                       allowed_methods=['HEAD', 'GET', 'OPTIONS',
                                         'POST', 'PUT'],
                       backoff_factor=1)
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

    def get_collections(self, coll:str=None, output=None):
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

        LOGGER.info('got info %s', coll)
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

    def get_studies(self, root:str=None, **kwargs):
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
        all_studies = self.get_collection_listing(root, **kwargs)
        #collections = self.get_collections(root, self.url)
        collections = self.get_collections(root)
        for collection in collections:
            all_studies.extend(self.get_collection_listing(collection[1], **kwargs))
        self.studies = all_studies
        return all_studies

    def get_collection_listing(self, coll_id, **kwargs):
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
        out = [(self.get_study_info(pid, collection=coll_id, **kwargs), pid) for pid in pids]
        for _ in out:
            _[0].update({'pid': _[1]})
        return [x[0] for x in out]

    def get_study_info(self, pid, **kwargs):
        '''
        Would it be to much to ask to be able to get info out of
        dataverse without this much crap?
        --------------------
        pid : str
            Persistent ID of a Dataverse study
        kwargs
            verbose : bool
                If True, print pid to stdout
            [any] any other information you need to include with the study,
            for example the collection.
        --------------------
        '''
        if kwargs.get('verbose'):
            print(f'Fetching metadata for {pid}')
        if not self.key:
            meta = self.session.get(f'{self.url}/api/datasets/:persistentId',
                                params={'persistentId': pid})
        else:
            meta = self.session.get(f'{self.url}/api/datasets/:persistentId',
                                params={'persistentId': pid},
                                headers={'X-Dataverse-key':self.key})
        meta.raise_for_status()
        LOGGER.debug(pid)
        return StudyMetadata(meta.json(), **kwargs)

class StudyMetadata(dict):
    '''
    The metadata container for a single study
    '''
    def __init__(self, study_meta:dict, **kwargs):
        '''
        Takes the requests.json() output of a call to {url}/api/datasets/:persistentId.

        The result is a dict with only one level, instead of 13.
        ---
        study_meta : dict
            Dataverse Native JSON from API call

        kwargs
            Anything else you want to include in the dictionary, like, say
            collection. That way you can have any info you want.
        ---
        '''
        self.study_meta  = study_meta
        self.extract_metadata()
        for key in list(kwargs.keys()):
            if key in USELESS_KEYS:
                del kwargs[key]
        self.update(kwargs)

    def extract_metadata(self):
        '''
        Convenience function for parsing the study metadata of the latest version.

        results are written to DvCollection.ez as a dict.
        '''
        for v in self.study_meta['data']['latestVersion']['metadataBlocks'].values():
            for field in v['fields']:
                self.extract_field_metadata(field)

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

if __name__ == '__main__':
    #set(q for x in x.studies for q in x.keys())
    # with open('dv_output_test.tsv', mode='w', newline='\n', encoding='utf-8') as w:
    #     writer=csv.DictWriter(w, fieldnames=sorted(list(set(q for x in x.studies
    #                                                         for q in x.keys()))),
    #delimiter='\t', quoting=csv.QUOTE_MINIMAL)
    #     writer.writeheader()
    #     writer.writerows(x.studies)
    pass
