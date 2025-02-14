# API Reference
<a id="dataverse_utils"></a>

## dataverse\_utils

Generalized dataverse utilities. Note that
`import dataverse_utils` is the equivalent of
`import dataverse_utils.dataverse_utils`

<a id="dataverse_utils.dvdata"></a>

## dataverse\_utils.dvdata

Dataverse studies and files

<a id="dataverse_utils.dvdata.Study"></a>

### Study Objects

```python
class Study(dict)
```

Dataverse record. Dataverse study records are pure metadata so this
is represented with a dictionary.

<a id="dataverse_utils.dvdata.Study.__init__"></a>

##### \_\_init\_\_

```python
def __init__(pid: str, url: str, key: str, **kwargs)
```

pid : str
    Record persistent identifier: hdl or doi
url : str
    Base URL to host Dataverse instance
key : str
    Dataverse API key with downloader privileges

<a id="dataverse_utils.dvdata.Study.get_version"></a>

##### get\_version

```python
@classmethod
def get_version(cls, url: str, timeout: int = 100) -> float
```

Returns a float representing a Dataverse version number.
Floating point value composed of:
float(f'{major_version}.{minor_verson:03d}{patch:03d}')
ie, version 5.9.2 would be 5.009002
url : str
    URL of base Dataverse instance. eg: 'https://abacus.library.ubc.ca'
timeout : int
    Request timeout in seconds

<a id="dataverse_utils.dvdata.Study.set_version"></a>

##### set\_version

```python
def set_version(url: str, timeout: int = 100) -> None
```

Sets self['target_version'] to appropriate integer value *AND*
formats self['upload_json'] to correct JSON format

url : str
    URL of *target* Dataverse instance
timeout : int
    request timeout in seconds

<a id="dataverse_utils.dvdata.Study.fix_licence"></a>

##### fix\_licence

```python
def fix_licence() -> None
```

With Dataverse v5.10+, a licence type of 'NONE' is now forbidden.
Now, as per <https://guides.dataverse.org/en/5.14/api/sword.html        ?highlight=invalid%20license>,
non-standard licences may be replaced with None.

This function edits the same Study object *in place*, so returns nothing.

<a id="dataverse_utils.dvdata.Study.production_location"></a>

##### production\_location

```python
def production_location() -> None
```

Changes "multiple" to True where typeName == 'productionPlace' in
Study['upload_json'] Changes are done
*in place*.
This change came into effect with Dataverse v5.13

<a id="dataverse_utils.dvdata.File"></a>

### File Objects

```python
class File(dict)
```

Class representing a file on a Dataverse instance

<a id="dataverse_utils.dvdata.File.__init__"></a>

##### \_\_init\_\_

```python
def __init__(url: str, key: str, **kwargs)
```

url : str
    Base URL to host Dataverse instance
key : str
    Dataverse API key with downloader privileges
id : int or str
    File identifier; can be a file ID or PID
args : list
kwargs : dict

To initialize correctly, pass a value from Study['file_info'].

Eg: File('https://test.invalid', 'ABC123', **Study_instance['file_info'][0])

<a id="dataverse_utils.dvdata.File.download_file"></a>

##### download\_file

```python
def download_file()
```

Downloads the file to a temporary location. Data will be in the ORIGINAL format,
not Dataverse-processed TSVs

<a id="dataverse_utils.dvdata.File.del_tempfile"></a>

##### del\_tempfile

```python
def del_tempfile()
```

Delete tempfile if it exists

<a id="dataverse_utils.dvdata.File.produce_digest"></a>

##### produce\_digest

```python
def produce_digest(prot: str = 'md5', blocksize: int = 2**16) -> str
```

Returns hex digest for object

    fname : str
       Path to a file object

    prot : str
       Hash type. Supported hashes: 'sha1', 'sha224', 'sha256',
          'sha384', 'sha512', 'blake2b', 'blake2s', 'md5'.
          Default: 'md5'

    blocksize : int
       Read block size in bytes

<a id="dataverse_utils.dvdata.File.verify"></a>

##### verify

```python
def verify() -> None
```

Compares checksum with stated checksum

<a id="dataverse_utils.dvdata.FileInfo"></a>

### FileInfo Objects

```python
class FileInfo(dict)
```

An object representing all of a dataverse study's files.
Easily parseable as a dict.

