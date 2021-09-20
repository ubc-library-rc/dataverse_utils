'''
A collection of Dataverse utilities for file and metadata
manipulation
'''


import csv
import io
#Dataverse/Glassfish can sometimes partially crash and the
#API doesn't return JSON correctly, so:
import json #for errors only
import logging
import mimetypes
import os
import time
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

def _make_info(dv_url, study, apikey) -> tuple:
    '''
    Returns correctly formated headers and URLs for a request

    ------------------------------------------
    Parameters:

    study : str
        Study handle or file ID

    dv_url : str
        URL to base dataverse instance

    apikey : Dataverse API key
    '''
    if dv_url.endswith('/'):
        dv_url = dv_url[:-1]
    headers = {'X-Dataverse-key': apikey}
    params = {'persistentId': study}
    return (dv_url, headers, params)

def make_tsv(start_dir, in_list=None, def_tag='Data', inc_header=True) -> str:
    '''
    Recurses the tree for files and produces tsv output with
    with headers 'file', 'description', 'tags'.

    The 'description' is the filename without an extension.

    Returns tsv as string.

    ------------------------------------------
    Parameters:

    start_dir : str
        Path to start directory

    in_list : list
        Input file list. Defaults to recursive walk of current directory.

    def_tag : str
        Default Dataverse tag (eg, Data, Documentation, etc)
        Separate tags with a comma:
        eg. ('Data, 2016')

    inc_header : bool
        Include header row
    '''
    if start_dir.endswith(os.sep):
        #start_dir += os.sep
        start_dir = start_dir[:-1]
    if not in_list:
        in_list = [f'{x[0]}{os.sep}{y}'
                   for x in os.walk(start_dir)
                   for y in x[2]
                   if not y.startswith('.')]
    if isinstance(in_list, set):
        in_list=list(in_list)
    in_list.sort()
    def_tag = ", ".join([x.strip() for x in def_tag.split(',')])
    headers = ['file', 'description', 'tags']
    outf = io.StringIO(newline='')
    tsv_writer = csv.writer(outf, delimiter='\t',
                            quoting=csv.QUOTE_NONNUMERIC,
                            )
    if inc_header:
        tsv_writer.writerow(headers)
    for row in in_list:
        desc = os.path.splitext(os.path.basename(row))[0]
        tsv_writer.writerow([row, desc, def_tag])
    outf.seek(0)
    outfile = outf.read()
    outf.close()

    return outfile

def dump_tsv(start_dir, filename, in_list=None,
             def_tag='Data', inc_header=True):
    '''
    Dumps output of make_tsv manifest to a file.

    ------------------------------------------
    Parameters:

    start_dir : str
        Path to start directory

    in_list : list
        List of files for which to create manifest entries. Will
        default to recursive directory crawl

    def_tag : str
        Default Dataverse tag (eg, Data, Documentation, etc)
        Separate tags with an easily splitable character:
        eg. ('Data, 2016')

    inc_header : bool
        Include header for tsv.
    '''
    dumper = make_tsv(start_dir, in_list, def_tag, inc_header)
    with open(filename, 'w', newline='') as tsvfile:
        tsvfile.write(dumper)

def file_path(fpath, trunc='') -> str:
    '''
    Create relative file path from full path string

    >>> file_path('/tmp/Data/2011/excelfile.xlsx', '/tmp/')
    'Data/2011'
    >>> file_path('/tmp/Data/2011/excelfile.xlsx', '/tmp')
    'Data/2011'

    ----------------------------------------
    Parameters:

    fpath : str
        File location (ie, complete path)

    trunc : str
        Leftmost portion of path to remove
    '''
    if trunc and not trunc.endswith(os.sep):
        trunc += os.sep

    path = os.path.dirname(fpath)
    try:
        if fpath.find(trunc) == -1:
            dirlabel = os.path.relpath(os.path.split(path)[0])
        dirlabel = os.path.relpath(path[path.find(trunc)+len(trunc):])

        if dirlabel == '.':
            dirlabel = ''
        return dirlabel

    except ValueError:
        return ''

def check_lock(dv_url, study, apikey) -> bool:
    '''
    Checks study lock status; returns True if locked.

    ----------------------------------------
    Parameters:

    dvurl : str
        URL of Dataverse installation

    study: str
        Persistent ID of study

    apikey : str
        API key for user
    '''
    dv_url, headers, params = _make_info(dv_url, study, apikey)
    lock_status = requests.get(f'{dv_url}/api/datasets/:persistentId/locks',
                               headers=headers,
                               params=params, timeout=300)
    lock_status.raise_for_status()
    data = lock_status.json().get('data')
    if data:
        LOGGER.warning('Study %s has been locked', study)
        LOGGER.warning('Lock info:\n%s', lock_status.json())
        return True
    return False

