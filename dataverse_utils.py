'''
A collection of Dataverse utilities for file and metadata
manipulation
'''

import csv
import io
import logging
import mimetypes
import os

from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests

LOGGER = logging.getLogger('__name__')

#A list of extensions which disable tabular processing
NOTAB = ['.sav', '.por', '.zip', '.csv', '.tsv', '.dta', '.rdata', '.xlsx']


class DvGeneralUploadError(Exception):
    '''
    Raised on non-200 URL response
    '''

class Md5Error(Exception):
    '''
    Raised on md5 mismatch
    '''

def make_tsv(start_dir, def_tag='Data'):
    '''
    Recurses the tree for files and produces tsv output with
    with headers 'file', 'description', 'tags'.

    The 'description' is the filename without an extension.

    ------------------------------------------
    Parameters:
    start_dir : str
        Path to start directory
    def_tag : str
        Default Dataverse tag (eg, Data, Documentation, etc)
        Separate tags with an easily splitable character:
        eg. ('Data, 2016')
    '''

    if not start_dir.endswith(os.sep):
        start_dir += os.sep
    basic = [f'{x[0]}{os.sep}{y}'
             for x in os.walk(start_dir)
             for y in x[2]
             if not y.startswith('.')]

    headers = ['file', 'description', 'tags']
    outf = io.StringIO()
    tsv_writer = csv.writer(outf, delimiter='\t',
                            quoting=csv.QUOTE_NONNUMERIC,
                            )
    tsv_writer.writerow(headers)
    for row in basic:
        desc = os.path.splitext(os.path.basename(row))[0]
        tsv_writer.writerow([row, desc, def_tag])
    outf.seek(0)
    outfile = outf.read()
    outf.close()
    return outfile

#def make_tsv_manifest(fname, def_tag='Data', outfile=None):
#    '''
#    Create a TSV file for editing in a spreadsheet application,
#    with headers 'file', 'description', 'tags'.
#
#    Normally you would use the output of:
#
#    find . -name "*" -type f > fname
#
#    as the input file.
#
#    By default, the new manifest overwrites the old.
#
#    The 'description' is the filename without an extension.
#
#    ------------------------------------------
#    Parameters:
#
#    fname : str
#        Input text file
#    def_tag : str
#        Default Dataverse tag (eg, Data, Documentation, etc)
#    outfile : str
#        output TSV file. Default overwrites input file
#    '''
#    if not outfile:
#        outfile = fname
#
#    with open(fname) as fil:
#        basic = fil.read()
#
#    basic = basic.split('\n')
#    basic = [x for x in basic if x]
#
#    headers = ['file', 'description', 'tags']
#    with open(outfile, 'w') as outf:
#        tsv_writer = csv.writer(outf, delimiter='\t',
#                                quoting=csv.QUOTE_NONNUMERIC,
#                                )
#        tsv_writer.writerow(headers)
#        for row in basic:
#            desc = os.path.splitext(os.path.basename(row))[0]
#            tsv_writer.writerow([row, desc, def_tag])

def file_path(fpath, trunc):
    '''
    Create relative file path from full path string

    >>> file_path('/tmp/Data/2011/excelfile.xlsx', '/tmp/')
    'Data/2011'
    >>> file_path('/tmp/Data/2011/excelfile.xlsx', '/tmp')
    'Data/2011'

    ----------------------------------------
    Parameters:

    fpath : str
        file location (ie, complete path)
    trunc : str
        rightmost portion of path to remove
    '''
    if not trunc.endswith(os.sep):
        trunc += os.sep

    path = os.path.dirname(fpath)
    return path[path.find(trunc)+len(trunc):]

def force_notab_unlock(study, dv_url, fid, apikey):
    '''
    Checks for a study lock and forcibly unlocks and uningests
    to prevent tabular file processing. Required if mime and filename
    spoofing is not sufficient.

    ----------------------------------------
    Parameters:

    study : str
        Persistent indentifer of study
    dv_url : str
        URL to base Dataverse installation
    fid : str
        File ID for file object
    apikey : str
        API key for user
    '''
    if dv_url.endswith('/'):
        dv_url = dv_url[:-1]
    headers = {'X-Dataverse-key': apikey}
    params = {'persistentId': study}
    lock_status = requests.get(f'{dv_url}/api/datasets/:persistentId/locks', headers=headers,
                               params=params, timeout=300)
    lock_status.raise_for_status()
    if lock_status.json()['data']:
        LOGGER.warning('Study %s has been locked', study)
        LOGGER.warning('Lock info:\n%s', lock_status.json())
        force_unlock = requests.delete(f'{dv_url}/api/datasets/:persistentId/locks',
                                       params=params, headers=headers,
                                       timeout=300)
        LOGGER.warning('Lock removed for %s', study)
        LOGGER.warning('Lock status:\n %s', force_unlock.json())
        f_params = {'persistentId': fid}
        #TODO: Awaiting answer from Harvard on how to remove progress bar
        #for uploaded tab files that squeak through
        uningest = requests.post(f'{dv_url}/api/files/{fid}/uningest',
                                 headers=headers,
                                 timeout=300)
        LOGGER.warning('Ingest halted for file %s for study %s', fid, study)
        uningest.raise_for_status()

