import dataverse_utils as du


if __name__ == '__main__':
    import sys
    #du.make_tsv_manifest('CIUS2018_manifest.tsv')
    #print(du.make_tsv(sys.argv[1])) 
    #'''
    import sys
    import csv
    hdl = 'hdl:11272.1/AB2/KWDCXH'
    dv = 'https://abacus.library.ubc.ca'
    #hdl = 'hdl:11272/AB2/YRPXP7'
    #dv = 'https://abacus-staging.library.ubc.ca'
    apikey = sys.argv[1]

    with open('CIUS_2018manifest.tsv') as fil:
    #with open('CIUS_2018_SPSS.tsv') as fil:
    #with open('junk.tsv') as fil:
        reader = csv.reader(fil, delimiter='\t', quotechar='"')
        for num, row in enumerate(reader):
            if num == 0:
                continue
            dirlabel = du.file_path(row[0], './')
            tags = row[-1].split(',')
            tags = [x.strip() for x in tags]
            descr= row[1]
            params = {'dv' : dv,
                      'tags' : tags,
                      'descr' : descr,
                      'dirlabel' : dirlabel,
                      'apikey' : apikey}
            try:
                du.upload_file(row[0], hdl, **params)
            except:
                continue
            #print(row[0], hdl, params)
    #'''