data_chunk : dict
    Metadata block;  the JSON output of a call to
    [server]/api/datasets/:persistentId/versions
server: str
    Base URL of dataverse server (like 'https://abacus.library.ubc.ca')

<a id="dataverse_utils.dvdata.FileInfo.__init__"></a>

##### \_\_init\_\_

```python
def __init__(**kwargs) -> None
```

Required keyword parameters:

url : str
    Base URL of dataverse installation
pid : str
    Handle or DOI of study

Optional keyword parameters:

apikey : str
    Dataverse API key; required for DRAFT or restricted material
timeout : int
    Optional timeout in seconds

<a id="dataverse_utils.scripts.dv_list_files"></a>

## dataverse\_utils.scripts.dv\_list\_files

Utility to dump [selected] file information for a particular dataverse record.

<a id="dataverse_utils.scripts.dv_list_files.parse"></a>

##### parse

```python
def parse() -> argparse.ArgumentParser()
```

Parses the arguments from the command line.

Returns argparse.ArgumentParser

<a id="dataverse_utils.scripts.dv_list_files.main"></a>

##### main

```python
def main() -> None
```

The primary function

<a id="dataverse_utils.scripts.dv_record_copy"></a>

## dataverse\_utils.scripts.dv\_record\_copy

Copies a dataverse record to collection
OR copies a record to an existing PID.

That way all you have to do
is edit a few fields in the GUI instead of
painfully editing JSON or painfully using the
Dataverse GUI.

<a id="dataverse_utils.scripts.dv_record_copy.parsley"></a>

##### parsley

```python
def parsley() -> argparse.ArgumentParser()
```

Parses the arguments from the command line.

Returns argparse.ArgumentParser

<a id="dataverse_utils.scripts.dv_record_copy.main"></a>

##### main

```python
def main()
```

You know what this does

<a id="dataverse_utils.scripts.dv_study_migrator"></a>

## dataverse\_utils.scripts.dv\_study\_migrator

Copies an entire record and migrates it *including the data*

<a id="dataverse_utils.scripts.dv_study_migrator.parsley"></a>

##### parsley

```python
def parsley() -> argparse.ArgumentParser()
```

Parses the arguments from the command line.

Returns argparse.ArgumentParser

<a id="dataverse_utils.scripts.dv_study_migrator.upload_file_to_target"></a>

##### upload\_file\_to\_target

```python
def upload_file_to_target(indict: dict, pid, source_url, source_key,
                          target_url, target_key)
```

Uploads a single file with metadata to a dataverse record

<a id="dataverse_utils.scripts.dv_study_migrator.remove_target_files"></a>

##### remove\_target\_files

```python
def remove_target_files(record: dataverse_utils.dvdata.Study,
                        timeout: int = 100)
```

Removes all files from a dataverse record.
    record: dataverse_utils.dvdata.Study
    timeout: int
        Timeout in seconds

<a id="dataverse_utils.scripts.dv_study_migrator.main"></a>

##### main

```python
def main()
```

Run this, obviously

<a id="dataverse_utils.scripts.dv_ldc_uploader"></a>

## dataverse\_utils.scripts.dv\_ldc\_uploader

Auto download/upload LDC metadata and files.

python3 uploadme.py LDC20201S01 . . . LDC2021T21 apikey

<a id="dataverse_utils.scripts.dv_ldc_uploader.parse"></a>

##### parse

```python
def parse() -> argparse.ArgumentParser()
```

Parses the arguments from the command line.

Returns argparse.ArgumentParser

<a id="dataverse_utils.scripts.dv_ldc_uploader.upload_meta"></a>

##### upload\_meta

```python
def upload_meta(ldccat: str,
                url: str,
                key: str,
                dvs: str,
                verbose: bool = False,
                certchain: str = None) -> str
```

Uploads metadata to target dataverse collection. Returns persistentId.

ldccat : str
    Linguistic Data Consortium catalogue number
url : str
    URL to base instance of Dataverse installation
key : str
    API key
dvs : str
    Target Dataverse collection short name
certchain : str
    Path to LDC .PEM certificate chain

<a id="dataverse_utils.scripts.dv_ldc_uploader.main"></a>

##### main

```python
def main() -> None
```

Uploads metadata and data to Dataverse collection/study respectively

<a id="dataverse_utils.scripts.dv_pg_facet_date"></a>