def upload_file(fpath, hdl, **kwargs):
    '''
    Uploads file to Dataverse study and sets file metdata and tags.
    ----------------------------------------
    Parameters:

    fpath : str
        file location (ie, complete path)
    hdl : str
        Dataverse persistent ID for study (handle or DOI)
    kwargs : dict
        other parameters. Acceptable keywords and contents are:
        dv : str
            REQUIRED
            url to base Dataverse installation
            eg: 'https://abacus.library.ubc.ca'
        apikey : str
            REQUIRED
            API key for user
        descr : str
            OPTIONAL
            file description
        md5 : str
            OPTIONAL
            md5sum for file checking
        tags : list
            OPTIONAL
            list of text file tags. Eg ['Data', 'June 2020']
        dirlabel : str
            OPTIONAL
            Unix style relative pathname for Dataverse
            file path: eg: path/to/file/
    '''
    if kwargs['dv'].endswith(os.sep):
        dvurl = kwargs['dv'][:-1]
    else:
        dvurl = kwargs['dv']
    if os.path.splitext(fpath)[1].lower() in NOTAB:
        file_name_clean = os.path.basename(fpath)
        file_name = os.path.basename(fpath) + '.NOPROCESS'
    else:
        file_name = os.path.basename(fpath)
        file_name_clean = file_name

    mime = mimetypes.guess_type(fpath)[0]
    if file_name.endswith('NOPROCESS') or mime == 'application/zip':
        mime = 'application/octet-stream'

    #create file metadata in nice, simple, chunks
    dv4_meta = {'label' : file_name_clean,
                'description' : kwargs.get('descr', ''),
                'directoryLabel': kwargs.get('dirlabel', ''),
                'categories': kwargs.get('tags', [])}
    fpath = os.path.abspath(fpath)
    fields = {'file': (file_name, open(fpath, 'rb'), mime)}
    fields.update({'jsonData' : f'{dv4_meta}'})
    multi = MultipartEncoder(fields=fields) # use multipart streaming for large files
    headers = {'X-Dataverse-key' : kwargs.get('apikey'),
               'Content-type' : multi.content_type}
    params = {'persistentId' : hdl}

    print(multi)

    LOGGER.info('Uploading %s to %s', fpath, hdl)
    upload = requests.post(f"{dvurl}/api/datasets/:persistentId/add",
                           params=params, headers=headers, data=multi,
                           timeout=1000)#timeout hardcoded. Bad idea?

    print(upload.json())
    #SPSS files still process despite spoof, so there's
    #a forcible unlock check
    fid = upload.json()['data']['files'][0]['dataFile']['id']
    print(f'FID: {fid}')
    force_notab_unlock(hdl, dvurl, fid, kwargs['apikey'])

    if upload.status_code != 200:
        reason = (upload.status_code, upload.reason)
        LOGGER.critical('Upload failure: %s', reason)
        raise DvGeneralUploadError(f'\nReason: {reason}\n{upload.text}')

    if kwargs.get('md5'):
        if upload.json()['data']['files'][0]['dataFile']['md5'] != kwargs.get('md5'):
            LOGGER.warning('md5sum mismatch on %s', fpath)
            raise Md5Error('md5sum mismatch')

def upload_from_tsv(fil, hdl, **kwargs):
    '''
    Utility for bulk uploading. Assumes fil is formatted
    as tsv with headers 'file', 'description', 'tags'.

    'tags' field will be split on commas.


    ----------------------------------------
    Parameters:

    fil : filelike object
        Open file object or io.IOStream()
    hdl : str
        Dataverse persistent ID for study (handle or DOI)
    kwargs : dict
        other parameters. Acceptable keywords and contents are:
        dv : str
            REQUIRED
            url to base Dataverse installation
            eg: 'https://abacus.library.ubc.ca'
        apikey : str
            REQUIRED
            API key for user
    '''
    reader = csv.reader(fil, delimiter='\t', quotechar='"')
    for num, row in enumerate(reader):
        if num == 0:
            continue
        dirlabel = file_path(row[0], './')
        tags = row[-1].split(',')
        tags = [x.strip() for x in tags]
        descr = row[1]
        params = {'dv' : kwargs.get('dv'),
                  'tags' : tags,
                  'descr' : descr,
                  'dirlabel' : dirlabel,
                  'apikey' : kwargs.get('apikey'),
                  'md5' : kwargs.get('md5', '')}
        upload_file(row[0], hdl, **params)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
