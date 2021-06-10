# Dataverse utilities

This is a generalized set of utilities which help with managing [Dataverse](https://dataverse.org) repositories. These utilities are ad-hoc, written as needed and subject to change, so this is not something you should be using in distributed applications, but more for one-off and quick projects.

That being said, the effort is being made to make this a useful library.

## The components

### dataverse_utils

The default feature set from `import dataverse_utils` (or, more easily, `import dataverse_utils as du` is designed to work with data alreadly present locally.

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

### ldc

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

## Scripts

Useful command line scripts will be placed here

## Samples

Sample material goes here. Not a script that's installed, but just for reference.


