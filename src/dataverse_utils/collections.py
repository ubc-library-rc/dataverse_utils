'''
Utilities for recursively analysing a Dataverse collection
'''
import logging
import string
import warnings

import markdown_pdf
import requests
from urllib3.util import Retry

#README
import bs4

import markdownify

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

    def get_collections(self, coll:str=None, output=None, **kwargs):# pylint:disable=unused-argument
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
        if not dvs:
            dvs = []
        output.extend(dvs)
        for dv in dvs:
            LOGGER.debug('%s/api/dataverses/%s/contents', self.url, dv[1])
            LOGGER.debug('recursive')
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
                for v2 in field['value']:
                    self.extract_field_metadata(field['value'][v2])
        if field['multiple']:
            if field['typeClass'] == 'compound':
                #produce a list of similar values concatenated
                for v3 in field['value']:
                    interim = {}
                    for insane_dict in field['value']:
                        for v3 in insane_dict.values():
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
                      'depositorRequirements', 'conditions',
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
                self['licenceLink'] = link

    def __version(self):
        '''
        Obtain the current version and add it to self
        '''
        if self.study_meta['data']['latestVersion']['versionState'] == 'RELEASED':
            self['studyVersion'] = (f"{self.study_meta['data']['latestVersion']['versionNumber']}."
                           f"{self.study_meta['data']['latestVersion']['versionMinorNumber']}")
            return
        self['studyVersion'] = self.study_meta['data']['latestVersion']['versionState']
        return

