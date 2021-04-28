'''
dataverse_utils setup file. Very basic
'''
import setuptools
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
    'description': 'Minor dataverse upload utilities',
    'long_description': readme(),
    'long_description_content_type' : 'text/markdown',
    'author': 'Paul Lesack',
    'url': 'https://github.com/ubc-library-rc',
    'download_url': 'https://github.com/ubc-library-rc',
    'author_email': 'paul.lesack@ubc.ca',
    'version' : '0.1',
    'install_requires': ['requests', 'requests_toolbelt'],
    'packages':setuptools.find_packages(),
    'name': 'dataverse_utils',
    'python_requires': '>=3.6'
}

setuptools.setup(**CONFIG)
