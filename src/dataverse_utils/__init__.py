'''
Generalized dataverse utilities. Note that
`import dataverse_utils` is the equivalent of
`import dataverse_utils.dataverse_utils`
'''
import pathlib
import sys
from dataverse_utils.dataverse_utils import *

VERSION = (0,20,1)
__version__ = '.'.join([str(x) for x in VERSION])

USERAGENT = (f'dataverse_utils/v{__version__} ({sys.platform.capitalize()}); '
             f'Python {sys.version[:sys.version.find("(")-1]}')
UAHEADER = {'User-agent' : USERAGENT}

SCRIPT_VERSIONS={
'dv_collection_info' : (0, 1, 2),
'dv_del' : (0, 2, 4),
'dv_ldc_uploader' : (0, 3, 0),
'dv_list_files' : (0, 1, 1),
'dv_manifest_gen' : (0, 5, 1),
'dv_pg_facet_date' : (0, 1, 1),
'dv_record_copy' : (0, 1, 2),
'dv_release' : (0, 1, 2),
'dv_replace_licence' : (0, 1, 1),
'dv_study_migrator' : (0, 4, 1),
'dv_upload_tsv' : (0, 5, 0)}

def script_ver_stmt(name:str)->str:
    '''
    Returns a formatted version statement for any script
    '''
    key = pathlib.Path(name).stem
    if not SCRIPT_VERSIONS.get(key):
        return f'dataverse_utils: v{__version__}'

    return (f"{key} v{'.'.join(map(str, SCRIPT_VERSIONS[key]))} / "
            f'dataverse_utils v{__version__}')
