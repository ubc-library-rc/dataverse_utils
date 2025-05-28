# Console utilities 

<style>
code {
  white-space : pre-wrap !important;
}
</style>

These utilities are available at the command line/command prompt and don't require any Python knowledge except how to install a Python library via pip, as outlined in the [overview](index.md) document.

Once installed via pip, the scripts [will](#footnote) be available via the command line and will not require calling Python explicitly. That is, they can be called from the command line directly. For example:

`dv_tsv_manifest`

is all you will need to type.

Note that these programs have been primarily tested on Linux and MacOS, with [Windows a tertiary priority](#footnote). Windows is notable for its unusual file  handling, so, as the MIT licence stipulates, there is no warranty as to the suitability for a particular purpose.


In alphabetical order:

## dv_collection_info

A recursive file metadata utility. You can specify the head of a tree and the harvester will harvest the \[latest\]  study metadata and output it as a spreadsheet. An API key is not required for publicly accessible data.

```nohighlight
usage: dv_collection_info [-h] [-u URL] -c COLLECTION [-k KEY] [-d DELIMITER] [-f [FIELDS ...]] [-o OUTPUT] [--verbose] [-v]

Recursively parses a dataverse collection and
outputs study metadata for the latest version.

If analyzing publicly available collections, a
dataverse API key for the target system is not
required.

options:
  -h, --help            show this help message and exit
  -u, --url URL         Dataverse installation base url. defaults to "https://abacus.library.ubc.ca"
  -c, --collection COLLECTION
                        Dataverse collection shortname or id at the top of the tree
  -k, --key KEY         API key
  -d, --delimiter DELIMITER
                        Delimiter for output spreadsheet. Default: tab (\t)
  -f, --fields [FIELDS ...]
                        Record metadata fields to output. For all fields, use "all". Default: title, author.
  -o, --output OUTPUT   Output file name.
  --verbose             Verbose output. See what's happening.
  -v, --version         Show version number and exit
```
## dv_del

This is bulk deletion utility for unpublished studies (or even single studies). It's useful when your automated procedures have gone wrong, or if you don't feel like navigating through many menus.

Note the `-i` switch which can ask for manual confirmation of deletions.

**Usage**

```nohighlight
usage: dv_del [-h] -k KEY [-d DATAVERSE | -p PID] [-i] [-u DVURL] [--version]

Delete draft studies from a Dataverse collection

options:
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

## dv_ldc_uploader

This is a very specialized utility which will scrape metadata from the [Linguistic Data Consortium](https://www.ldc.upenn.edu/) (LDC) and create a metadata record in a Dataverse. The LDC does not have an API, so the metadata is scraped from their web site. This means that the metadata may not be quite as controlled as that which comes from an API. 

Data from the LDC website is converted to [Dryad](https://datadryad.org)-style JSON via `dataverse_utils.ldc` via the use of the [dryad2dataverse](https://ubc-library-rc.github.io/dryad2dataverse) library.

There are two main methods of use for this utility:

1. Multiple metadata uploads. Multiple LDC record numbers can be supplied and a study without files will be created for each one.

2. If a TSV file with file information is upplied via the `-t` or `--tsv` switch, the utility will upload a single LDC study and upload the contents of the tsv file to the created record.

### Important note

**2024-09 Update**

The problem listed below seems to have resolved itself by September 2024. It's not clear whether this was a `certifi` issue or an issue with LDC's certificates. In any case, if you are having problems with LDC website, use the `-c` switch and follow the procedure below.

---

As of early 2023, the LDC website is not supported by `certifi`. You will need to manually supply a certificate chain to use the utility.

To obtain the certificate chain (in Firefox) perform the following steps:

1. Select Tools/Page Info
2. In the Security tab, select View Certificate
3. Scroll to "PEM (chain)"
4. Right click and "Save link as"

Use this file for the -c/--certchain option below.

Searching for "download pem certificate chain [browser]" in a search engine will undoubtedly bring up results for whatever browser you like.

**Usage**

```nohighlight
usage: dv_ldc_uploader [-h] [-u URL] -k KEY [-d DVS] [-t TSV] [-r] [-n CNAME] [-c CERTCHAIN] [-e EMAIL] [-v] [--version] studies [studies ...]

Linguistic Data Consortium metadata uploader for Dataverse. This utility will scrape the metadata from the LDC website (https://catalog.ldc.upenn.edu) and upload data based on a TSV
manifest. Please note that this utility was built with the Abacus repository (https://abacus.library.ubc.ca) in mind, so many of the defaults are specific to that Dataverse installation.

positional arguments:
  studies               LDC Catalogue numbers to process, separated by spaces. eg. "LDC2012T19 LDC2011T07". Case is ignored, so "ldc2012T19" will also work.

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     Dataverse installation base URL. Defaults to "https://abacus.library.ubc.ca"
  -k KEY, --key KEY     API key
  -d DVS, --dvs DVS     Short name of target Dataverse collection (eg: ldc). Defaults to "ldc"
  -t TSV, --tsv TSV     Manifest tsv file for uploading and metadata. If not supplied, only metadata will be uploaded. Using this option requires only one positional *studies* argument
  -r, --no-restrict     Don't restrict files after upload.
  -n CNAME, --cname CNAME
                        Study contact name. Default: "Abacus support"
  -c CERTCHAIN, --certchain CERTCHAIN
                        Certificate chain PEM: use if SSL issues are present. The PEM chain must be downloaded with a browser. Default: None
  -e EMAIL, --email EMAIL
                        Dataverse study contact email address. Default: abacus-support@lists.ubc.ca
  -v, --verbose         Verbose output
  --version             Show version number and exit
```

## dv_list_files

This utility will produce a csv, tsv or JSON output showing the

* path/name of a file
* description
* the file download page URL
* the API URL to download the file
* the version of the file (ie, the study version)
* the state of the version.

Unless specified, the most current version is shown. If an API key is supplied and a draft version exists, then the most current version is considered the draft version.

```nohighlight

usage: dv_list_files [-h] [-u URL] [-o {csv,tsv,json}] [-a] [-k KEY] [-f FILE] [-v] pid

This will parse a Dataverse record and show the path, filename, descriptions
and download information for a Dataverse record. An API key is required
for DRAFT versions.

positional arguments:
  pid                   Dataverse study persistent identifier (DOI/handle)

options:
  -h, --help            show this help message and exit
  -u, --url URL         Dataverse installation base url. Defaults to "https://abacus.library.ubc.ca"
  -o, --output {csv,tsv,json}
                        Output format. One of  csv, tsv, or json. Default tsv because descriptions often contain commas
  -a, --all             Show info for *all* versions, not just most current
  -k, --key KEY         API key; required for restricted or draft data sets
  -f, --file FILE       Dump output to FILE
  -v, --version         Show version number and exit
```

##  dv_manifest_gen

Not technically a Dataverse-specific script, this utility will generate a tab-separated value output. The file consists of 3 columns: **file, description and tags**, and optionally a **mimetype** column.

Editing the result and using the upload utility to parse the tsv will add descriptive metadata, tags and file paths to an upload instead of laboriously using the Dataverse GUI.

Tags may be separated by commas, eg: "Data, SAS, June 2021".

Using stdout and a redirect will also save time. First dump a file as normal. Add other files to the end with different information using the exclude header switch `-x` and different tags along with output redirection `>>`.

**Usage**

```nohighlight
usage: dv_manifest_gen [-h] [-f FILENAME] [-t TAG] [-x] [-r] [-q QUOTE] [-a] [-m] [-p] [--version] [files ...]

Creates a file manifest in tab separated value format which can then be edited and used for file uploads to a Dataverse collection. Files can be edited to add file descriptions and
comma-separated tags that will be automatically attached to metadata using products using the dataverse_utils library. Will dump to stdout unless -f or --filename is used. Using the
command and a dash (ie, "dv_manifest_gen.py -" produces full paths for some reason.

positional arguments:
  files                 Files to add to manifest. Leaving it blank will add all files in the current directory. If using -r will recursively show all.

options:
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
  -p, --path            Include an optional path column for custom file paths
  --version             Show version number and exit
```

## dv_pg_facet_date 

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

This cannot be stressed enough. **This tool will directly change values within the PostgreSQL database which holds all of Dataverse's information**. Use this at your own risk; no warranty is implied and no responsibility will be accepted for data loss, etc. If any of the options listed for the utility make no sense to you or sound like gibberish, do not use this tool.

Because editing the underlying database may have a high pucker factor for some, there is both a dry-run option and an option to just dump out SQL instead of actually touching anything. These two options do not perform a study reindex and don't alter the contents of the database.

**Usage**

```nohighlight
usage: dv_pg_facet_date [-h] [-d DBNAME] [-u USER] -p PASSWORD [-r | -o] [-s] -k KEY [-w URL] [--version] pids [pids ...] {distributionDate,productionDate,dateOfDeposit,dist,prod,dep}

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

## dv_record_copy

Copies an existing Dataverse study metadata record to a target collection, or replaces a currently existing record. Files are not copied, only the study record. This utility is useful for mateial which is in a series, requiring only minor changes for each iteration.

**Usage**

```nohighlight
usage: dv_record_copy [-h] [-u URL] -k KEY (-c COLLECTION | -r REPLACE) [-v] pid

Record duplicator for Dataverse. This utility will download a Dataverse record And then upload the study level metadata into a new record in a user-specified collection. Please note that
this utility was built with the Abacus repository (https://abacus.library.ubc.ca) in mind, so many of the defaults are specific to that Dataverse installation.

positional arguments:
  pid                   PID of original dataverse recordseparated by spaces. eg. "hdl:11272.1/AB2/NOMATH hdl:11272.1/AB2/HANDLE". Case is ignored, so "hdl:11272.1/ab2/handle" will also
                        work.

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     Dataverse installation base URL. Defaults to "https://abacus.library.ubc.ca"
  -k KEY, --key KEY     API key
  -c COLLECTION, --collection COLLECTION
                        Short name of target Dataverse collection (eg: ldc). Defaults to "statcan-public"
  -r REPLACE, --replace REPLACE
                        Replace metadata data in record with this PID
  -v, --version         Show version number and exit
```

## dv_release

A bulk release utility for Dataverse. This utility will normally be used after a migration or large data transfer, such as a [dryad2dataverse](https://ubc-library-rc.github.io/dryad2dataverse) transfer from the Dryad data repository. It can release studies individually by persistent ID or just release all unreleased files in a Dataverse.

**Usage**

```nohighlight
usage: dv_release [-h] [-u URL] -k KEY [-i] [--time STIME] [-v] [-r] [-d DV | -p PID [PID ...]] [--version]

Bulk file releaser for unpublished Dataverse studies. Either releases individual studies or all unreleased studies in a single Dataverse collection.

options:
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

##dv_replace_licen[cs]e

This will replace the text in a record with the text Markdown file. Text is converted to HTML. Optionally, the record can be republished without incrementing the version (ie, with `type=updatecurrent`.

**Deprecation warning**

`dv_replace_license` will be removed in future releases to conform to Canadian English standards.

```nohighlight
usage: dv_replace_licence [-h] [-u URL] -l LIC -k KEY [-r] [--version] studies [studies ...]

Replaces the licence text in a Dataverse study and [optionally] republishes it as the same version. Superuser privileges are required for republishing as the version is not incremented.
This software requires the Dataverse installation to be running Dataverse software version >= 5.6.

positional arguments:
  studies               Persistent IDs of studies

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     Base URL of Dataverse installation. Defaults to "https://abacus.library.ubc.ca"
  -l LIC, --licence LIC
                        Licence file in Markdown format
  -k KEY, --key KEY     Dataverse API key
  -r, --republish       Republish study without incrementing version
  --version             Show version number and exit
``` 
## dv_study_migrator

If for some reason you need to copy everything from a Dataverse record to a different Dataverse installation or a different collection, this utility will do it for you. Metadata, file names, paths, restrictions etc will all be copied. There are some limitations, though, as only the most recent version will be copied and date handling is done on the target server. The utility will either copy records specifice with a persistent identifer (PID) to a target collection on the same or another server, or replace records with an existing PID.

```nohighlight
usage: dv_study_migrator [-h] -s SOURCE_URL -a SOURCE_KEY -t TARGET_URL -b TARGET_KEY [-o TIMEOUT] (-c COLLECTION | -r REPLACE [REPLACE ...]) [-v] pids [pids ...]

Record migrator for Dataverse.

This utility will take the most recent version of a study
from one Dataverse installation and copy the metadata
and records to another, completely separate dataverse installation.

You could also use it to copy records from one collection to another.

positional arguments:
  pids                  PID(s) of original Dataverse record(s) in source Dataverse
                        separated by spaces. eg. "hdl:11272.1/AB2/JEG5RH
                        doi:11272.1/AB2/JEG5RH".
                        Case is ignored.

options:
  -h, --help            show this help message and exit
  -s SOURCE_URL, --source_url SOURCE_URL
                        Source Dataverse installation base URL.
  -a SOURCE_KEY, --source_key SOURCE_KEY
                        API key for source Dataverse installation.
  -t TARGET_URL, --target_url TARGET_URL
                        Source Dataverse installation base URL.
  -b TARGET_KEY, --target_key TARGET_KEY
                        API key for target Dataverse installation.
  -o TIMEOUT, --timeout TIMEOUT
                        Request timeout in seconds. Default 100.
  -c COLLECTION, --collection COLLECTION
                        Short name of target Dataverse collection (eg: dli).
  -r REPLACE [REPLACE ...], --replace REPLACE [REPLACE ...]
                        Replace data in these target PIDs with data from the
                        source PIDS. Number of PIDs listed here must match
                        the number of PID arguments to follow. That is, the number
                        of records must be equal. Records will be matched on a
                        1-1 basis in order. For example:
                        [rest of command] -r doi:123.34/etc hdl:12323/AB/SOMETHI
                        will replace the record with identifier 'doi' with the data from 'hdl'.
                        
                        Make sure you don't use this as the penultimate switch, because 
                        then it's not possible to disambiguate PIDS from this argument
                        and positional arguments.
                        ie, something like dv_study_migrator -r blah blah -s http//test.invalid etc.
  -v, --version         Show version number and exit
```


## dv_upload_tsv

Now that you have a tsv full of nicely described data, you can easily upload it to an existing study if you know the persistent ID and have an API key.

For the best metadata, you should probably edit it manually to add correct descriptive metadata, notably the "Description" and "Tags". Tags are split separated by commas, so it's possible to have multiple tags for each data item, like "Data, SPSS, June 2021".

File paths are automatically generated from the "file" column. Because of this, you should probably use relative paths rather than absolute paths unless you want to have a lengthy path string in Dataverse.

If uploading a tsv which includes mimetypes, be aware that mimetypes for zip files will be ignored to circumvent Dataverse's automatic unzipping feature.

The rationale for manually specifiying mimetypes is to enable the use of previews which require a specific mimetype to function, but Dataverse does not correctly detect the type. For example, the GeoJSON file previewer requires a mimetype of `application/geo+json`, but the detection of this mimetype is not supported until Dataverse v5.9. By manually setting the mimetype, the previewer can be used by earlier Dataverse versions.

**Usage**

```nohighlight
usage: dv_upload_tsv [-h] -p PID -k KEY [-u URL] [-r] [-n] [-t TRUNCATE] [-o] [-v] tsv

Uploads data sets to an *existing* Dataverse study
from the contents of a TSV (tab separated value)
file. Metadata, file tags, paths, etc are all read
from the TSV.

JSON output from the Dataverse API is printed to stdout during
the process.

By default, files will be unrestricted but the utility will ask
for confirmation before uploading.

positional arguments:
  tsv                   TSV file to upload

options:
  -h, --help            show this help message and exit
  -p PID, --pid PID     Dataverse study persistent identifier (DOI/handle)
  -k KEY, --key KEY     API key
  -u URL, --url URL     Dataverse installation base url. defaults to "https://abacus.library.ubc.ca"
  -r, --restrict        Restrict files after upload.
  -n, --no-confirm      Don't confirm non-restricted status
  -t TRUNCATE, --truncate TRUNCATE
                        
                        Left truncate file path. As Dataverse studies
                        can retain directory structure, you can set
                        an arbitrary starting point by removing the
                        leftmost portion. Eg: if the TSV has a file
                        path of /home/user/Data/file.txt, setting
                        --truncate to "/home/user" would have file.txt
                        in the Data directory in the Dataverse study.
                        The file is still loaded from the path in the
                        spreadsheet.
                        
                        Defaults to no truncation.
  -o, --override        
                        
                        Disables replacement of mimetypes for Dataverse-
                        processable files. That is, files such as Excel,
                        SPSS, etc, will have their actual mimetypes sent
                        instead of 'application/octet-stream'.
                        Useful when mimetypes are specified in the TSV
                        file and the upload mimetype is not 
                        the expected result.
                        
  -v, --version         Show version number and exit
```

<a name='footnote' />
## Notes for Windows users

Command line scripts for Python may not necessarily behave the way they do in Linux/Mac, depending on *how* you access them. For detailed information on Windows systems, please see the [Windows testing document](windows.md)


