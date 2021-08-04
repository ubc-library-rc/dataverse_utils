'''
Belated test framework for dataverse utils
'''

import unittest

import dataverse_utils as du

class FilePath(unittest.TestCase):
    '''
    The file path for files in a TSV is dependent on
    dataverse_utils.file_path, so gettting this right is
    somewhat important.
    '''

    def test_file_path(self):
        '''
        As above
        '''
        first_set = ['./path/to/file.xls',
                     'path/to/file.xls',
                     ]

        second_set = ['path/file.xls',
                      './path/file.xls',]
        
        third_set = ['file.xls',
                     './file.xls',
                      ]
        for path in first_set:
            self.assertEqual(du.file_path(path), 'path/to')
        for path in second_set:
            self.assertEqual(du.file_path(path), 'path')
        for path in third_set:
            self.assertEqual(du.file_path(path), '')
        
        self.assertEqual(du.file_path('./path/to/file.xls', './'), 'path/to')
        self.assertEqual(du.file_path('./path/to/file.xls', './path/to/'), '')

if __name__ == '__main__':
    unittest.main()