## dataverse\_utils.scripts.dv\_pg\_facet\_date

Reads the date from a Dataverse study and forces the facet sidebar to use that
date by manually updating the Dataverse Postgres database.

This *must* be run on the server that hosts a Dataverse installation,
and the user must supply, at a minimum, the database password and
a persistent ID to be read, as well as a date type.

Requires two non-standard python libraries: psycopg2
(use psycopg2-binary to avoid installing from source) and requests.

Psycopg2 is not part of the requirements for dataverse_utils
because it is only used for the server portion of these utilities,
and hence useless for them.

<a id="dataverse_utils.scripts.dv_pg_facet_date.parsely"></a>

##### parsely

```python
def parsely() -> argparse.ArgumentParser
```

Command line argument parser

<a id="dataverse_utils.scripts.dv_pg_facet_date.parse_dtype"></a>

##### parse\_dtype

```python
def parse_dtype(dtype) -> str
```

Returns correctly formatted date type string for Dataverse API

---
dtype : str
    One of the allowable values from the parser

<a id="dataverse_utils.scripts.dv_pg_facet_date.write_old"></a>

##### write\_old

```python
def write_old(data) -> None
```

Writes older data to a tsv file. Assumes 4 values per item:
id, authority, identifier, publicationdate.

publicationdate is assumed to be a datetime.datetime instance.
------

**Arguments**:

  
  data : list
  Postqres query output list (ie, data = cursor.fetchall())

<a id="dataverse_utils.scripts.dv_pg_facet_date.write_sql"></a>

##### write\_sql

```python
def write_sql(data) -> None
```

Write SQL to file

<a id="dataverse_utils.scripts.dv_pg_facet_date.get_datetime"></a>

##### get\_datetime

```python
def get_datetime(datestr) -> (datetime.datetime, str)
```

Return datetime from poorly formatted Dataverse dates string

----
datestr : str
    Dataverse date returned by API

<a id="dataverse_utils.scripts.dv_pg_facet_date.fetch_date_api"></a>

##### fetch\_date\_api

```python
def fetch_date_api(url, key, pid, dtype) -> str
```

Returns the requested date string from the Dataverse study record

----
url : str
    Base URL of Dataverse installation
key :str
    API key for Dataverse user
pid : str
    Persistent identifier for Dataverse study
dtype : str
    Date type required

<a id="dataverse_utils.scripts.dv_pg_facet_date.reindex"></a>

##### reindex

```python
def reindex(pid) -> dict
```

Reindexes study in place. Localhost access only.

----
pid : str
    PersistentId for Dataverse study

<a id="dataverse_utils.scripts.dv_pg_facet_date.main"></a>

##### main

```python
def main()
```

The heart of the application

<a id="dataverse_utils.scripts.dv_release"></a>

## dataverse\_utils.scripts.dv\_release

Bulk release script for Dataverse.

This is almost identical to the dryad2dataverse bulk
releaser except that the defaults are changed to
https://abacus.library.ubc.ca

<a id="dataverse_utils.scripts.dv_release.argp"></a>

##### argp

```python
def argp()
```

Parses the arguments from the command line.

Returns arparse.ArgumentParser

<a id="dataverse_utils.scripts.dv_release.Dverse"></a>

### Dverse Objects

```python
class Dverse()
```

An object representing a Dataverse installation

<a id="dataverse_utils.scripts.dv_release.Dverse.__init__"></a>

##### \_\_init\_\_

```python
def __init__(dvurl, apikey, dvs)
```

Intializes Dataverse installation object.

**Arguments**:

- `dvurl`: str. URL to base Dataverse installation
(eg. 'https://abacus.library.ubc.ca')
- `apikey`: str. API key for Dataverse user
- `dv`: str. Short name of target Dataverse collection (eg. 'statcan')

<a id="dataverse_utils.scripts.dv_release.Dverse.study_list"></a>

##### study\_list

```python
@property
def study_list() -> list
```

Returns a list of all studies (published or not) in
the Dataverse collection

<a id="dataverse_utils.scripts.dv_release.Dverse.unreleased"></a>

##### unreleased

```python
@property
def unreleased(all_stud: list = None) -> list
```

Finds only unreleased studies from a list of studies

**Arguments**:

- `all_stud`: list. List of Dataverse studies. Defaults to output of
Dverse.get_study_list()