def force_notab_unlock(study, dv_url, fid, apikey, try_uningest=True) -> int:
    '''
    Forcibly unlocks and uningests
    to prevent tabular file processing. Required if mime and filename
    spoofing is not sufficient.

    Returns 0 if unlocked, file id if locked (and then unlocked).

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

    try_uningest : bool
        Try to uningest the file that was locked.
        Default: True
    '''
    dv_url, headers, params = _make_info(dv_url, study, apikey)
    force_unlock = requests.delete(f'{dv_url}/api/datasets/:persistentId/locks',
                                   params=params, headers=headers,
                                   timeout=300)
    LOGGER.warning('Lock removed for %s', study)
    LOGGER.warning('Lock status:\n %s', force_unlock.json())
    if try_uningest:
        uningest_file(dv_url, fid, apikey, study)
        return int(fid)
    return 0

def uningest_file(dv_url, fid, apikey, study='n/a'):
    '''
    Tries to uningest a file that has been ingested.
    Requires superuser API key.

    ----------------------------------------
    Parameters:

    dv_url : str
        URL to base Dataverse installation

    fid : int or str
        File ID of file to uningest

    apikey : str
        API key for superuser

    study : str
        Optional handle parameter for log messages
    '''
    dv_url, headers, params = _make_info(dv_url, fid, apikey)
    fid = params['persistentId']
    #TODONE: Awaiting answer from Harvard on how to remove progress bar
    #for uploaded tab files that squeak through.
    #Answer: you can't!
    try:
        uningest = requests.post(f'{dv_url}/api/files/{fid}/uningest',
                                 headers=headers,
                                 timeout=300)
        LOGGER.warning('Ingest halted for file %s for fileID %s', fid, study)
        uningest.raise_for_status()
    except requests.exceptions.HTTPError:
        LOGGER.error('Uningestion error: %s', uningest.reason)
        print(uningest.reason)

def upload_file(fpath, hdl, **kwargs):
    '''
    Uploads file to Dataverse study and sets file metadata and tags.

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

        nowait : bool
            OPTIONAL
            Force a file unlock and uningest instead of waiting for processing
            to finish

        trunc : str
            OPTIONAL
            Leftmost portion of path to remove
    '''
    #Why are SPSS files getting processed anyway?
    #Does SPSS detection happen *after* upload
    #Does the file need to be renamed post hoc?
    #I don't think this can be fixed. Goddamitsomuch.
    if kwargs['dv'].endswith(os.sep):
        dvurl = kwargs['dv'][:-1]
    else:
        dvurl = kwargs['dv']
    if os.path.splitext(fpath)[1].lower() in NOTAB:
        file_name_clean = os.path.basename(fpath)
        #file_name = os.path.basename(fpath) + '.NOPROCESS'
        # using .NOPROCESS doesn't seem to work?
        file_name = os.path.basename(fpath) + '.NOPROCESS'
    else:
        file_name = os.path.basename(fpath)
        file_name_clean = file_name

    mime = mimetypes.guess_type(fpath)[0]
    if file_name.endswith('.NOPROCESS') or mime == 'application/zip':
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
    try:
        print(upload.json())
    except json.decoder.JSONDecodeError:
        #This can happend when Glassfish crashes
        LOGGER.critical(upload.text)
        print(upload.text)
        err = ('It\'s possible Glassfish may have crashed. '
               'Check server logs for anomalies')
        LOGGER.exception(err)
        print(err)
        raise
    #SPSS files still process despite spoof, so there's
    #a forcible unlock check
    fid = upload.json()['data']['files'][0]['dataFile']['id']
    print(f'FID: {fid}')
    if kwargs.get('nowait') and check_lock(dvurl, hdl, kwargs['apikey']):
        force_notab_unlock(hdl, dvurl, fid, kwargs['apikey'])
    else:
        while check_lock(dvurl, hdl, kwargs['apikey']):
            time.sleep(10)

    if upload.status_code != 200:
        LOGGER.critical('Upload failure: %s', (upload.status_code, upload.reason))
        raise DvGeneralUploadError(f'\nReason: {(upload.status_code, upload.reason)}'
                                   f'\n{upload.text}')

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

    trunc : str
       Leftmost portion of Dataverse study file path to remove.
       eg: trunc ='/home/user/' if the tsv field is
       '/home/user/Data/ASCII'
       would set the path for that line of the tsv to 'Data/ASCII'.
       Defaults to None.

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
        #dirlabel = file_path(row[0], './')
        dirlabel = file_path(row[0], kwargs.get('trunc', ''))
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
