'''
Auto download/upload LDC metadata and files.

python3 uploadme.py LDC20201S01 . . . LDC2021T21 apikey

'''
#import glob
import os
import sys
import dataverse_utils as du
import dataverse_utils.ldc as ldc

KEY = sys.argv[-1]


ldc.ds.constants.DV_CONTACT_EMAIL = 'abacus-support@lists.ubc.ca'
ldc.ds.constants.DV_CONTACT_NAME = 'Abacus Support'

#studs  = glob.glob('LDC*')
STUDS = sys.argv[1:-1]
HERE = os.getcwd()
#del studs[studs.index('LDC2019S22')] # 3 DVDs
#del studs[studs.index('LDC2021T02')] # 1 GB
for stud in STUDS:
    os.chdir(stud)
    a = ldc.Ldc(stud)
    a.fetch_record()
    print(f'Uploading {stud} metadata')
    info = a.upload_metadata(url='https://abacus.library.ubc.ca', key=KEY, dv='ldc')
    hdl = info['data']['persistentId']
    print(f'Uploading files to {hdl}')
    with open(stud+'manifest.tsv') as fil:
        du.upload_from_tsv(fil, hdl=hdl, dv='https://abacus.library.ubc.ca', apikey=KEY)
    os.chdir(HERE)