<a id="dataverse_utils.scripts.dv_release.Study"></a>

### Study Objects

```python
class Study()
```

Instance representing a Dataverse study

<a id="dataverse_utils.scripts.dv_release.Study.__init__"></a>

##### \_\_init\_\_

```python
def __init__(**kwargs)
```

:kwarg dvurl: str. Base URL for Dataverse instance
:kwarg apikey: str. API key for Dataverse user
:kwarg pid: str. Persistent identifier for study
:kwarg stime: int. Time between file lock checks. Default 10
:kwarg verbose: Verbose output. Default False

<a id="dataverse_utils.scripts.dv_release.Study.status_ok"></a>

##### status\_ok

```python
def status_ok()
```

Checks to see if study has a lock. Returns True if OK to continue, else False.

<a id="dataverse_utils.scripts.dv_release.Study.release_me"></a>

##### release\_me

```python
def release_me(interactive=False)
```

Releases study and waits until it's unlocked before returning to the function


<a id="dataverse_utils.scripts.dv_release.main"></a>

##### main

```python
def main()
```

The primary function. Will release all unreleased studies in the
the target Dataverse collection, or selected studies as required.

<a id="dataverse_utils.scripts.dv_del"></a>

## dataverse\_utils.scripts.dv\_del

Dataverse Bulk Deleter
Deletes unpublished studies at the command line

<a id="dataverse_utils.scripts.dv_del.delstudy"></a>

##### delstudy

```python
def delstudy(dvurl, key, pid)
```

Deletes Dataverse study

dvurl : str
    Dataverse installation base URL
key : str
    Dataverse user API key
pid : str
    Dataverse collection study persistent identifier

<a id="dataverse_utils.scripts.dv_del.conf"></a>

##### conf

```python
def conf(tex)
```

Confirmation dialogue checker. Returns true if "Y" or "y"

<a id="dataverse_utils.scripts.dv_del.getsize"></a>

##### getsize

```python
def getsize(dvurl, pid, key)
```

Returns size of Dataverse study. Mostly here for debugging.
dvurl : str
    Dataverse installation base URL
pid : str
    Dataverse collection study persistent identifier
key : str
    Dataverse user API key

<a id="dataverse_utils.scripts.dv_del.parsley"></a>

##### parsley

```python
def parsley() -> argparse.ArgumentParser
```

Argument parser as separate function

<a id="dataverse_utils.scripts.dv_del.main"></a>

##### main

```python
def main()
```

Command line bulk deleter

<a id="dataverse_utils.scripts.dv_replace_licence"></a>

## dataverse\_utils.scripts.dv\_replace\_licence

Replace all licence in a study with one read from an external
markdown file. This requires using a different API, the
"semantic metadata api"
https://guides.dataverse.org/en/5.6/developers/
dataset-semantic-metadata-api.html

<a id="dataverse_utils.scripts.dv_replace_licence.parsley"></a>

##### parsley

```python
def parsley() -> argparse.ArgumentParser()
```

parse the command line

<a id="dataverse_utils.scripts.dv_replace_licence.replace_licence"></a>

##### replace\_licence

```python
def replace_licence(hdl, lic, key, url='https://abacus.library.ubc.ca')
```

Replace the licence for a dataverse study with
persistent ID hdl.

---
hdl : str
    Dataverse persistent ID
lic : str
    Licence text in Markdown format
key : str
    Dataverse API key
url : str
    Dataverse installation base URL

<a id="dataverse_utils.scripts.dv_replace_licence.republish"></a>

##### republish

```python
def republish(hdl, key, url='https://abacus.library.ubc.ca')
```

Republish study without updating version

---
hdl : str
    Persistent Id
key : str
    Dataverse API key
url : str
    Dataverse installation base URL

<a id="dataverse_utils.scripts.dv_replace_licence.print_stat"></a>

##### print\_stat

```python
def print_stat(rjson)
```

Prints error status to stdout

<a id="dataverse_utils.scripts.dv_replace_licence.main"></a>

##### main

```python
def main()
```

Main script function

<a id="dataverse_utils.scripts.dv_upload_tsv"></a>

## dataverse\_utils.scripts.dv\_upload\_tsv

Uploads data sets to a dataverse installation from the
contents of a TSV (tab separated value)
file. Metadata, file tags, paths, etc are all read
from the TSV.

