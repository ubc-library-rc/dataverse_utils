'''
Utilities for recursively analysing a Dataverse collection
'''
import io
import logging
import pathlib
import string
import tempfile
import textwrap
import typing
import traceback
import warnings

import bs4
import markdown_pdf
import markdownify
import pyreadstat
import pandas as pd
import pyreadr
import requests
import tqdm #Progress meter
from urllib3.util import Retry
from dataverse_utils import UAHEADER

#README


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
        self.__key = key
        if self.__key:
            self.headers = {'X-Dataverse-key': self.__key}
            self.headers.update(UAHEADER)
        else:
            self.headers = UAHEADER.copy()
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
        shortname = self.session.get(f'{self.url}/api/dataverses/{dvid}', headers=self.headers)
        shortname.raise_for_status()
        return shortname.json()['data']['alias']

    def get_collections(self, coll:str=None, output=None, **kwargs):#pylint: disable=unused-argument
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
                                 headers=self.headers)
        data = x.json().get('data')
        #---
        #Because it's possible that permissions errors can cause API read errors,
        #we have this insane way of checking errors.
        #I have no idea what kind of errors would be raised, so it has
        #a bare except, which is bad. But what can you do?
        dvs =[]
        for _ in data:
            if _['type'] == 'dataverse':
                try:
                    out=self.__get_shortname(_['id'])
                    dvs.append((_['title'], out))
                except Exception as e:

                    obscure_error = f'''
                                        An error has occured where a collection can be
                                        identified by ID but its name cannot be determined.
                                        This is (normally) caused by a configuration error where
                                        administrator permissions are not correctly inherited by
                                        the child collection.

                                        Please check with the system administrator to determine
                                        any exact issues.

                                        Problematic collection id number: {_.get("id",
                                        "not available")}'''
                    print(50*'-')
                    print(textwrap.dedent(obscure_error))
                    print(e)
                    LOGGER.error(textwrap.fill(textwrap.dedent(obscure_error).strip()))
                    traceback.print_exc()
                    print(50*'-')
                    raise e
        #---
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
                                  headers=self.headers)
        cl.raise_for_status()
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
        meta = self.session.get(f'{self.url}/api/datasets/:persistentId',
                            params={'persistentId': pid},
                            headers=self.headers)
        meta.raise_for_status()
        LOGGER.debug(pid)
        return StudyMetadata(study_meta=meta.json(), key=self.__key, url=self.url)

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
        self.headers = UAHEADER.copy()
        if not (('study_meta' in kwargs) or ('url' in kwargs and 'pid' in kwargs)):
            raise TypeError('At least one of a URL/pid combo (url, pid) (and possibly key) or '
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
        if self.kwargs.get('key'):
            self.headers.update({'X-Dataverse-key':self.kwargs['key']})
        params = {'persistentId': self.pid}
        self.session = requests.Session()
        self.session.mount('https://',
                           requests.adapters.HTTPAdapter(max_retries=RETRY))
        self.url = self.url.strip('/')
        if not self.url.startswith('https://'):
            self.url = f'https://{self.url}'
        data = self.session.get(f'{self.url}/api/datasets/:persistentId',
                                headers=self.headers, params=params)
        return data.json()

    def __has_metadata(self):
        '''
        Deacessioned items are notable for their lack of any indication
        that they are deacessioned. However, they lack the "latestVersion" key.
        '''
        #try:
        #    t = self.study_meta['data']
        #    del t #OMG This is so dumb
        #except KeyError as e:
        #    raise e

        if not self.study_meta.get('data'):
            raise KeyError('data')

        testfields = ['id', 'identifier', 'authority', 'latestVersion']
        if all(self.study_meta['data'].get(_) for _ in testfields):
            return True
        return False

    def extract_metadata(self):
        '''
        Convenience function for parsing the study metadata of the latest version.

        results are written to DvCollection.ez as a dict.
        '''
        if not self.__has_metadata():
            return


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
    #TODO: Add: DOI, current date, reorder geospatial metadata to be sane. Plus files
    #Use pyreadstat, damage, pandas or all of the above to get file level metadata
    def __init__(self, study_metadata_obj: StudyMetadata, **kwargs):
        '''
        Send in StudyMetadata dict to create a nicely formatted README document

        self_study_metadata_obj: StudyMetadata
            A study metadata object

        optional kwargs:

        local: str
            Path to the top level directory which holds study files.
            If present, the Readme creator will try to create extended data from
            local files instead of downloading.
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
            #not everyone has a pid for the file
            if not fileout.get('Persistent Identifier'):
                del fileout['Persistent Identifier']
            #TODO add file detailed metadata
            # Should I only have remote material here? What about
            # local files?
            if self.kwargs.get('local'):
                #TODO, if local
                fpath = pathlib.Path(self.kwargs['local'])
                #And from here you have to walk the tree to get the file in fil['filename']
            elif self.meta.kwargs.get('url'): # Should this be optional? ie,
                                              # and self.kwargs.get('download') or summat
                d_dict = FileAnalysis(url=self.meta.kwargs['url'],
                                      key=self.meta.kwargs.get('key'),
                                      **fil).md
                #I test here
                #d_dict = FileAnalysis(local='tmp/eics_2023_pumf_v1.sav').md
                if d_dict:
                    fileout['Data Dictionary'] = d_dict

            fmeta.append(fileout)
        #----- original
        #outtmp = []
        #for li in fmeta:
        #    outtmp.append('  \n'.join(f'{k}: {v}' for k, v in li.items()))
        #return '\n\n'.join(outtmp)
        #-------
        outtmp = []
        for li in fmeta:
            o2 = []
            for k, v in li.items():
                if k == 'Data Dictionary':
                    o2.append(f'### {k} for {li["File"]}  \n{v}')
                else:
                    o2.append(f'{k}: {v}')
            outtmp.append('  \n'.join(o2))
        outtmp = '\n\n'.join(outtmp)
        return outtmp

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
        #cludgy geometry hack is best hack
        if self.bbox():
            fout.update(self.bbox())
            delme = [_ for _ in fout if _.endswith('tude')]
            for _ in delme:
                del fout[_]

        outstr =  '\n\n'.join(f'{self.make_md_heads(k)}{v}' for k, v in fout.items())
        outstr += '\n\n## File information\n\n'
        outstr += self.file_metadata_md

        return outstr

    def bbox(self)->dict:
        '''
        Produce sane bounding boxes
        '''
        #Yes, northLongitude, etc. Blame Harvard.
        bbox_order =['westLongitude',
                     'southLongitude',
                     'southLatitude',
                     'eastLongitude',
                     'northLongitude',
                     'northLatitude']

        geog_me = {_: self.meta[_].split(';')
                   for _ in bbox_order if self.meta.get(_)}# Checking for existence causes problems
        if not geog_me: #Sometimes there is no bounding box
            return {}
        bbox = {k: [f'{v} {k[0].capitalize()}'.strip()
                  for v in geog_me[k]] for k in bbox_order if geog_me.get(k)}
        boxes =  self.max_zip(*bbox.values())
        boxes = [', '.join(_) for _ in boxes]
        boxes = [f'({_})' for _ in boxes]
        return {'Bounding box(es)': '; '.join(boxes)}

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
        #Geography fields are a special case yay.
        #westLongitude is the fist one
        if 'westLongitude' in fieldlist:
            ins_here = fieldlist.index('westLongitude')
            fieldlist.insert(ins_here, 'Bounding box(es)')
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
        #Also pluralization of concatenated fields
        fixthese ={'U R L': 'URL',
                   'U R I': 'URI',
                   'I D':
                   'ID',
                   'Ds': '',
                   'Country':'Country(ies)',
                   'State':'State(s)',
                   'City':'City(ies)',
                   'Geographic Unit':'Geographic unit(s)'}
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
        dest = pathlib.Path(dest).expanduser().absolute()
        output = markdown_pdf.MarkdownPdf(toc_level=1)
        content = markdown_pdf.Section(self.readme_md, toc=False)
        output.add_section(content)
        output.save(dest)

    def write_md(self, dest:str)->None:
        '''
        Write markdown to file
        '''
        dest = pathlib.Path(dest).expanduser().absolute()
        with open(file=dest, mode='w', encoding='utf=8') as f:
            f.write(self.readme_md)

class FileAnalysis(dict):
    '''
    Download and analyze a file from a dataverse installation and
    produce useful metadata
    '''

    def __init__(self, **kwargs):
        '''
        Intialize the object. Minimum required:

        Mandatory keyword arguments:

        Either

        local : str
            Path to local file

        OR

        url : str
            URL of Dataverse instance
        key : str
            API key for downloading

        AND at least one of fid or pid:
        fid : int
            Integer file id
        pid : str
            Persistent ID of file

        ----------
        Optional keyword arguments
        filename : str
            File name (original)
        filesize_bytes : int
            File size in bytes
        local : str
            Path to local file in case you don't need to download it.
        '''

        #self.url = self.__clean_url(url)
        self.headers = UAHEADER.copy()
        self.kwargs = kwargs
        if self.kwargs.get('key'):
            self.headers.update({'X-Dataverse-key':self.kwargs['key']})
        self.local = None
        if not self.__sufficient:
            err = ('Insufficient required arguments. '
                   'Include (url, key, '
                   '(pid or id)) or (local) keyword parameters.')
            raise TypeError(err)
        self.tempfile = None
        self.session = requests.Session()
        self.session.mount('https://',
                           requests.adapters.HTTPAdapter(max_retries=RETRY))
        self.checkable = {'.sav': self.stat_file_metadata,
                          '.sas7bdat': self.stat_file_metadata,
                          '.dta': self.stat_file_metadata,
                          '.csv': self.generic_metadata,
                          '.tsv': self.generic_metadata,
                          '.rdata': self.generic_metadata,
                          '.rda': self.generic_metadata}
        self.filename = None #get it later
        self.enhance()

    def __del__(self):
        '''
        Cleanup
        '''
        self.session.close()
        del self.tempfile

    def __sufficient(self):
        if self.kwargs.get('local'):
            return True
        if (self.kwargs['url'] and self.kwargs['key']
           and (self.kwargs.get('pid') or self.kwargs.get('id'))):
            return True
        return False

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

    def __get_filename(self, head:dict)->typing.Union[str, None]:
        '''
        Determines whether or not this is a file that should be downloaded for further checking
        '''
        fname = head.get('content-type')
        if fname:
            if 'name=' in fname:
                start = head['content-type'].find('name=')+5
                end = head['content-type'].find(';', start)
                if end != -1:
                    fname = head['content-type'][start:end].strip('"')
                else:
                    fname = head['content-type'][start:].strip('"')
        fname = self.kwargs.get('filename', fname)
        return fname

    @property
    def __whichfile(self):
        return self.tempfile.name if self.tempfile else self.local

    def __check(self):
        '''
        Determines if this is one of the filetypes which supports extra metadata
        '''
        if pathlib.Path(self.filename).suffix.lower() in self.checkable:
            return True
        return False

    def download(self, block_size:int=1024, force=False, local=None)-> None:
        '''
        Download the file to a temporary location for analysis.
        block_size : int
            Streaming block size
        force : bool
            Download even if not a file that is checkable
        local : str
            Path to local file
        '''
        # pylint: disable=consider-using-with
        self.tempfile = tempfile.NamedTemporaryFile(delete=True,
                                                    delete_on_close=False)
        if local:
            self.local = local
            self.filename = local
            self.tempfile.close()
            del self.tempfile #to erase it
            self.tempfile = None
            return

        params = {'format':'original'}
        url = self.__clean_url(self.kwargs['url'])
        if self.kwargs.get('pid'):
            params.update({'persistentId':self.kwargs['pid']})
            data = self.session.get(f'{url}/api/access/datafile/:persistentId',
                                    headers=self.headers,
                                    params=params,
                                    stream=True)
        else:
            data = self.session.get(f'{url}/api/access/datafile/{self.kwargs["id"]}',
                                    headers=self.headers,
                                    params=params,
                                    stream=True)
        data.raise_for_status()
        self.filename = self.__get_filename(data.headers)

        if self.__check() or force:
            filesize = self.kwargs.get('filesize_bytes',
                                       data.headers.get('content-length', 9e9))
            filesize = int(filesize) # comes out as string from header
            with tqdm.tqdm(total=filesize, unit='B', unit_scale=True, desc=self.filename) as t:
                for _ in data.iter_content(block_size):
                    self.tempfile.file.write(_)
                    t.update(len(_))
            self.tempfile.close()

    def enhance(self):
        '''
        Convenience function for downloading and creating extra metadata,
        ie, "enhancing" the metadata.
        '''
        self.download(local=self.kwargs.get('local'))
        do_it = pathlib.Path(self.filename).suffix.lower()
        if do_it in self.checkable:
            self.checkable[do_it](ext=do_it)

    def stat_file_metadata(self, ext:str)->dict:
        '''
        Use as a framework for everything else, ideally
        '''
        matcher = {'.sav': pyreadstat.read_sav,
                   '.dta': pyreadstat.read_dta,
                   '.sas7bdat': pyreadstat.read_sas7bdat}
        if not self.filename or ext not in matcher:
            return
        #whichfile = self.tempfile.name if self.tempfile else self.local
        statdata, meta = matcher[ext](self.__whichfile)
        outmeta = {}
        outmeta['variables'] = {_:{} for _ in meta.column_names_to_labels}

        for k, v in meta.column_names_to_labels.items():
            outmeta['variables'][k]['Variable label'] = v
        for k, v in meta.original_variable_types.items():
            outmeta['variables'][k]['Variable type'] = v
        for k, v in meta.variable_to_label.items():
            outmeta['variables'][k]['Value labels'] = meta.value_labels.get(v, '')
        outmeta['encoding'] = meta.file_encoding
        for dt in statdata.columns:
            desc = {k:str(v) for k, v in dict(statdata[dt].describe()).items()}
            outmeta['variables'][dt].update(desc)
        self.update(outmeta)
        return

    #def csv_metadata(self):
    #    '''
    #    Convenience function for nsv_metadata
    #    '''
    #    self.generic_metadata('.csv')

    #def tsv_metadata(self):
    #    '''
    #    Convenience function for nsv_metadata
    #    '''
    #    self.generic_metadata('.tsv')

    def generic_metadata(self, ext):
        '''
        Make metadata for a [ct]sv file and RData

        ext : str
            extension ('.csv' or '.tsv')
        '''
        #if ext == '.tsv':
        #    data = pd.read_csv(self.__whichfile, sep='\t')
        #else:
        #    data = pd.read_csv(self.__whichfile)

        lookuptable ={'.tsv': {'func': pd.read_csv,
                                'kwargs' : {'sep':'\t'}},
                        '.csv': {'func' : pd.read_csv},
                        '.rda': {'func' : pyreadr.read_r},
                       '.rdata':{'func' : pyreadr.read_r}}
        data = lookuptable[ext]['func'](self.__whichfile,
                                              **lookuptable[ext].get('kwargs', {}))
        if ext  in ['.rda', '.rdata']:
            data = data[None] #why pyreadr why
        outmeta = {}
        outmeta['variables'] = {_:{} for _ in data.columns}
        for dt in data.columns:
            outmeta['variables'][dt]['Variable type'] = str(data[dt].dtype)
            # Make something from nothing
            desc = {k:str(v) for k, v in dict(data[dt].describe()).items()}
            outmeta['variables'][dt].update(desc)
        self.update(outmeta)

    @property
    def md(self):
        '''
        Create markdown out of a FileAnalysis object
        '''
        out = io.StringIO()
        indent = '\u00A0' # &nbsp;
        if not self.get('variables'):
            return None
        for k, v in self.items():
            if k != 'variables':
                out.write(f'**{k.capitalize()}** : {v}  \n')
        for k, v in self.get('variables',{}).items():
            out.write(f"**{k}**: {v.get('Variable label', 'Description N/A')}  \n")
            for kk, vv, in v.items():
                if kk == 'Variable label':
                    continue
                if not isinstance(vv, dict):
                    out.write(f'**{kk.capitalize()}**: {vv}  \n')
                else:
                    out.write(f'**{kk.capitalize()}**:  \n')
                    for kkk, vvv in vv.items():
                        #this one only originally
                        out.write(f'{4*indent}{kkk}: {vvv}  \n')
            out.write('\n')

        out.seek(0)
        return out.read()

if __name__ == '__main__':
    pass
