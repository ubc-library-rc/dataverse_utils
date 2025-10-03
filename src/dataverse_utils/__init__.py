'''
Generalized dataverse utilities. Note that
`import dataverse_utils` is the equivalent of
`import dataverse_utils.dataverse_utils`
'''
from dataverse_utils.dataverse_utils import *
import sys

VERSION = (0,19,1)
__version__ = '.'.join([str(x) for x in VERSION])

USERAGENT = (f'dataverse_utils/v{__version__} ({sys.platform.capitalize()}); '
             f'Python {sys.version[:sys.version.find("(")-1]}')
UAHEADER = {'User-agent' :USERAGENT}