<a id="dataverse_utils.scripts.dv_upload_tsv.parse"></a>

##### parse

```python
def parse() -> argparse.ArgumentParser()
```

Parses the arguments from the command line.

Returns argparse.ArgumentParser

<a id="dataverse_utils.scripts.dv_upload_tsv.main"></a>

##### main

```python
def main() -> None
```

Uploads data to an already existing Dataverse study

<a id="dataverse_utils.scripts.dv_manifest_gen"></a>

## dataverse\_utils.scripts.dv\_manifest\_gen

Creates a file manifest in tab separated value format
which can be used with other dataverse_util library utilities
and functions to upload files complete with metadata.

<a id="dataverse_utils.scripts.dv_manifest_gen.parse"></a>

##### parse

```python
def parse() -> argparse.ArgumentParser()
```

Parses the arguments from the command line.

Returns argparse.ArgumentParser

<a id="dataverse_utils.scripts.dv_manifest_gen.quotype"></a>

##### quotype

```python
def quotype(quote: str) -> int
```

Parse quotation type for csv parser.

returns csv quote constant.

<a id="dataverse_utils.scripts.dv_manifest_gen.main"></a>

##### main

```python
def main() -> None
```

The main function call

<a id="dataverse_utils.dataverse_utils"></a>

## dataverse\_utils.dataverse\_utils

A collection of Dataverse utilities for file and metadata
manipulation

<a id="dataverse_utils.dataverse_utils.DvGeneralUploadError"></a>

### DvGeneralUploadError Objects

```python
class DvGeneralUploadError(Exception)
```

Raised on non-200 URL response

<a id="dataverse_utils.dataverse_utils.Md5Error"></a>

### Md5Error Objects

```python
class Md5Error(Exception)
```

Raised on md5 mismatch

<a id="dataverse_utils.dataverse_utils.make_tsv"></a>

##### make\_tsv

```python
def make_tsv(start_dir,
             in_list=None,
             def_tag='Data',
             inc_header=True,
             mime=False,
             quotype=csv.QUOTE_MINIMAL,
             **kwargs) -> str
```

Recurses the tree for files and produces tsv output with
with headers 'file', 'description', 'tags'.

The 'description' is the filename without an extension.

Returns tsv as string.

------------------------------------------

**Arguments**:

  
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
  
  mime : bool
  Include automatically determined mimetype
  
- `quotype` - int
  integer value or csv quote type.
  Default = csv.QUOTE_MINIMAL
  Acceptable values:
  csv.QUOTE_MINIMAL / 0
  csv.QUOTE_ALL / 1
  csv.QUOTE_NONNUMERIC / 2
  csv.QUOTE_NONE / 3
  
- `path` - bool
  If true include a 'path' field so that you can type
  in a custom path instead of actually structuring
  your data

<a id="dataverse_utils.dataverse_utils.dump_tsv"></a>

##### dump\_tsv

```python
def dump_tsv(start_dir, filename, in_list=None, **kwargs)
```

Dumps output of make_tsv manifest to a file.

------------------------------------------

**Arguments**:

  
  start_dir : str
  Path to start directory
  
  in_list : list
  List of files for which to create manifest entries. Will
  default to recursive directory crawl
  
  OPTIONAL KEYWORD ARGUMENTS
  
  def_tag : str
  Default Dataverse tag (eg, Data, Documentation, etc)
  Separate tags with an easily splitable character:
  eg. ('Data, 2016')
- `Default` - 'Data'
  
  inc_header : bool
  Include header for tsv.
  Default : True
  
- `quotype` - int
  integer value or csv quote type.
  Default : csv.QUOTE_MINIMAL
  Acceptable values:
  csv.QUOTE_MINIMAL / 0
  csv.QUOTE_ALL / 1
  csv.QUOTE_NONNUMERIC / 2
  csv.QUOTE_NONE / 3

<a id="dataverse_utils.dataverse_utils.file_path"></a>

##### file\_path

```python
def file_path(fpath, trunc='') -> str
```

Create relative file path from full path string

>>> file_path('/tmp/Data/2011/excelfile.xlsx', '/tmp/')
'Data/2011'
>>> file_path('/tmp/Data/2011/excelfile.xlsx', '/tmp')
'Data/2011'

----------------------------------------

