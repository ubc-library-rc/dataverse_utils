'''
Creates dataverse JSON from Linguistic Data Consortium
website page.

'''
import os
import time

import markdown
import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup as bs
import dryad2dataverse.serializer as ds

with open(os.path.dirname(os.path.abspath(__file__))+os.sep
          +'data'+os.sep+'LDC_EULA_general.md') as lic:
    mark = markdown.Markdown()
    LIC_NAME = lic.readline()[2:].strip()
    lic.seek(0)
    LICENCE = mark.convert(lic.read())

class Ldc(ds.Serializer):
    '''
    An LDC item (eg, LDC2021T01)
    '''
    def __init__(self, ldc):
        self.ldc = ldc.strip().upper()
        self.ldcHtml = None
        self._ldcJson = None
        self._dryadJson = None
        self._dvJson = None
        self.session = requests.Session()
        self.session.mount('https://',
                           HTTPAdapter(max_retries=ds.constants.RETRY_STRATEGY))

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
        if not self._dryadJson:
            self._dryadJson = self.make_dryad_json()
        return self._dryadJson

    @property
    def dvJson(self):
        #return False
        if not self._dvJson:
            self._dvJson = self.make_dv_json()
        return self._dvJson

    @property
    def embargo(self):
        return False

    @property
    def fileJson(self, timeout=45):
        return False

    @property
    def files(self):
        return None

    @property
    def oversize(self, maxsize=None):
        if not maxsize:
            maxsize = ds.constants.MAX_UPLOAD

    @property
    def id(self):
        return self.ldc

    def fetch_record(self, url=None, timeout=45):
        interim = self.session.get(f'https://catalog.ldc.upenn.edu/{self.ldc}')
        interim.raise_for_status()
        self.ldcHtml = interim.text

    def make_ldc_json(self):
        '''
        Returns a dict with keys created from an LDC catalogue web
        page.

        intext : str
            HTML page source from LDC catalogue page.
        '''
        if not self.ldcHtml:
            self.fetch_record()
        soup = bs(self.ldcHtml, 'html.parser')
        data = [x.text.strip() for x in soup.find_all('td')]
        LDC_dict = {data[x][:data[x].find('\n')].strip(): data[x+1].strip() for x in range(0, len(data), 2)}
        #Related Works appears to have an extra 'Hide' at the end
        if LDC_dict.get('Related Works:'):
            LDC_dict['Related Works'] = list(set([x.strip() for x in LDC_dict['Related Works:'].split('\n')]))
            del LDC_dict['Related Works:'] #remove the renamed key
        LDC_dict['Linguistic Data Consortium'] = LDC_dict['LDC Catalog No.']
        del LDC_dict['LDC Catalog No.']#This key must be renamed for consistency
        LDC_dict['Author(s)'] = [x.strip() for x in LDC_dict['Author(s)'].split(',')]
        other_meta = soup.find_all('div')
        alldesc = [x for x in other_meta if x.attrs.get('itemprop') == 'description']
        alldesc = str(alldesc).split('<h3>')
        for i in range(1, len(alldesc)):
            alldesc[i] = '<h3>' + alldesc[i]
        alldesc.pop(0)
        subdict = {}
        for i in alldesc:
            subsoup = bs(i, 'html.parser')
            key = subsoup.h3.text.strip()
            text = '\n'.join([str(x).strip() for x in subsoup.find_all('p')])
            if text:
                subdict[key] = text
            text = '\n'.join([x.text.strip() for x in subsoup.find_all('span')])
            if text:
                subdict[key] = subdict.get(key, '') + '<p>\n' + text + '\n</p>'

        LDC_dict.update(subdict)
        #self.ldcJson = LDC_dict
        return LDC_dict

    @staticmethod
    def name_parser(name):
        '''
        name : str
            A name
        '''
        names = name.split(' ')
        return {'lastName': names[-1], 'firstName': ' '.join(names[:-1]), 'affiliation':''}

    def make_dryad_json(self, ldc=None):
        '''
        Creates a Dryad-style dict from an LDC dictionary

        ldc : dict
            Dictionary containing LDC data
        '''
        if not ldc:
            ldc = self.ldcJson
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
        releaseDate = time.strptime(ldc['Release Date'], '%B %d, %Y')
        releaseDate = time.strftime('%Y-%m-%d', releaseDate)
        dryad['lastModificationDate'] = releaseDate
        dryad['publicationDate'] = releaseDate

        return dryad


    def _make_note(self, ldc=None):
        '''
        Creates a generalizes HTML notes field from a bunch of
        LDC fields that don't fit into dataverse

        '''
        if not ldc:
            ldc = self.ldcJson
        note_fields = ['DCMI Type(s)',
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
        Finds the index number of an item in Dataverse's idiotic JSON
        '''
        for num, item in enumerate(dvjson['datasetVersion']['metadataBlocks']['citation']['fields']):
            if item['typeName'] == key:
                return num
        return None

    def make_dv_json(self, ldc=None):
        '''
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
        p_affil = super()._convert_generic(inJson={'producerAffiliation': 'University of Pennsylvania'},
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
        s_info = super()._convert_generic(inJson={'seriesInformation': 'Linguistic Data Consortium'},
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
        keyword_field = [(x, y) for x, y in enumerate(dvjson['datasetVersion']['metadataBlocks']['citation']['fields']) if y.get('typeName') == 'keyword'][0]
        key_pos = [x for x, y in enumerate(keyword_field[1]['value']) if y['keywordVocabulary']['value'] == 'Dryad'][0]
        dvjson['datasetVersion']['metadataBlocks']['citation']['fields'][keyword_field[0]]['value'][key_pos]['keywordVocabulary']['value'] = 'Linguistic Data Consortium'

        #The first keyword field is hardcoded in by dryad2dataverse.serializer
        #So I think it needs to be deleted
        keyword_field = [(x, y) for x, y in enumerate(dvjson['datasetVersion']['metadataBlocks']['citation']['fields']) if y.get('typeName') == 'otherId'][0] #ibid
        del dvjson['datasetVersion']['metadataBlocks']['citation']['fields'][keyword_field[0]]

        #Notes
        note_index = Ldc.find_block_index(dvjson, 'notesText')
        if note_index:
            dvjson['datasetVersion']['metadataBlocks']['citation']['fields'][note_index]['value'] = self._make_note()
        else:
            notes = super()._typeclass('notesText', False, 'primitive')
            notes['value'] = self._make_note()
            dvjson['datasetVersion']['metadataBlocks']['citation']['fields'].append(notes)

        #Deletes unused "publication" fields: rewrite to make it a function call.
        keyword_field = [(x, y) for x, y in enumerate(dvjson['datasetVersion']['metadataBlocks']['citation']['fields']) if y.get('typeName') == 'publication'][0] #ibid
        del dvjson['datasetVersion']['metadataBlocks']['citation']['fields'][keyword_field[0]]

        #And now the licence:
        dvjson['datasetVersion']['license'] = LIC_NAME
        dvjson['datasetVersion']['termsOfUse'] = LICENCE
        return dvjson

    def upload_metadata(self, **kwargs) -> dict:
        '''
        uploads metadata to dataverse
        kwargs:
        url : base url to Dataverse
        key : api key
        dv : dataverse to which it is being uploaded

        Returns json from connection attempt.
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
