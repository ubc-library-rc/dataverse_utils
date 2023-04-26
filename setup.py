'''
dataverse_utils setup file. Very basic
'''
import ast
#import glob
import os
import setuptools

#This is where to put the primary version string
INIT = os.path.join(os.path.dirname(__file__),
                    'dataverse_utils', '__init__.py')

#Don't make a VERSION_CONTROL variable
VERSION_LINE = list(
    filter(lambda l: l.startswith('VERSION'), open(INIT)))[0].strip()

def get_version(version_tuple):
    '''Get version from module'''
    if not isinstance(version_tuple[-1], int):
        return '.'.join(
            map(str, version_tuple[:-1])
        ) + version_tuple[-1]
    return '.'.join(map(str, version_tuple))

#literal_eval turns '(3,2,3)' into a tuple, and is safer than eval
PKG_VERSION = get_version(ast.literal_eval(VERSION_LINE.split('=')[-1].strip()))

def readme():
    '''
    Read in the markdown long description
    '''
    try:
        with open('README.md') as fil:
            return fil.read()
    except IOError:
        return ''
# NAME to project name
CONFIG = {
    'description': 'Dataverse utilities',
    'long_description': readme(),
    'long_description_content_type' : 'text/markdown',
    'author': 'Paul Lesack',
    'url': 'https://github.com/ubc-library-rc/dataverse_utils',
    'download_url': 'https://github.com/ubc-library-rc/dataverse_utils',
    'author_email': 'paul.lesack@ubc.ca',
    'version' : PKG_VERSION,
    'install_requires': ['requests', 'requests_toolbelt',
                         ('dryad2dataverse @ git+https://github.com/'
                           'ubc-library-rc/dryad2dataverse.git@master'),
                         'beautifulsoup4', 'Markdown', 'markdownify'],
    'packages':setuptools.find_packages(),
    'include_package_data' : True,
    'package_data' : {'': ['data/*']},
    'entry_points':{'console_scripts':[
        'dv_del=dataverse_utils.scripts.dv_del:main',
        'dv_ldc_uploader=dataverse_utils.scripts.dv_ldc_uploader:main',
        'dv_manifest_gen=dataverse_utils.scripts.dv_manifest_gen:main',
        'dv_pg_facet_date=dataverse_utils.scripts.dv_pg_facet_date:main',
        'dv_record_copy=dataverse_utils.scripts.dv_record_copy:main',
        'dv_release=dataverse_utils.scripts.dv_release:main',
        'dv_replace_licenses=dataverse_utils.scripts.dv_replace_licenses:main',
        'dv_upload_tsv=dataverse_utils.scripts.dv_upload_tsv:main']},
    #'scripts': glob.glob('scripts/*py'),
    'name': 'dataverse_utils',
    'python_requires': '>=3.6'
}

setuptools.setup(**CONFIG)
