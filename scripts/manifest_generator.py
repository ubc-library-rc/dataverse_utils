import os
import dataverse_utils as du
import glob

ldcs  = glob.glob('LDC*')
here = os.getcwd()
for ldc in ldcs:
   os.chdir(ldc)
   du.dump_tsv('./', ldc+'manifest.tsv')
   os.chdir(here)

