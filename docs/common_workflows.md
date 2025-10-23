# Common workflows

Given the pile of various utilities, what are they _for?_ Here are some very common use cases.

## Studies with many files

While it's possible to add multiple files at once to a Dataverse record by uploading a zip file, there is no metadata included in a zip file, which means laboriously adding file descriptions after the fact using the Dataverse GUI.

Imagine that you have a study with a complex file tree and a large number of files. For example:

```nohighlight
.
├── Command Files
│   ├── bootstrap
│   │   ├── sas
│   │   │   └── bsw_i.sas
│   │   └── spss
│   │       └── bsw_i.sps
│   ├── sas
│   │   └── CCHS_2022_SAS_sas.zip
│   ├── spss
│   │   └── CCHS_2022_SPSS_sps.zip
│   └── stata
│       └── CCHS_2022_Stata_do.zip
├── Data
│   ├── ascii
│   │   ├── CCHS_2022_ASCII_csv.zip
│   │   ├── CCHS_2022_ASCII_txt.zip
│   │   ├── pumf_cchs.csv
│   │   └── PUMF_MASTER_CCHS.txt
│   ├── bootstrap
│   │   ├── ascii
│   │   │   ├── bsw.txt
│   │   │   ├── CCHS_2022_BSW_ASCII_csv.zip
│   │   │   └── CCHS_2022_BSW_ASCII_txt.zip
│   │   ├── sas
│   │   │   ├── bsw.sas7bdat
│   │   │   └── CCHS_2022_BSW_SAS_sas7bdat.zip
│   │   ├── spss
│   │   │   ├── bsw.sav
│   │   │   └── CCHS_2022_BSW_SPSS_sav.zip
│   │   └── stata
│   │       ├── bsw.dta
│   │       └── CCHS_2022_BSW_Stata_dta.zip
│   ├── sas
│   │   └── CCHS_2022_SAS_sas7bdat.zip
│   ├── spss
│   │   ├── cchs_2022_pumf_v1.sav
│   │   └── CCHS_2022_SPSS_sav.zip
│   └── stata
│       └── CCHS_2022_Stata_dta.zip
└── Documentation
    ├── CCHS 2022 PUMF Complement User Guide.pdf
    ├── CCHS_2022_CV_Tables_PUMF.pdf
    ├── CCHS_2022_DataDictionary_Freqs.pdf
    ├── CCHS_2022_Income_Master File.pdf
    ├── CCHS_2022_PUMF_Grouped_Variables.pdf
    └── CCHS_2022_User_Guide.pdf
```

The procedure for this would be as follows:

* Create a study record manually
* Using `dv_manifest_gen`, create a file manifest. If the tree exists (ie, the files are arranged as shown above), use `dv_manifest_gen -r * [plus any other options]` to create a tsv manifest. If the tree does not yet exist, use the `-p` switch to add the field which allows virtual paths
* Edit the resultant tsv with file metadata. For example, the first three lines could be something like:
```
file	description	tags
Command Files/bootstrap/sas/bsw_i.sas	SAS program for bootstrap weights file	Command Files, SAS, Bootstrap weights
Command Files/bootstrap/spss/bsw_i.sps	SPSS syntax for bootstrap weights file	Command Files, SPSS, Bootstrap weights
```
* Once the file metadata is complete, upload the whole works in one shot:
`dv_upload_tsv -u [url] -k [your API key] -p [your study id] [your manifest tsv file]`

Once it's uploaded, verify it's correct and you've saved a great deal of time.

Your definition of "many" may vary, but generally "many" is >=1.

## Using Linguistic Data Consortium metadata

If your instituion uses a Dataverse installation to host Linguistic Data Consortium materials, you can automate record creation.

* Create a file manifest as outlined above for your LDC data.
* Use `dv_ldc_uploader -u [dataverse_url] -k [API key] -t [your file manifest] -d [collection name] [LDC Study number]` and your record will be created and the files uploaded and restricted. The only thing left to do is to review the record and hit the **publish** button.

## Creating README templates for institutional users

Researcher documentation is notoriously incomplete, often neglecting important information such as rights information or basic data dictionaries. Even if the fields are required to _create_ a record, they can still be missing from researcher-supplied documentation. Data dictionaries, message digests, etc are also often missing.

The README creator will harvest this information, much of which is required to create a record in the first place, and concatenate it into a nicely structured text (or PDF) document. 

This can be forwarded to the researcher for editing and uploading along with a data set.

This is commonly done by the administrator of a collection, as they have access to the study contents and metadata.

To do this:

`dv_readme_creator -u [Dataverse url] -p [persistent ID] --k [API key] README.md`

Attach the resultant `README.md` file to an email along with suggestions for improvement.

## Collection analysis

While Dataverse installations have a reasonably robust set of metrics available, detailed collection analysis may be required for any number of reasons. Collection recursion is not supported in the API, but is required for institutions analyzing their collections.

A spreadsheet of a collection with selected metadata fields can be made easily with `dv_collection_info`

For example, you wish to recursively analyze your collection called `foo`, and you need the authors, titles, keywords and distribution date.

`dv_collection_info -u [Dataverse instance] -k [key, may or may not be required] -c foo -f authorName title keywordValue distributionDate -o [wherever your file is .tsv]`

Field names are those defined in the Dataverse JSON specification. Fields can be added by custom metadata blocks, but a sample can be found on the IQSS github page [here](https://github.com/IQSS/dataverse/blob/19e67ef9e7e6a373d2551629fe19bb63a9ac7d18/scripts/api/data/dataset-create-new-all-default-fields.json#L633) [2025-10-23], where the field names are found using the 'typeName' key.

## Recurring series

Some records are broadly similar, requiring only minor changes, such as a year change, etc. Instead of copy/paste:

`dv_record_copy -u [Dataverse installation] -k [key] -c [collection where it should live] doi:xxx/xxx`

Your record is instantly copied and requires minor edits instead of a full manual entry.

### Helper utilities

All of these things take place in a command line environment. To avoid having to leave it to use a spreadsheet application, consider using [Visidata](https://www.visidata.org/) instead of a spreadsheet so that you can rapidly edit any tabular data. *Dataverse_utils* has no affiliation with _Visidata_ beyond recommending it as a useful tool. 

