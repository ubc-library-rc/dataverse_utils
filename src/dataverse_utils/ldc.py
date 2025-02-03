'''
Creates dataverse JSON from Linguistic Data Consortium
website page.

'''
import copy
import os
#import re
import time

import markdown
import markdownify
import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup as bs
import dryad2dataverse.serializer as ds

#pylint: disable=invalid-name
with open(os.path.dirname(os.path.abspath(__file__))+os.sep
          +'data'+os.sep+'LDC_EULA_general.md', encoding='utf-8') as lic:
    mark = markdown.Markdown()
    LIC_NAME = lic.readline()[2:].strip()
    lic.seek(0)
    LICENCE = mark.convert(lic.read())

class Ldc(ds.Serializer):
    '''
    An LDC item (eg, LDC2021T01)
    '''
    #pylint: disable=super-init-not-called, arguments-differ
    def __init__(self, ldc, cert=None):
        '''
        Returns a dict with keys created from an LDC catalogue web
        page.

        ----------------------------------------
        Parameters:

        ldc : str
           Linguistic Consortium Catalogue Number (eg. 'LDC2015T05'.
           This is what forms the last part of the LDC catalogue URL.
        cert : str
            Path to certificate chain; LDC has had a problem
            with intermediate certificates, so you can
            download the chain with a browser and supply a
            path to the .pem with this parameter
        '''
        self.ldc = ldc.strip().upper()
        self.ldcHtml = None
        self._ldcJson = None
        self._dryadJson = None
        self._dvJson = None
        self.cert = cert
        self.session = requests.Session()
        self.session.mount('https://',
                           HTTPAdapter(max_retries=ds.constants.RETRY_STRATEGY))
        if self.cert:
            self.cert = os.path.expanduser(self.cert)
        self.__fixdesc = None

    @property
    def ldcJson(self):
        '''
        Returns a JSON based on the LDC web page scraping
        '''
        if not self._ldcJson:
            self._ldcJson = self.make_ldc_json()
        return self._ldcJson

    @property
    def dryadJson(self):
        '''
        LDC metadata in Dryad JSON format
        '''
        if not self._dryadJson:
            self._dryadJson = self.make_dryad_json()
        return self._dryadJson

    @property
    def dvJson(self):
        '''
        LDC metadata in Dataverse JSON format
        '''
        #return False
        if not self._dvJson:
            self._dvJson = self.make_dv_json()
        return self._dvJson

    @property
    def embargo(self):
        '''
        Boolean indicating embargo status
        '''
        return False

    @property
    def fileJson(self):
        '''
        Returns False: No attached files possible at LDC
        '''
        return False

    @property
    def files(self):
        '''
        Returns None. No files possible
        '''
        return None

    @property
    def oversize(self, maxsize=None):
        '''
        Make sure file is not too big for the Dataverse instance
        '''
        #pylint: disable=property-with-parameters
        if not maxsize:
            maxsize = ds.constants.MAX_UPLOAD

    @property
    def id(self):
        return self.ldc

    def fetch_record(self, timeout=45):
        '''
        Downloads record from LDC website
        '''
        interim = self.session.get(f'https://catalog.ldc.upenn.edu/{self.ldc}',
                                   verify=self.cert, timeout=timeout)
        interim.raise_for_status()
        self.ldcHtml = interim.text

    def make_ldc_json(self):
        '''
        Returns a dict with keys created from an LDC catalogue web
        page.
        '''
        if not self.ldcHtml:
            self.fetch_record()
        soup = bs(self.ldcHtml, 'html.parser')
        #Should data just look in the *first* table? Specifically tbody?
        #Is it always the first? I assume yes.
        tbody = soup.find('tbody')#new
        data = [x.text.strip() for x in tbody.find_all('td')]#new
        #data = [x.text.strip() for x in soup.find_all('td')]#original
        LDC_dict = {data[x][:data[x].find('\n')].strip(): data[x+1].strip()
                    for x in range(0, len(data), 2)}
        #Related Works appears to have an extra 'Hide' at the end
        if LDC_dict.get('Related Works:'):
            LDC_dict['Related Works'] = (x.strip() for x in LDC_dict['Related Works:'].split('\n'))
            del LDC_dict['Related Works:'] #remove the renamed key
        LDC_dict['Linguistic Data Consortium'] = LDC_dict['LDC Catalog No.']
        del LDC_dict['LDC Catalog No.']#This key must be renamed for consistency
        LDC_dict['Author(s)'] = [x.strip() for x in LDC_dict['Author(s)'].split(',')]
        #Other metadata probably has HTML in it, so we keep as much as possible
        other_meta = soup.find_all('div')
        alldesc = [x for x in other_meta if x.attrs.get('itemprop') == 'description']
        #sometimes they format pages oddly and we can use this for a
        #quick and dirty fix
        self.__fixdesc = copy.deepcopy(alldesc)
        #sections use h3, so split on these
        #24 Jan 23 Apparently, this is all done manually so some of them sometime use h4.
        #Because reasons.
        #was:
        #alldesc = str(alldesc).split('<h3>')
        #is now
        alldesc = str(alldesc).replace('h4>', 'h3>').split('<h3>')
        for i in range(1, len(alldesc)):
            alldesc[i] = '<h3>' + alldesc[i]
        #first one is not actually useful, so discard it
        alldesc.pop(0)


        #So far, so good. At this point the relative links need fixing
        #and tables need to be converted to pre.
        for desc in alldesc:
            #It's already strings; replace relative links first
            desc = desc.replace('../../../', 'https://catalog.ldc.upenn.edu/')
            subsoup = bs(desc, 'html.parser')
            key = subsoup.h3.text.strip()
            #don't need the h3 tags anymore
            subsoup.find('h3').extract()
            # Convert tables to <pre>
            for tab in subsoup.find_all('table'):
                content = str(tab)
                #convert to markdown
                content = markdownify.markdownify(content)
                tab.name = 'pre'
                tab.string = content #There is not much documentation on the
                                     #difference between tab.string and tab.content
            #That was relatively easy
            LDC_dict[key] = str(subsoup)
        LDC_dict['Introduction'] = LDC_dict.get('Introduction',
                                                self.__no_intro())
        return LDC_dict

    def __no_intro(self)->str:
        '''
        Makes an introduction even if they forgot to include the word "Introduction"
        '''
        #self.__fixdesc is set in make_ldc_json
        intro = [x for x in self.__fixdesc if
                 self.__fixdesc[0]['itemprop']=='description'][0]
        while intro.find('div'): #nested?, not cleaning properly
            intro.find('div').unwrap() # remove the div tag
        intro = str(intro)
        #Normally, there's an <h3>Introduction</h3> but sometimes there's not
        #Assumes that the first section up to "<h" is an intro.
        #You know what they say about assuming
        intro = intro[:intro.find('<h')]
        start = intro.find('<div')
        if start != -1:
            end = intro.find('>',start)+1
            intro = intro.replace(intro[start:end], '').strip()
        return intro

    @staticmethod
    def name_parser(name):
        '''
        Returns lastName/firstName JSON snippet from name

        -----------------/-----------------------
        Parameters:

        name : str
            A name
        '''
        names = name.split(' ')
        return {'lastName': names[-1], 'firstName': ' '.join(names[:-1]), 'affiliation':''}

    def make_dryad_json(self, ldc=None):
        '''
        Creates a Dryad-style dict from an LDC dictionary

        ----------------------------------------
        Parameters:

        ldc : dict
            Dictionary containing LDC data. Defaults to self.ldcJson
        '''
        if not ldc:
            ldc = self.ldcJson
        print(ldc)
        dryad = {}
        dryad['title'] = ldc['Item Name']
        dryad['authors'] = [Ldc.name_parser(x) for x in ldc['Author(s)']]
        abstract = ('<p><b>Introduction</b></p>'
                    f"<p>{ldc['Introduction']}</p>"
                    '<p><b>Data</b></p>'
                    f"<p>{ldc['Data']}</p>")
        if ldc.get('Acknowledgement'):
            abstract += ('<p><b>Acknowledgement</b></p>'
                         f"<p>{ldc['Acknowledgement']}</p>")
        dryad['abstract'] = abstract
        dryad['keywords'] = ['Linguistics']

        #Dataverse accepts only ISO formatted date

        try:
            releaseDate = time.strptime(ldc['Release Date'], '%B %d, %Y')
            releaseDate = time.strftime('%Y-%m-%d', releaseDate)
        except KeyError:
            #Older surveys don't have a release date field
            #so it must be created from the record number
            if self.ldc[3] == '9':
                releaseDate = '19' + self.ldc[3:5]
        dryad['lastModificationDate'] = releaseDate
        dryad['publicationDate'] = releaseDate

        return dryad


    def _make_note(self, ldc=None):
        '''
        Creates a generalizes HTML notes field from a bunch of
        LDC fields that don't fit into dataverse

        ----------------------------------------
        Parameters:

        ldc : dict
            Dictionary containing LDC data. Defaults to self.ldcJson
        '''
        if not ldc:
            ldc = self.ldcJson
        note_fields = ['DCMI Type(s)',
                       'Sample Type',
                       'Sample Rate',
                       'Application(s)',
                       'Language(s)',
                       'Language ID(s)']
        outhtml = []
        for note in note_fields:
            if ldc.get(note):
                data = ldc[note].split(',')
                data = [x.strip() for x in data]
                data = ', '.join(data)
                if note != 'Language ID(s)':
                    data = data[0].capitalize() + data[1:]
                    #data = [x.capitalize() for x in data]
                outhtml.append(f'{note}: {data}')
        outhtml.append(f'Metadata automatically created from '
                       f'<a href="https://catalog.ldc.upenn.edu/{self.ldc}">'
                       f'https://catalog.ldc.upenn.edu/{self.ldc}</a> '
                       f'[{time.strftime("%d %b %Y", time.localtime())}]')
        return '<br />'.join(outhtml)

    @staticmethod
    def find_block_index(dvjson, key):
        '''
        Finds the index number of an item in Dataverse's idiotic JSON list

        ----------------------------------------
        Parameters:

        dvjson : dict
            Dataverse JSON

        key : str
           key for which to find list index
        '''
        for num, item in enumerate(dvjson['datasetVersion']
                                   ['metadataBlocks']['citation']['fields']):
            if item['typeName'] == key:
                return num
        return None

    def make_dv_json(self, ldc=None):
        '''
        Returns complete Dataverse JSON

        ----------------------------------------
        Parameters:

        ldc : dict
            LDC dictionary. Defaults to self.ldcJson
        '''
        if not ldc:
            ldc = self.ldcJson

        dvjson = super().dvJson.copy()

        #ID Numbers
        otherid = super()._typeclass('otherId', True, 'compound')
        ids = []
        for item in ['Linguistic Data Consortium', 'ISBN', 'ISLRN', 'DOI']:
            if ldc.get(item):
                out = {}
                agency = super()._convert_generic(inJson={item:item},
                                                  dryField=item,
                                                  dvField='otherIdAgency')
                value = super()._convert_generic(inJson={item:ldc[item]},
                                                 dryField=item,
                                                 dvField='otherIdValue')
                out.update(agency)
                out.update(value)
                ids.append(out)
        otherid['value'] = ids
        dvjson['datasetVersion']['metadataBlocks']['citation']['fields'].append(otherid)

        #Producer and publisher
        prod = super()._typeclass('producer', True, 'compound')
        p_name = super()._convert_generic(inJson={'producerName': 'Linguistic Data Consortium'},
                                          dryField='producerName',
                                          dvField='producerName')
        p_affil = super()._convert_generic(inJson={'producerAffiliation':
                                                   'University of Pennsylvania'},
                                           dryField='producerName',
                                           dvField='producerName')
        p_url = super()._convert_generic(inJson={'producerURL': 'https://www.ldc.upenn.edu/'},
                                         dryField='producerURL',
                                         dvField='producerURL')
        p_name.update(p_affil)
        p_name.update(p_url)
        prod['value'] = [p_name]
        dvjson['datasetVersion']['metadataBlocks']['citation']['fields'].append(prod)

        #Kind of data
        kind = super()._typeclass('kindOfData', True, 'primitive')
        kind['value'] = 'Linguistic data'

        #Series
        series = super()._typeclass('series', False, 'compound')
        s_name = super()._convert_generic(inJson={'seriesName': 'LDC'},
                                          dryField='seriesName',
                                          dvField='seriesName')
        s_info = super()._convert_generic(inJson={'seriesInformation':
                                                  'Linguistic Data Consortium'},
                                          dryField='seriesInformation',
                                          dvField='seriesInformation')
        s_name.update(s_info)
        series['value'] = s_name #not a list
        dvjson['datasetVersion']['metadataBlocks']['citation']['fields'].append(series)

        #Data sources
        series = super()._typeclass('dataSources', True, 'primitive')
        data_sources = ldc['Data Source(s)'].split(',')
        data_sources = [x.strip().capitalize() for x in data_sources]
        series['value'] = data_sources
        dvjson['datasetVersion']['metadataBlocks']['citation']['fields'].append(series)

        #Fix keyword labels that are hardcoded for Dryad
        #There should be only one keyword block
        keyword_field = [(x, y) for x, y in enumerate(dvjson['datasetVersion']['metadataBlocks']
                                                      ['citation']['fields'])
                                                        if y.get('typeName') == 'keyword'][0]
        key_pos = [x for x, y in enumerate(keyword_field[1]['value'])
                   if y['keywordVocabulary']['value'] == 'Dryad'][0]
        dvjson['datasetVersion']['metadataBlocks']['citation']\
                ['fields'][keyword_field[0]]['value'][key_pos]\
                ['keywordVocabulary']['value'] = 'Linguistic Data Consortium'

        #The first keyword field is hardcoded in by dryad2dataverse.serializer
        #So I think it needs to be deleted
        keyword_field = [(x, y) for x, y in
                         enumerate(dvjson['datasetVersion']['metadataBlocks']['citation']['fields'])
                         if y.get('typeName') == 'otherId'][0] #ibid
        del dvjson['datasetVersion']['metadataBlocks']['citation']['fields'][keyword_field[0]]

        #Notes
        note_index = Ldc.find_block_index(dvjson, 'notesText')
        if note_index:
            dvjson['datasetVersion']['metadataBlocks']['citation']\
                ['fields'][note_index]['value'] = self._make_note()
        else:
            notes = super()._typeclass('notesText', False, 'primitive')
            notes['value'] = self._make_note()
            dvjson['datasetVersion']['metadataBlocks']['citation']['fields'].append(notes)

        #Deletes unused "publication" fields: rewrite to make it a function call.
        keyword_field = [(x, y) for x, y in enumerate(dvjson['datasetVersion']
                                                      ['metadataBlocks']['citation']['fields'])
                         if y.get('typeName') == 'publication'][0] #ibid
        del dvjson['datasetVersion']['metadataBlocks']['citation']['fields'][keyword_field[0]]

        #And now the licence:
        dvjson['datasetVersion']['license'] = LIC_NAME
        dvjson['datasetVersion']['termsOfUse'] = LICENCE
        return dvjson

    def upload_metadata(self, **kwargs) -> dict:
        '''
        Uploads metadata to dataverse

        Returns json from connection attempt.

        ----------------------------------------
        Parameters:

        kwargs:

        url : str
            base url to Dataverse

        key : str
            api key

        dv : str
            Dataverse to which it is being uploaded

        '''
        url = kwargs['url'].strip('/')
        key = kwargs['key']
        dv = kwargs['dv']
        json = kwargs.get('json', self.dvJson)
        try:
            upload = self.session.post(f'{url}/api/dataverses/{dv}/datasets',
                                       headers={'X-Dataverse-key':key},
                                       json=json)
            upload.raise_for_status()
            return upload.json()
        except (requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError):
            print(upload.text)
            raise

if __name__ == '__main__':
    pass