class ReadmeCreator:
    '''
    Make a formatted README document out of study metadata
    '''
    #TODO: Should this even be in this file? Separate? Completely separate?
    #TODO: Add: DOI, current date, reorder geospatial metadata to be sane. Plus files
    #Use pyreadstat, damage, pandas or all of the above to get file level metadata
    def __init__(self, study_metadata_obj: StudyMetadata, **kwargs):
        '''
        Send in StudyMetadata dict to create a nicely formatted README document
        '''
        self.meta = study_metadata_obj
        self.kwargs = kwargs
        warnings.filterwarnings('ignore', category=bs4.MarkupResemblesLocatorWarning)
        #These values are the first part of the keys that need
        #concatenation to make them more legible.
        self.concat = ['author', 'datasetContact','otherId', 'keyword', 'topic', 'publication',
                       'producer', 'production', 'distributor', 'series', 'software',
                       'dsDescription', 'grant', 'contributor']

    def __html_to_md(self, inval)->str:
        '''
        Convert any HTML to markdown, or as much as possible
        '''
        if isinstance(inval, str):
            #markdownify kwargs are here:
            #https://github.com/matthewwithanm/python-markdownify
            return markdownify.markdownify(inval)
        return str(inval)

    def make_md_heads(self, inkey:str)->str:
        '''
        Because we want the things to be nice
        '''
        section_heads = {'Title':'## ',
                        'Description':'**Description**\n\n',
                        'Licence': '### Licence\n\n',
                        'Terms of Use': '### Terms of Use\n\n'}
        if inkey in section_heads:
            return section_heads[inkey]
        multi = [self.rename_field(_) for _ in  self.concat]
        if inkey in multi:
            if inkey not in ['Series', 'Software', 'Production']:
                return f'{inkey}(s):  \n'
            return f'{inkey}:  \n'
        return f'{inkey}: '

    @property
    def file_metadata_md(self):
        '''
        Produce pretty markdown for file metadata
        '''
        fmeta = []
        for fil in self.meta.files:
            fileout = {}
            fileout['File'] = fil['filename']
            for k, v in fil.items():
                fileout[k.capitalize().replace('_',' ').replace('Pid', 'Persistent Identifier')] = v
            fileout['Message digest'] = f'{fileout["Chk type"]}: {fileout["Chk digest"]}'
            for rem in ['Chk type', 'Chk digest', 'Id', 'Has tab file', 'Study pid',
                        'File label', 'Filename']:
                del fileout[rem]
            fmeta.append(fileout)

    
        outtmp = []
        for li in fmeta:
            outtmp.append('  \n'.join(f'{k}: {v}' for k, v in li.items()))
        return '\n\n'.join(outtmp)
        #return fmeta

    @property
    def readme_md(self)->str:
        '''
        Generate a markdown readme string
        '''
        metatmp = self.meta.copy()
        neworder = self.reorder_fields(metatmp)
        addme = self.concatenator(metatmp)
        metatmp.update(addme)
        out = {_:None for _ in neworder} # A new dictionary with the correct order
        for k, v in metatmp.items():
            out[k]=v
        #Now remove keys that should be gone
        for rem in self.concat:
            out = {k:v for k,v in out.items()
                       if not (k.startswith(rem) and len(k) > len(rem))}

        fout = {self.rename_field(k): self.__fix_relation_type(self.__html_to_md(v))
                for k, v in out.items()}


        outstr =  '\n\n'.join(f'{self.make_md_heads(k)}{v}' for k, v in fout.items())
        outstr += '\n\n## File information\n\n'
        outstr += self.file_metadata_md

        return outstr

    def __fix_relation_type(self, badstr:str)->str:
        '''
        For some reason, Dataverse puts camelCase values in the 'values' field
        for publication relation. This will make it more readable.
        '''
        fixthese = ['IsCitedBy', 'IsSupplementTo', 'IsSupplementedBy', 'IsReferencedBy']
        for val in fixthese:
            badstr=badstr.replace(val, self.rename_field(val))
        return badstr

    def reorder_fields(self, indict)->list:
        '''
        Create a new dictionary with the keys in the right order
        '''
        fieldlist = list(indict)
        for val in self.concat:
            pts = [n for n, x in enumerate(fieldlist) if x.startswith(val)]
            if pts:
                ins_point = min(pts)
                fieldlist.insert(ins_point, val)
        return fieldlist

    def rename_field(self, instr:str)->str:
        '''
        Split and capitalize fields as required
        eg: keywordValue -> Keyword Value
        eg: termsOfUse -> Terms of Use
        '''
        noncap = ['A', 'Of', 'The']

        wordsp = ''.join(map(lambda x: x if x not in string.ascii_uppercase
                             else f' {x}', list(instr)))
        wordsp = wordsp.split(' ')
        #wordsp[0] = wordsp[0].capitalize()
        #wordsp = ' '.join(map(lambda x: x if x not in noncap else x.lower(), wordsp))
        wordsp = list(map(lambda x: x if x not in noncap else x.lower(), wordsp))
        wordsp[0] = wordsp[0].capitalize()
        wordsp = ' '.join(wordsp)
        #because they can't even use camelCaseConsistently
        fixthese ={'U R L': 'URL', 'U R I': 'URI', 'I D': 'ID', 'Ds': ''}
        for k, v in fixthese.items():
            wordsp = wordsp.replace(k, v)
        return wordsp.strip()

    def concatenator(self, meta):
        '''Produce a concatenated dictionary with the key being just the prefix'''
        #The keys are the first part of the fields that need concatenation
        concat = {_:[] for _ in self.concat}

        for k, v in meta.items():
            for fk in concat:
                if k.startswith(fk):
                    if v:
                        if concat[fk]:
                            concat[fk].append(v.split(';'))
                        else:
                            concat[fk] = [v.split(';')]


        outdict = {}
        for ke, va in concat.items():
            if va:
                interim = self.max_zip(*va)
                interim = [' - '.join([y.strip() for y in _ if y]) for _ in interim ]
                #interim = '; '.join(interim) # Should it be newline?
                #interim = '  \n'.join(interim) # Should it be newline?
                interim= '<br/>'.join(interim)# Markdownify strips internal spaces
                #if ke.startswith('keyw'):
                #    breakpoint()
                outdict[ke] = interim
        return outdict

    def max_zip(self, *args):
        '''
        Like zip, only uses the *maximum* length and appends None if not found
        '''
        length = max(map(len, args))
        outlist=[]
        for n in range(length):
            vals = []
            for arg in args:
                try:
                    vals.append(arg[n])
                except IndexError:
                    vals.append(None)
            outlist.append(vals)
        return outlist

    def write_pdf(self, dest:str)->None:
        '''
        Make the PDF and save it at "dest"
        '''
        output = markdown_pdf.MarkdownPdf(toc_level=1)
        content = markdown_pdf.Section(self.readme_md, toc=False)
        output.add_section(content)
        output.save(dest)

if __name__ == '__main__':
    pass
