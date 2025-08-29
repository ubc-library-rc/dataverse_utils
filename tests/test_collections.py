import json
import unittest
import pathlib
from unittest.mock import MagicMock

import dataverse_utils.collections as c

APIFILE = pathlib.Path(pathlib.Path(__file__).parent,'dv_frankenstein_complete_api_output.json')
with open(APIFILE, encoding='utf-8') as w:
    APIDATA = json.load(w)

API2 = pathlib.Path(pathlib.Path(__file__).parent,'get_collection_listing.json')
with open(API2, encoding='utf-8') as w:
    COLL_LISTING = json.load(w)


class TestDvCollection(unittest.TestCase):
    def setUp(self):
        self.dv_coll = c.DvCollection(url='borealisdata.ca', 
                                      coll='gallupcarleton')
        self.dv_coll.get_collections=MagicMock(return_value=None)
        self.dv_coll.__get_shortname=MagicMock(return_value=None)
        self.dv_coll.get_collection_listing = MagicMock(return_value=COLL_LISTING)
        self.dv_coll.get_studies=MagicMock(return_value={})
        self.dv_coll.get_study_info = MagicMock(return_value=c.StudyMetadata(study_meta=APIDATA))

    def test_get_coll(self):
        self.assertEqual(self.dv_coll.get_collections(), None)
        self.dv_coll.get_collections.assert_called()

    def test_get_study_info(self):
        x= self.dv_coll.get_study_info('hdl:/ran/dom')
        self.assertIsInstance(x, c.StudyMetadata)
    

class TestStudyMetadata(unittest.TestCase):
    def setUp(self):
        self.teststudy = c.StudyMetadata(study_meta=APIDATA)

    def test_iscorr(self):
        self.assertIsInstance(self.teststudy, c.StudyMetadata)
    
    def test_key_error(self):
        self.assertRaises(c.MetadataError, c.StudyMetadata, study_meta={'status':'ERROR'})

    def test_files(self):
        self.assertIsInstance(self.teststudy.files, list)


class TestReadmeOutput(unittest.TestCase):
    def setUp(self):
        self.teststudy = c.StudyMetadata(study_meta=APIDATA)
        self.readme  = c.ReadmeCreator(self.teststudy)

    def test_rename_field(self):
        self.assertEqual(self.readme.rename_field('versionMinorNumber'), 'Version Minor Number')

        self.assertEqual(self.readme.rename_field('testOfTheThing'), 'Test of the Thing')

        self.assertEqual(self.readme.rename_field('aFieldOfThePeople'), 'A Field of the People')