**Arguments**:

  
  fpath : str
  File location (ie, complete path)
  
  trunc : str
  Leftmost portion of path to remove

<a id="dataverse_utils.dataverse_utils.check_lock"></a>

##### check\_lock

```python
def check_lock(dv_url, study, apikey) -> bool
```

Checks study lock status; returns True if locked.

----------------------------------------

**Arguments**:

  
  dvurl : str
  URL of Dataverse installation
  
- `study` - str
  Persistent ID of study
  
  apikey : str
  API key for user

<a id="dataverse_utils.dataverse_utils.force_notab_unlock"></a>

##### force\_notab\_unlock

```python
def force_notab_unlock(study, dv_url, fid, apikey, try_uningest=True) -> int
```

Forcibly unlocks and uningests
to prevent tabular file processing. Required if mime and filename
spoofing is not sufficient.

Returns 0 if unlocked, file id if locked (and then unlocked).

----------------------------------------

**Arguments**:

  
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
- `Default` - True

<a id="dataverse_utils.dataverse_utils.uningest_file"></a>

##### uningest\_file

```python
def uningest_file(dv_url, fid, apikey, study='n/a')
```

Tries to uningest a file that has been ingested.
Requires superuser API key.

----------------------------------------

**Arguments**:

  
  dv_url : str
  URL to base Dataverse installation
  
  fid : int or str
  File ID of file to uningest
  
  apikey : str
  API key for superuser
  
  study : str
  Optional handle parameter for log messages

<a id="dataverse_utils.dataverse_utils.upload_file"></a>

##### upload\_file

```python
def upload_file(fpath, hdl, **kwargs)
```

Uploads file to Dataverse study and sets file metadata and tags.

----------------------------------------

**Arguments**:

  
  fpath : str
  file location (ie, complete path)
  
  hdl : str
  Dataverse persistent ID for study (handle or DOI)
  
  kwargs : dict
  
  other parameters. Acceptable keywords and contents are:
  
  dv : str
  REQUIRED
  url to base Dataverse installation
- `eg` - 'https://abacus.library.ubc.ca'
  
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
  
  rest : bool
  OPTIONAL
  Restrict file. Defaults to false unless True supplied
  
  mimetype : str
  OPTIONAL
  Mimetype of file. Useful if using File Previewers. Mimetype for zip files
  (application/zip) will be ignored to circumvent Dataverse's automatic
  unzipping function.
  
  label : str
  OPTIONAL
  If included in kwargs, this value will be used for the label
  
  timeout : int
  OPTIONAL
  Timeout in seconds
  
  override : bool
  OPTIONAL
  Ignore NOTAB (ie, NOTAB = [])
  
  timeout = int
  OPTIONAL
  Timeout in seconds

<a id="dataverse_utils.dataverse_utils.restrict_file"></a>

##### restrict\_file

```python
def restrict_file(**kwargs)
```

Restrict file in Dataverse study.

----------------------------------------

**Arguments**:

  
  
  kwargs : dict
  
  other parameters. Acceptable keywords and contents are:
  
  **One of pid or fid is required**
  pid : str
  file persistent ID
  
  fid : str
  file database ID
  
  dv : str
  REQUIRED
  url to base Dataverse installation
- `eg` - 'https://abacus.library.ubc.ca'
  
  apikey : str
  REQUIRED
  API key for user
  
  rest : bool
  On True, restrict. Default True

<a id="dataverse_utils.dataverse_utils.upload_from_tsv"></a>

##### upload\_from\_tsv

```python
def upload_from_tsv(fil, hdl, **kwargs)
```

Utility for bulk uploading. Assumes fil is formatted
as tsv with headers 'file', 'description', 'tags'.

'tags' field will be split on commas.

----------------------------------------

**Arguments**:

  
  fil : filelike object
  Open file object or io.IOStream()
  
  hdl : str
  Dataverse persistent ID for study (handle or DOI)
  
  trunc : str
  Leftmost portion of Dataverse study file path to remove.
- `eg` - trunc ='/home/user/' if the tsv field is
  '/home/user/Data/ASCII'
  would set the path for that line of the tsv to 'Data/ASCII'.
  Defaults to None.
  
  kwargs : dict
  
  other parameters. Acceptable keywords and contents are:
  
  dv : str
  REQUIRED
  url to base Dataverse installation
