# Utility scripts

<style>
code {
  white-space : pre-wrap !important;
}
</style>

These scripts are available at the command line/command prompt and don't require any Python knowledge except how to install a Python library via pip, as outlined in the [overview](index.md) document.

Once installed via pip, the scripts [_should_](#footnote) be available via the command line and will not require calling Python explicitly. That is, they can be called from the command line directly. For example:

`dv_tsv_manifest.py`

is all you will need to type.

Note that these programs have been primarily tested on Linux and MacOS, with [Windows a tertiary priority](#footnote). Windows is notable for its unusual file  handling, so, as the MIT licenses stipulates, there is no warranty as to the suitability for a particular purpose.

Of course, they *should* work.

In no particular order:

## dv_del.py

This is bulk deletion utility for unpublished studies (or even single studies). It's useful when your automated procedures have gone wrong, or if you don't feel like navigating through many menus.

Note the `-i` switch which can ask for manual confirmation of deletions.


**Usage**

```nohighlight
usage: dv_del.py [-h] -k KEY [-d DATAVERSE | -p PID] [-i] [-u DVURL] [--version]

Delete draft studies from a Dataverse collection

optional arguments:
  -h, --help            show this help message and exit
  -k KEY, --key KEY     Dataverse user API key
  -d DATAVERSE, --dataverse DATAVERSE
                        Dataverse collection short name from which to delete all draft records. eg. "ldc"
  -p PID, --persistentId PID
                        Handle or DOI to delete in format hdl:11272.1/FK2/12345
  -i, --interactive     Confirm each study deletion
  -u DVURL, --url DVURL
                        URL to base Dataverse installation
  --version             Show version number and exit
```

##  dv_manifest_gen.py

Not technically a Dataverse-specific script, this utility will generate a tab-separated value output. The file consists of 3 columns: **file, description and tags**, and optionally a **mimetype** column.

Editing the result and using the upload utility to parse the tsv will add descriptive metadata, tags and file paths to an upload instead of laboriously using the Dataverse GUI.

Tags may be separated by commas, eg: "Data, SAS, June 2021".

Using stdout and a redirect will also save time. First dump a file as normal. Add other files to the end with different information using the exclude header switch `-x` and different tags along with output redirection `>>`.

**Usage**

```nohighlight
usage: dv_manifest_gen.py [-h] [-f FILENAME] [-t TAG] [-x] [-r] [-q QUOTE] [-a] [-m] [--version] [files [files ...]]

Creates a file manifest in tab separated value format which can then be edited and used for file uploads to a Dataverse collection. Files can be edited to add file descriptions and
comma-separated tags that will be automatically attached to metadata using products using the dataverse_utils library. Will dump to stdout unless -f or --filename is used. Using the
command and a dash (ie, "dv_manifest_gen.py -" produces full paths for some reason.

positional arguments:
  files                 Files to add to manifest. Leaving it blank will add all files in the current directory. If using -r will recursively show all.

optional arguments:
  -h, --help            show this help message and exit
  -f FILENAME, --filename FILENAME
                        Save to file instead of outputting to stdout
  -t TAG, --tag TAG     Default tag(s). Separate with comma and use quotes if there are spaces. eg. "Data, June 2021". Defaults to "Data"
  -x, --no-header       Don't include header in output. Useful if creating a complex tsv using redirects (ie, ">>").
  -r, --recursive       Recursive listing.
  -q QUOTE, --quote QUOTE
                        Quote type. Cell value quoting parameters. Options: none (no quotes), min (minimal, ie. special characters only )nonum (non-numeric), all (all cells). Default:
                        min
  -a, --show-hidden     Include hidden files.
  -m, --mime            Include autodetected mimetypes
  --version             Show version number and exit
```

## dv_upload_tsv.py

Now that you have a tsv full of nicely described data, you can easily upload it to an existing study if you know the persistent ID and have an API key.

For the best metadata, you should probably edit it manually to add correct descriptive metadata, notably the "Description" and "Tags". Tags are split separated by commas, so it's possible to have multiple tags for each data item, like "Data, SPSS, June 2021".

File paths are automatically generated from the "file" column. Because of this, you should probably use relative paths rather than absolute paths unless you want to have a lengthy path string in Dataverse.

If uploading a tsv which includes mimetypes, be aware that mimetypes for zip files will be ignored to circumvent Dataverse's automatic unzipping feature.

The rationale for manually specifiying mimetypes is to enable the use of previews which require a specific mimetype to function, but Dataverse does not correctly detect the type. For example, the GeoJSON file previewer requires a mimetype of `application/geo+json`, but the detection of this mimetype is not supported until Dataverse v5.9. By manually setting the mimetype, the previewer can be used by earlier Dataverse versions.

**Usage**

```nohighlight
usage: dv_upload_tsv.py [-h] -p PID -k KEY [-u URL] [-r] [-t TRUNCATE] [--version] [tsv]

Uploads data sets to an *existing* Dataverse study from the contents of a TSV (tab separated value) file. Metadata, file tags, paths, etc are all read from the TSV. JSON output from the
Dataverse API is printed to stdout during the process.

positional arguments:
  tsv                   TSV file to upload

optional arguments:
  -h, --help            show this help message and exit
  -p PID, --pid PID     Dataverse study persistent identifier (DOI/handle)
  -k KEY, --key KEY     API key
  -u URL, --url URL     Dataverse installation base url. defaults to "https://abacus.library.ubc.ca"
  -r, --restrict        Restrict files after upload.
  -t TRUNCATE, --truncate TRUNCATE
                        Left truncate file path. As Dataverse studies can retain directory structure, you can set an arbitrary starting point by removing the leftmost portion. Eg: if the
                        TSV has a file path of /home/user/Data/file.txt, setting --truncate to "/home/user" would have file.txt in the Data directory in the Dataverse study. The file is
                        still loaded from the path in the spreadsheet. Defaults to no truncation.
  --version             Show version number and exit
```

## dv_release.py

A bulk release utility for Dataverse. This utility will normally be used after a migration or large data transfer, such as a [dryad2dataverse](https://ubc-library-rc.github.io/dryad2dataverse) transfer from the Dryad data repository. It can release studies individually by persistent ID or just release all unreleased files in a Dataverse.

**Usage**

```nohighlight
usage: dv_release.py [-h] [-u URL] -k KEY [-i] [--time STIME] [-v] [-r] [-d DV | -p PID [PID ...]] [--version]

Bulk file releaser for unpublished Dataverse studies. Either releases individual studies or all unreleased studies in a single Dataverse collection.

optional arguments:
  -h, --help            show this help message and exit
  -u URL, --url URL     Dataverse installation base URL. Default: https://abacus.library.ubc.ca
  -k KEY, --key KEY     API key
  -i, --interactive     Manually confirm each release
  --time STIME, -t STIME
                        Time between release attempts in seconds. Default 10
  -v                    Verbose mode
  -r, --dry-run         Only output a list of studies to be released
  -d DV, --dv DV        Short name of Dataverse collection to process (eg: statcan)
  -p PID [PID ...], --pid PID [PID ...]
                        Handles or DOIs to release in format hdl:11272.1/FK2/12345 or doi:10.80240/FK2/NWRABI. Multiple values OK
  --version             Show version number and exit
```

## dv_ldc_uploader.py

This is a very specialized utility which will scrape metadata from the [Linguistic Data Consortium](https://www.ldc.upenn.edu/) (LDC) and create a metadata record in a Dataverse. The LDC does not have an API, so the metadata is scraped from their web site. This means that the metadata may not be quite as controlled as that which comes from an API. 

Data from the LDC website is converted to [Dryad](https://datadryad.org)-style JSON via `dataverse_utils.ldc` via the use of the [dryad2dataverse](https://ubc-library-rc.github.io/dryad2dataverse) library.

There are two main methods of use for this utility:

1. Multiple metadata uploads. Multiple LDC record numbers can be supplied and a study without files will be created for each one.

2. If a TSV file with file information is upplied via the `-t` or `--tsv` switch, the utility will upload a single LDC study and upload the contents of the tsv file to the created record.

**Usage**

```nohighlight
usage: dv_ldc_uploader.py [-h] [-u URL] -k KEY [-d DVS] [-t TSV] [-n CNAME] [-e EMAIL] [-v] [--version] studies [studies ...]

Linguistic Data Consortium metadata uploader for Dataverse. This utility will scrape the metadata from the LDC website (https://catalog.ldc.upenn.edu) and upload data based on a TSV
manifest. Please note that this utility was built with the Abacus repository (https://abacus.library.ubc.ca) in mind, so many of the defaults are specific to that Dataverse installation.

positional arguments:
  studies               LDC Catalogue numbers to process, separated by spaces. eg. "LDC2012T19 LDC2011T07". Case is ignored, so "ldc2012T19" will also work.

optional arguments:
  -h, --help            show this help message and exit
  -u URL, --url URL     Dataverse installation base URL. Defaults to "https://abacus.library.ubc.ca"
  -k KEY, --key KEY     API key
  -d DVS, --dvs DVS     Short name of target Dataverse collection (eg: ldc). Defaults to "ldc"
  -t TSV, --tsv TSV     Manifest tsv file for uploading and metadata. If not supplied, only metadata will be uploaded. Using this option requires only one positional *studies* argument
  -n CNAME, --cname CNAME
                        Study contact name. Default: "Abacus support"
  -e EMAIL, --email EMAIL
                        Dataverse study contact email address. Default: abacus-support@lists.ubc.ca
  -v, --verbose         Verbose output
  --version             Show version number and exit
```


## dv_pg_facet_date.py 

This specialized tool is designed to be run on the **server** on which the Dataverse installation exists. When material is published in a Dataverse installation, the "Publication Year" facet in the Dataverse GUI is automatically populated with a date, which is the publication date *in that Dataverse installation*. This makes sense from the point of view of research data which is first deposited into a Dataverse installation, but fails as a finding aid for either;

*  older data sets that have been migrated and reingested
*  licensed data sets which may have been published years before they were purchased and ingested.

For example, if you have a dataset that was published in 1971 but you only added it to your Dataverse installation in 2021, it is not necessarily intuitive to the end user that the "publication date" in this instance would be 2021. Ideally, you might like it to be 1971.

Unfortunately, there is no API-based tool to manage this date. The only way to change it, as of late 2021, is to modify the underlying PostgreSQL database directly with the desired date. Subsequently, the study must be reindexed so that the revised publication date appears as an option in the facet.

This tool will perform those operations. However, the tool must be run on the *server* on which the Dataverse installation exists, as reindexing API calls must be from localhost and database access is necessarily restricted.

There are a few other prerequisites for using this tool which differ from the rest of the scripts included in this package. 

* The user must have shell access to the server hosting the Dataverse installation
* Python 3.6 or higher must be installed
* The user must possess a valid Dataverse API key
* The user must know the PostgreSQL password
* If the database name and user have been changed, the user must know this as well
* The script requires the manual installation of `psycopg2-binary` or have a successfully compiled `psycopg2` package for Python. See <https://www.psycopg.org/docs/>. This **is not installed** with the normal `pip install` of the *dataverse_utils* package as none of the other scripts require it and, in general, the odds of someone using this utility are low. If you forget to install it, the program will politely remind you.

This cannot be stressed enough. **This tool will directly change values within the PostgreSQL database which holds all of Dataverse's information**. Use this at your own risk; no warranty is implied and no responsibility will be accepted for data loss, etc. If any of the items listed make no sense to you or sound like gibberish, do not use this tool.

Because editing the underlying database may have a high pucker factor for some, there is both a dry-run option and an option to just dump out SQL instead of actually touching anything. These two options do not perform a study reindex and don't alter the contents of the database.

**Usage**

```nohighlight
usage: dv_pg_facet_date.py [-h] [-d DBNAME] [-u USER] -p PASSWORD [-r | -o] [-s] -k KEY [-w URL] [--version] pids [pids ...] {distributionDate,productionDate,dateOfDeposit,dist,prod,dep}

A utility to change the 'Production Date' web interface facet in a Dataverse installation to one of the three acceptable date types: 'distributionDate', 'productionDate', or
'dateOfDeposit'. This must be done in the PostgreSQL database directly, so this utility must be run on the *server* that hosts a Dataverse installation. Back up your database if you are
unsure.

positional arguments:
  pids                  persistentIdentifier
  {distributionDate,productionDate,dateOfDeposit,dist,prod,dep}
                        date type which is to be shown in the facet. The short forms are aliases for the long forms.

optional arguments:
  -h, --help            show this help message and exit
  -d DBNAME, --dbname DBNAME
                        Database name
  -u USER, --user USER  PostgreSQL username
  -p PASSWORD, --password PASSWORD
                        PostgreSQL password
  -r, --dry-run         print proposed SQL to stdout
  -o, --sql-only        dump sql to file called *pg_sql.sql* in current directory. Appends to file if it exists
  -s, --save-old        Dump old values to tsv called *pg_changed.tsv* in current directory. Appends to file if it exists
  -k KEY, --key KEY     API key for Dataverse installation.
  -w URL, --url URL     URL for base Dataverse installation. Default https://abacus.library.ubc.ca
  --version             Show version number and exit

THIS WILL EDIT YOUR POSTGRESQL DATABASE DIRECTLY. USE AT YOUR OWN RISK.
```

<a name='footnote' />
## Notes for Windows users

Command line scripts for Python may not necessarily behave the way they do in Linux/Mac, depending on *how* you access them. For detailed information on Windows systems, please see the [Windows testing document](windows.md)


