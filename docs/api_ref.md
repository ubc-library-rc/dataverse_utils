# API Reference

<a name="dataverse_utils"></a>
## dataverse\_utils

Generalized dataverse utilities

<a name="dataverse_utils.dataverse_utils"></a>
## dataverse\_utils.dataverse\_utils

A collection of Dataverse utilities for file and metadata
manipulation

<a name="dataverse_utils.dataverse_utils.DvGeneralUploadError"></a>
### DvGeneralUploadError Objects

```python
class DvGeneralUploadError(Exception)
```

Raised on non-200 URL response

<a name="dataverse_utils.dataverse_utils.Md5Error"></a>
### Md5Error Objects

```python
class Md5Error(Exception)
```

Raised on md5 mismatch

<a name="dataverse_utils.dataverse_utils.make_tsv"></a>
##### make\_tsv

```python
make_tsv(start_dir, in_list=None, def_tag='Data', inc_header=True)
```

Recurses the tree for files and produces tsv output with
with headers 'file', 'description', 'tags'.

The 'description' is the filename without an extension.

Returns tsv as string

------------------------------------------

**Arguments**:

  
  start_dir : str
  Path to start directory
  
  in_list : list
  Input file list. Defaults to recursive walk of current directory.
  
  def_tag : str
  Default Dataverse tag (eg, Data, Documentation, etc)
  Separate tags with an easily splitable character:
  eg. ('Data, 2016')
  
  inc_header : bool
  Include header row

<a name="dataverse_utils.dataverse_utils.dump_tsv"></a>
##### dump\_tsv

```python
dump_tsv(start_dir, filename, in_list=None, def_tag='Data', inc_header=True)
```

Dumps output of make_tsv manifest to a file.

------------------------------------------

**Arguments**:

  
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

<a name="dataverse_utils.dataverse_utils.file_path"></a>
##### file\_path

```python
file_path(fpath, trunc)
```

Create relative file path from full path string

>>> file_path('/tmp/Data/2011/excelfile.xlsx', '/tmp/')
'Data/2011'
>>> file_path('/tmp/Data/2011/excelfile.xlsx', '/tmp')
'Data/2011'

----------------------------------------

**Arguments**:

  
  fpath : str
  file location (ie, complete path)
  
  trunc : str
  rightmost portion of path to remove

<a name="dataverse_utils.dataverse_utils.check_lock"></a>
##### check\_lock

```python
check_lock(dv_url, study, apikey) -> bool
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

<a name="dataverse_utils.dataverse_utils.force_notab_unlock"></a>
##### force\_notab\_unlock

```python
force_notab_unlock(study, dv_url, fid, apikey, try_uningest=True) -> int
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

<a name="dataverse_utils.dataverse_utils.uningest_file"></a>
##### uningest\_file

```python
uningest_file(dv_url, fid, apikey, study='n/a')
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

<a name="dataverse_utils.dataverse_utils.upload_file"></a>
##### upload\_file

```python
upload_file(fpath, hdl, **kwargs)
```

Uploads file to Dataverse study and sets file metdata and tags.

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

<a name="dataverse_utils.dataverse_utils.upload_from_tsv"></a>
##### upload\_from\_tsv

```python
upload_from_tsv(fil, hdl, **kwargs)
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
  
  kwargs : dict
  
  other parameters. Acceptable keywords and contents are:
  
  dv : str
  REQUIRED
  url to base Dataverse installation
- `eg` - 'https://abacus.library.ubc.ca'
  
  apikey : str
  REQUIRED
  API key for user

<a name="dataverse_utils.ldc"></a>
## dataverse\_utils.ldc

Creates dataverse JSON from Linguistic Data Consortium
website page.

<a name="dataverse_utils.ldc.Ldc"></a>
### Ldc Objects

```python
class Ldc(ds.Serializer)
```

An LDC item (eg, LDC2021T01)

<a name="dataverse_utils.ldc.Ldc.ldcJson"></a>
##### ldcJson

```python
 | @property
 | ldcJson()
```

Returns a JSON based on the LDC web page scraping

<a name="dataverse_utils.ldc.Ldc.make_ldc_json"></a>
##### make\_ldc\_json

```python
 | make_ldc_json()
```

Returns a dict with keys created from an LDC catalogue web
page.

intext : str
    HTML page source from LDC catalogue page.

<a name="dataverse_utils.ldc.Ldc.name_parser"></a>
##### name\_parser

```python
 | @staticmethod
 | name_parser(name)
```

name : str
    A name

<a name="dataverse_utils.ldc.Ldc.make_dryad_json"></a>
##### make\_dryad\_json

```python
 | make_dryad_json(ldc=None)
```

Creates a Dryad-style dict from an LDC dictionary

ldc : dict
    Dictionary containing LDC data

<a name="dataverse_utils.ldc.Ldc.find_block_index"></a>
##### find\_block\_index

```python
 | @staticmethod
 | find_block_index(dvjson, key)
```

Finds the index number of an item in Dataverse's idiotic JSON

<a name="dataverse_utils.ldc.Ldc.make_dv_json"></a>
##### make\_dv\_json

```python
 | make_dv_json(ldc=None)
```

ldc : dict
    LDC dictionary. Defaults to self.ldcJson

<a name="dataverse_utils.ldc.Ldc.upload_metadata"></a>
##### upload\_metadata

```python
 | upload_metadata(**kwargs) -> dict
```

uploads metadata to dataverse
kwargs:
url : base url to Dataverse
key : api key
dv : dataverse to which it is being uploaded

Returns json from connection attempt.