- `eg` - 'https://abacus.library.ubc.ca'
  
  apikey : str
  REQUIRED
  API key for user
  
  rest : bool
  On True, restrict access. Default False

<a id="dataverse_utils.ldc"></a>

## dataverse\_utils.ldc

Creates dataverse JSON from Linguistic Data Consortium
website page.

<a id="dataverse_utils.ldc.Ldc"></a>

### Ldc Objects

```python
class Ldc(ds.Serializer)
```

An LDC item (eg, LDC2021T01)

<a id="dataverse_utils.ldc.Ldc.__init__"></a>

##### \_\_init\_\_

```python
def __init__(ldc, cert=None)
```

Returns a dict with keys created from an LDC catalogue web
page.

----------------------------------------

**Arguments**:

  
  ldc : str
  Linguistic Consortium Catalogue Number (eg. 'LDC2015T05'.
  This is what forms the last part of the LDC catalogue URL.
  cert : str
  Path to certificate chain; LDC has had a problem
  with intermediate certificates, so you can
  download the chain with a browser and supply a
  path to the .pem with this parameter

<a id="dataverse_utils.ldc.Ldc.ldcJson"></a>

##### ldcJson

```python
@property
def ldcJson()
```

Returns a JSON based on the LDC web page scraping

<a id="dataverse_utils.ldc.Ldc.dryadJson"></a>

##### dryadJson

```python
@property
def dryadJson()
```

LDC metadata in Dryad JSON format

<a id="dataverse_utils.ldc.Ldc.dvJson"></a>

##### dvJson

```python
@property
def dvJson()
```

LDC metadata in Dataverse JSON format

<a id="dataverse_utils.ldc.Ldc.embargo"></a>

##### embargo

```python
@property
def embargo()
```

Boolean indicating embargo status

<a id="dataverse_utils.ldc.Ldc.fileJson"></a>

##### fileJson

```python
@property
def fileJson()
```

Returns False: No attached files possible at LDC

<a id="dataverse_utils.ldc.Ldc.files"></a>

##### files

```python
@property
def files()
```

Returns None. No files possible

<a id="dataverse_utils.ldc.Ldc.oversize"></a>

##### oversize

```python
@property
def oversize(maxsize=None)
```

Make sure file is not too big for the Dataverse instance

<a id="dataverse_utils.ldc.Ldc.fetch_record"></a>

##### fetch\_record

```python
def fetch_record(timeout=45)
```

Downloads record from LDC website

<a id="dataverse_utils.ldc.Ldc.make_ldc_json"></a>

##### make\_ldc\_json

```python
def make_ldc_json()
```

Returns a dict with keys created from an LDC catalogue web
page.

<a id="dataverse_utils.ldc.Ldc.name_parser"></a>

##### name\_parser

```python
@staticmethod
def name_parser(name)
```

Returns lastName/firstName JSON snippet from name

-----------------/-----------------------

**Arguments**:

  
  name : str
  A name

<a id="dataverse_utils.ldc.Ldc.make_dryad_json"></a>

##### make\_dryad\_json

```python
def make_dryad_json(ldc=None)
```

Creates a Dryad-style dict from an LDC dictionary

----------------------------------------

**Arguments**:

  
  ldc : dict
  Dictionary containing LDC data. Defaults to self.ldcJson

<a id="dataverse_utils.ldc.Ldc.find_block_index"></a>

##### find\_block\_index

```python
@staticmethod
def find_block_index(dvjson, key)
```

Finds the index number of an item in Dataverse's idiotic JSON list

----------------------------------------

**Arguments**:

  
  dvjson : dict
  Dataverse JSON
  
  key : str
  key for which to find list index

<a id="dataverse_utils.ldc.Ldc.make_dv_json"></a>

##### make\_dv\_json

```python
def make_dv_json(ldc=None)
```

Returns complete Dataverse JSON

----------------------------------------

**Arguments**:

  
  ldc : dict
  LDC dictionary. Defaults to self.ldcJson

<a id="dataverse_utils.ldc.Ldc.upload_metadata"></a>

##### upload\_metadata

```python
def upload_metadata(**kwargs) -> dict
```

Uploads metadata to dataverse

Returns json from connection attempt.

----------------------------------------

**Arguments**:

  
  kwargs:
  
  url : str
  base url to Dataverse
  
  key : str
  api key
  
  dv : str
  Dataverse to which it is being uploaded

