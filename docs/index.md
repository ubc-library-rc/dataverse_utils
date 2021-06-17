# Dataverse utilities

This is a generalized set of utilities which help with managing [Dataverse](https://dataverse.org) repositories. These utilities are _ad-hoc_, written as needed and subject to change.

That being said, the effort is being made to make this a useful library. Source code (and this documentation) is available at the Github repository <https://github.com/ubc-library-rc/dataverse_utils>, and the user-friendly version of the documentation is at <https://ubc-library-rc.github.io/dataverse_utils>.

## Installation

Any installation will require the use of the command line/command prompt.

The easiest installation is with `pip`:

```
pip install git+https://github.com/ubc-library-rc/dataverse_utils
```

Other methods of installing Python packages can be found at <https://packaging.python.org/tutorials/installing-packages/>.

If you have [mkdocs](https://www.mkdocs.org) installed, you can view the documentation in a web browser by running mkdocs from the top level directory of the library by running `mkdocs serve`.

## The components

### Scripts

There are five (5) scripts currently available.

* **dv_del.py**: Bulk (unpublished) file deletion utility

* **dv_ldc_uploader.py**: A utility which scrapes Linguistic Data Consortium metadata from their website, converts it to Dataverse JSON and uploads it, with the possibility of including local files.

* **dv_manifest_gen.py**: Creates a simple tab-separated value format file which can be edited and then used to upload files as well as file-level metadata. Normally files will be edited after creation.

* **dv_release.py**: A bulk release utility. Either releases all the unreleased studies in a Dataverse or individually if persistent identifiers are available.

* **dv_upload_tsv.py**: Takes a tsv file in the format from *dv_manifest_gen.py* and does all the uploading and metadata entry.

More information about these can be found on the [scripts page](scripts.md).

### Python library: dataverse_utils

The default feature set from `import dataverse_utils` (or, more easily, `import dataverse_utils as du` is designed to work with data already present locally.

The idea of this portion is to create a tsv file manifest for files which are to be uploaded to a Dataverse instance. Once the manifest is created, it's edited to add descriptive metadata, file paths and tags. Then, the manifest is used to upload those files to a an existing Dataverse study.

```
import dataverse_utils as du
du.dump_tsv('.', '/Users/you/tmp/testme.tsv')
[Edit the .tsv at this stage here]
du.upload_from_tsv(fil='/Users/you/tmp/testme.tsv',
                   hdl='hdl:PERSIST/ID',
		   dv='https://dataverse.invalid'
		   apikey='IAM-YOUR-DVERSE-APIKEY')
```

The tsv should be edited to have a description. Tags should be separated by commas in the "Tags" column.

If you are using relative paths, make sure that the script you are using is reading from the correct location.

#### ldc

The `ldc` component represents the [Linguistic Data Consortium](https://catalog.ldc.upenn.edu/) or LDC. The ldc module is designed to harvest LDC metadata from its catalogue, convert it to Dataverse JSON, then upload it to a Dataverse installation. Once the study has been created, the general `dataverse_utils` module can handle the file uploading.

The `ldc` module requires the [dryad2dataverse](https://github.com/ubc-library-rc/dryad2dataverse) package.

Because of this, it requires a tiny bit more effort, because LDC material doesn't have the required metadata. Here's snippet that shows how it works.

```
import dataverse_utils.ldc as ldc

ldc.ds.constants.DV_CONTACT_EMAIL='iamcontact@test.invalid'
ldc.ds.constants.DV_CONTACT_NAME='Generic Support Email'
KEY = 'IAM-YOUR-DVERSE-APIKEY'

stud = 'LDC2021T02' #LDC study number

a = ldc.Ldc(stud)
a.fetch_record()
#Data goes into the 'ldc' dataverse
info = a.upload_metadata(url='https://dataverse.invalid', 
		  				 key=KEY, 
		  				 dv='ldc')
hdl =  info['data']['persistentId'] 

with open('/Users/you/tmp/testme.tsv') as fil:
	du.upload_from_tsv(fil, hdl=hdl,dv='https://dataverse.invalid', 
                       apikey=KEY)
```
Note that one method uses `key` and the other `apikey`. This is what is known as _ad hoc_. 

More information is available at the [API reference](api_ref.md).

### Samples

The `sample` directory contains Python scripts which demonstrate the usage of the _dataverse_utils_ library. They're not necessarily complete examples or optimized. Or even present, intially. You know,  _ad_hoc_.


