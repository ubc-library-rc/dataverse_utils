'''
Bagit archiver class for dataverse_utils
'''
import hashlib
import json
import logging
import pathlib
import zipfile

import bagit
import bs4
import tqdm
import requests

import dataverse_utils.collections as dvc

LOGGER = logging.Logger(__name__)

class PIDError(Exception):
    '''Raise on invalid PIDs being passed'''

class DigestMismatchError(Exception):
    '''Raise on hex digest mismatches'''

class Archive:
    '''
    All in one
   '''
    def __init__(self, **kwargs):
        '''
        Bagit archive creator

        Parameters
        ----------
        **kwargs
            Required parameters:
            url : str
                URL of Dataverse instance
            key : str
                API key with appropriate privileges
            target_dir : str
                Destination directory for Bagit archive
            pid : str
                DOI or handle of study object to Bag

        Optional parameters
        -------------------
        **kwargs
            session : requests.Session
            all_versions : bool
                Create bag using *all* versions, not just current versions
            contact_email : str
                Contact email for Bag. Depending on the Dataverse installation,
                email harvest may be suppressed via API.
            contact_phone : str
                Contact number for Bag, in international format.
                ie +1 604 555 5555
                   +49 30 5555 5555

        Notes
        -----
        Workflow usually will proceed like this:
        ```
        bag = Archive(**kwargs) #whatever kwargs is
        bag.write_metadata()
        bag.process_files()
        bag.bagit_meta()
        bag.refresh_bag()
        if args.compress:
            bag.compress_bag(expunge=True)
        ```

        '''
        self.kwargs = kwargs
        self.study = None
        self.__tpid = self.kwargs['pid'].replace(':','-').replace('/','_')
        self.__validate_pid()
        self.study = dvc.StudyMetadata(**self.kwargs)
        #Default for Dataverse is md5
        self.kwargs['digest_type'] = kwargs.get('digest_type', 'md5')
        #unzip an archive in the target dir so that you don't
        #waste time downloading needlessly
        self.__zip = pathlib.Path(self.kwargs['target_dir'], f'{self.__tpid}.zip')
        x=self.__zip
        if self.__zip.exists():
            self.__unzip_existing_bag()
        self.bag = self.__bag()
        self.session = kwargs.get('session', requests.Session())
        self.session.mount('https://',
                           requests.adapters.HTTPAdapter(max_retries=dvc.RETRY))
        self.limiter = dvc.RateLimiter(rate_limit_on=kwargs.get('rate_limit_on', True),
                                      rate_limit_min=kwargs.get('rate_limit_min',0.3),
                                      rate_limit_max=kwargs.get('rate_limit_max', 2))

    def __validate_pid(self):
        '''Basic PID format check'''
        if self.kwargs['pid'][:3].lower() not in ['hdl', 'doi']:
            raise PIDError(f'{self.kwargs["pid"]} is not a valid PID')

    def __bag(self):
        '''Create a Bagit bag'''
        try:
            baggy = bagit.Bag(self.target_dir)

        except bagit.BagError:
            self.__make_dir()
            baggy = bagit.make_bag(self.target_dir)
            baggy.save(manifests=True)

        if self.kwargs['digest_type'] not in baggy.algorithms:
            baggy.algorithms.append(self.kwargs['digest_type'])
            #bagit source line 1258
        return baggy

    @property
    def target_dir(self):
        '''
        Create a clean target directory
        '''
        return pathlib.Path(self.kwargs['target_dir'], self.__tpid).expanduser().absolute()

    def __make_dir(self):
        '''
        Create target dir
        '''
        self.target_dir.mkdir(exist_ok=True)

    def write_metadata(self):
        '''
        Write study metadata
        '''
        #Bag should exist, everything gets dumped into 'data'
        mpath = pathlib.Path(self.target_dir, 'data','metadata')
        mpath.mkdir(exist_ok=True)
        if self.kwargs['all_versions']:
            for meta in [('study_metadata_all_versions',  self.study.all_versions),
                         ('file_metadata_all_versions', self.study.all_files)]:
                with open(pathlib.Path(mpath, f'{meta[0]}.json'),
                          mode='w', encoding='utf-8') as f:
                    json.dump(meta[1], f)
            for ver in self.study.versions:
                wpath = pathlib.Path(mpath, ver)
                wpath.mkdir(exist_ok=True)
                with open(pathlib.Path(wpath,f'metadata_version_{ver}.json'),
                                       mode='w', encoding='utf-8') as f:
                    json.dump(self.study.version_metadata(ver),f)
                with open(pathlib.Path(wpath, f'file_metadata_{ver}.json'),
                          mode='w', encoding='utf-8') as f:
                    _maj, _min = (int(_) for _ in ver.split('.'))
                    fmeta ={'files': [_['files'] for _ in self.study.all_versions['data']
                            if _['versionNumber']==_maj and
                            _['versionMinorNumber']==_min][0]}
                    json.dump(fmeta,f)

        else:
            with open(pathlib.Path(mpath,'study_metadata.json'),
                       mode='w', encoding='utf-8') as f:
                json.dump(self.study.study_meta, f)

    def __should_download(self, hexdigest=str, digest_type:str=None)->bool:
        '''
        Checks if file is present in bag and needs to be downloaded
        '''
        if not digest_type:
            digest_type = self.kwargs['digest_type']
        if not self.bag:
            return True
        if hexdigest not in [_.get(digest_type.lower(),'') for _ in self.bag.entries.values()]:
            return True
        return False

    def download_file(self, fid=int)->requests.models.Response:
        '''
        Download files

        Parameters
        ----------
        fid : int
            Dataverse file ID
        '''
        #check hash with hashlib
        data = self.session.get(f'{self.kwargs["url"]}/api/access/datafile/{fid}',
                                    headers=self.study.headers,
                                    params={'format':'original'},
                                    stream=True,
                                    timeout=self.kwargs.get('timeout', 15))
        self.limiter.rate_limit()
        return data

    def produce_digest(self, fobj:bytes, prot:str = 'md5') -> str:
        '''
        Returns hex digest

        Parameters
        ----------
        prot : str
            Hash type. Supported hashes: 'sha1', 'sha224', 'sha256',
            'sha384','sha512', 'blake2b', 'blake2s', 'md5'.
            default='md5'
        blocksize : int
            Read block size in bytes
        '''
        ok_hash = {'sha1' : hashlib.sha1(),
                   'sha224' : hashlib.sha224(),
                   'sha256' : hashlib.sha256(),
                   'sha384' : hashlib.sha384(),
                   'sha512' : hashlib.sha512(),
                   'blake2b' : hashlib.blake2b(),
                   'blake2s' : hashlib.blake2s(),
                   'md5': hashlib.md5()}
        #blocksize: int = 2**16
        #fobj.seek(0)
        try:
            _hash = ok_hash[prot]
        except (UnboundLocalError, KeyError):
            message = ('Unsupported hash type. Valid values are '
                       f'{list(ok_hash)}.')
            LOGGER.exception('Unsupported hash type. Valid values are %s', message)
            raise

        #fblock = fobj.read(blocksize)
        #while fblock:
        #    _hash.update(fblock)
        #    fblock = fobj.read(blocksize)
        #return _hash.hexdigest()
        _hash.update(fobj)
        return _hash.hexdigest()

    def verify_download(self, fobj:bytes, prot:str, correct_digest:str)->bool:
        '''Validate files by comparing calculated digests with the stated ones

        Parameters
        ----------
        fobj : bytes
            Bytes to compare, normally requests.content
        prot : str
            Protocol (ie, md5, etc)
        correct_digest : str
            Correct hex digest
        '''
        calc = self.produce_digest(fobj, prot.lower())
        if calc != correct_digest:
            LOGGER.error('%s comparison error: %s should be %s',
                         prot, calc, correct_digest)
            return False
        LOGGER.info('%s match: %s', prot, calc)
        return True

    def save_file_to_bag(self, fobj:bytes, validate:bool=True, **kwargs):
        '''
        Save the file to the bag file store

        Parameters
        ----------
        fobj : bytes
            Requests.content
        validate : bool
            Re-validate the hex digest against the *written* file
        kwargs : dict
            File information. Must include either 'dataFile_originalFileName, 'label' or
            'dataFile_filename'. If validating, must *also* include
            'dataFile_checksum_type' and 'dataFile_checksum_value'
            Naming priority is in that order, as nature intended.

        Notes
        -----
        Files are saved to the directory called *files* inside the
        data directory in the bag.
        '''
        fname = kwargs.get('dataFile_originalFileName',
                           kwargs.get('label', kwargs['dataFile_filename']))
        files_loc = pathlib.Path(self.target_dir, 'data','files')
        if not files_loc.exists():
            files_loc.mkdir(exist_ok=True)
        writefile = pathlib.Path(files_loc, fname)
        with open(writefile, mode='wb') as f:
            f.write(fobj)
        if validate:
            with open(writefile, mode='rb') as f:
                if not self.verify_download(f.read(),
                                           kwargs['dataFile_checksum_type'],
                                           kwargs['dataFile_checksum_value']):
                    LOGGER.error('Hex digest mismatch between written file and downloaded file')
                    LOGGER.error('File information: {kwargs}')
                    msg=('Hex digest mismatch between written file and '
                        f'downloaded file. file id: {kwargs.get("dataFile_id", "N/A")}, '
                        f'study PID: {kwargs.get("dataFile_persistentId", "N/A")}')
                    raise DigestMismatchError(msg)

    def process_files(self):
        '''
        Iterate over files to download and write them, if necessary,
        to physical media
        '''
        # self.study['current_version']
        file_list = ([_ for _ in self.study.all_files if
                    _['versionStatement'] == self.study.current_version]
                    if not self.kwargs['all_versions']
                    else self.study.all_files)

        for file in tqdm.tqdm(file_list,
                              desc='Download check',
                              unit='file',
                              leave=False,
                              bar_format=dvc.BAR_FORMAT):
            down = self.__should_download(file['dataFile_checksum_value'],
                                        file.get('dataFile_checksum_type', 'md5'))
            if down:
                download = self.download_file(file['dataFile_id'])
                #breakpoint()
                if not self.verify_download(download.content,
                                            file['dataFile_checksum_type'].lower(),
                                            file['dataFile_checksum_value']):
                    LOGGER.error('Validation error for file with ID %s', file['dataFile_id'])
                    raise DigestMismatchError(f'Validation error for {file}')
                self.save_file_to_bag(download.content, **file)

    def bagit_meta(self):
        '''Add applicable metadata for the Bagit bag'''
        #See spec:  https://datatracker.ietf.org/doc/html/rfc8493#section-2.1.1
        self.bag.info['Contact-Name'] = self.study.get('authorName')
        self.bag.info['Contact-Email'] = self.kwargs.get('contact_email',
                                              self.study.get('datasetContactEmail'))
        self.bag.info['Contact-Phone'] = self.kwargs.get('contact_phone')
        #bag date automatically set
        #self.bag.info['Bagging-Date'] = datetime.datetime.now().strftime('%Y-%M-%d')
        size = sum(pathlib.Path(a[0], c).stat().st_size
                   for a in pathlib.Path.walk(self.target_dir)
                   for c in a[2])
        self.bag.info['Bag-Size'] = f'{size/1024**2} MB'
        self.bag.info['Source-Organization'] = self.kwargs['url']
        if self.study.get('dsDescriptionValue'):
            desc = bs4.BeautifulSoup(self.study['dsDescriptionValue'], 'html.parser').text
            self.bag.info['External-Description'] = desc
        self.bag.info['External-Identifier'] = self.study.pid
        repl_dict = {}
        for k, v in self.bag.info.items():
            if v:
                repl_dict.update({k:v})
        self.bag.info = repl_dict

    def refresh_bag(self):
        '''Refresh to keep it fresh'''
        self.bag.save(manifests=True)

    def __unzip_existing_bag(self):
        with zipfile.ZipFile(self.__zip) as zz:
            #Note! self.kwargs['target_dir'], or the top level not including PID
            zz.extractall(path=self.kwargs['target_dir'])

    def compress_bag(self, expunge=False):
        '''Compress the bag into a zip file.
        The zip file will have the same ID as the bag directory,
        ['pid'].replace(':','-').replace('/','_')

        Parameters
        ----------
        expunge : bool
            If True, delete uncompressed Bagit archve
        '''
        with zipfile.ZipFile(self.__zip,
                             mode='w',
                             compression=zipfile.ZIP_DEFLATED,
                             allowZip64=True,
                             compresslevel=9) as zipper:
            #You could iterate without the second loop but it's much
            #nicer if you can use tqdm
            top_level = self.target_dir.name
            filedict = []
            for p in self.target_dir.walk():
                for f in p[2]:
                    file = pathlib.Path(p[0],f)
                    _index = file.parts.index(top_level)
                    name = pathlib.Path('/'.join(file.parts[_index:]))
                    filedict.append({'file':file, 'arcname':name})
            #Iterate over this dict because it's all in one place
            for _ in tqdm.tqdm(filedict,
                              desc='Files',
                              unit='file',
                              leave=False,
                              bar_format=dvc.BAR_FORMAT):
                zipper.write(_['file'], arcname=_['arcname'])
        if expunge:
            for d in self.target_dir.walk():
                for f in d[2]:
                    delme = pathlib.Path(d[0], f)
                    if delme.exists():
                        delme.unlink()
            for d in self.target_dir.walk(top_down=False):
                for sd in d[1]:
                    delme = pathlib.Path(d[0], sd)
                    if delme.exists():
                        delme.rmdir()
            self.target_dir.rmdir()
