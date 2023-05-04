# Dataverse utilities

This is a generalized set of utilities which help with managing [Dataverse](https://dataverse.org) repositories. This has *nothing* to do with the Microsoft product of the same name. Despite being written as they were required, that doesn't mean they're not useful or user-friendly. 

With these utilities you can:

* Upload your data sets from a tab-separated-value spreadsheet
* Bulk release multiple data sets
* Bulk delete (unpublished) assets
* Quickly duplicate records
* Replace licences
* and more!

**Get your copy today!**

Source code (and this documentation) is available at the Github repository <https://github.com/ubc-library-rc/dataverse_utils>, and the user-friendly version of the documentation is at <https://ubc-library-rc.github.io/dataverse_utils>. Presumably you know this already otherwise you wouldn't be reading this.

## Installation

Any installation will require the use of the command line/command prompt.

The easiest installation is with `pip`:

```nohighlight
pip install dataverse_utils
```

There is also a *server specific version* if you need to use the **dv_facet_date** utility. This can *only* be run on a server hosting a Dataverse instance, so for the vast majority of users it will be unusable.

This can also be installed with `pip`:

```nohighlight
pip install 'dataverse_utils[server]'
```

Note the extra quotes. You can install the server version if you want to, but it's useless without server access.

### Upgrading

Just as easy as installation:

```nohighlight
pip install --upgrade dataverse_utils
```

Other methods of installing Python packages can be found at <https://packaging.python.org/tutorials/installing-packages/>.

### Downloading the source code

Source code is available at <https://github.com/ubc-library-rc/dataverse_utils>. Working on the assumption that `git` is installed, you can download the whole works with:

`git clone https://github.com/ubc-library-rc/dataverse_utils`

If you have [mkdocs](https://www.mkdocs.org) installed, you can view the documentation in a web browser by running mkdocs from the top level directory of the *downloaded source files* by running `mkdocs serve`.

## The components

### Console utilities 

There are eight (8) console utilities currently available.

* **dv_del.py**: Bulk (unpublished) file deletion utility

* **dv_ldc_uploader.py**: A utility which scrapes Linguistic Data Consortium metadata from their website, converts it to Dataverse JSON and uploads it, with the possibility of including local files. **As of early 2023, there is an issue which requires attaching a manually downloaded certificate chain**. Don't worry, that's not as hard as it sounds.

* **dv_manifest_gen.py**: Creates a simple tab-separated value format file which can be edited and then used to upload files as well as file-level metadata. Normally files will be edited after creation, usually in a spreadsheet like Excel.

* **dv_pg_facet_date.py**: A server-based tool which updates the publication date facet and performs a study reindex.

* **dv_record_copy.py**: Copies an existing Dataverse study metadata record to a target collection, or replace a currently existing record.

* **dv_release.py**: A bulk release utility. Either releases all the unreleased studies in a Dataverse or individually if persistent identifiers are available.

* **dv_replace_licences**: Replaces the licence associated with a PID with text from a Markdown file. Also available as **dv_replace_licenses** for those using American English.

* **dv_upload_tsv.py**: Takes a tsv file in the format from *dv_manifest_gen.py* and does all the uploading and metadata entry.


More information about these can be found on the [console utilities page](scripts.md).

### Python package: dataverse_utils

This package contains a variety of utility functions which, for the most part, allow uploads of files and associated metadata without having to touch the Dataverse GUI or to have complex JSON attached.

For example, the `upload_file` requires no JSON attachments:

```
dataverse_utils.upload_file('/path/to/file.ext',
                            dv='https://targetdataverse.invalid'
                            descr='A file description',
                            tags=['Data', 'Example', 'Spam'],
                            dirlabel=['path/to/spam'],
                            mimetype='application/geo+json') 
```

Consult the [API reference](api_ref.md) for full details.

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
