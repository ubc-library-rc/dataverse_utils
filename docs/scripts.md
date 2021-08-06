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

Note that these programs have been primarily tested on Linux and MacOS, with [Windows a distant third](#footnote). Windows is notable for its unusual file  handling, so, as the MIT licenses stipulates, there is no warranty as to the suitability for a particular purpose.

Of course, they *should* work.

In no particular order:

## dv_del.py

This is bulk deletion utility for unpublished studies (or even single studies). It's useful when your automated procedures have gone wrong, or if you don't feel like navigating through many menus.

Note the `-i` switch which can ask for manual confirmation of deletions.


**Usage**

```nohighlight
usage: dv_del.py [-h] -k KEY [-d DATAVERSE | -p PID] [-i] [-u DVURL]

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
```

##  dv_manifest_gen.py

Not technically a Dataverse-specific script, this utility will generate a tab-separated value output. The file consists of 3 columns: **file, description and tags**. 

Editing the result and using the upload utility to parse the tsv will add descriptive metadata, tags and file paths to an upload instead of laboriously using the Dataverse GUI.

Tags may be separated by commas, eg: "Data, SAS, June 2021".

Using stdout and a redirect will also save time. First dump a file as normal. Add other files to the end with different information using the exclude header switch `-x` and different tags along with output redirection `>>`.

**Usage**

```nohighlight
usage: dv_manifest_gen.py [-h] [-f FILENAME] [-t TAG] [-x] [-r] [--version] [files [files ...]]

Creates a file manifest in tab separated value format which can then be edited and used for file uploads to a Dataverse collection. Files can be edited to add file descriptions and
comma-separated tags that will be automatically attached to metadata using products using the dataverse_utils library. Will dump to stdout unless -f or --filename is used. Using the
command and a dash (ie, "dv_manifest_gen.py -" produces full paths for some reason.

positional arguments:
  files                 Files to add to manifest

optional arguments:
  -h, --help            show this help message and exit
  -f FILENAME, --filename FILENAME
                        Save to file instead of outputting to stdout
  -t TAG, --tag TAG     Default tag(s). Separate with comma and use quotes if there are spaces. eg. "Data, June 2021". Defaults to "Data"
  -x, --no-header       Don't include header in output. Useful if creating a complex tsv using redirects (ie, ">>").
  -r, --recursive       Recursive listing.
  --version             Show version number and exit
```

## dv_upload_tsv.py

Now that you have a tsv full of nicely described data, you can easily upload it to an existing study if you know the persistent ID and have an API key.

For the best metadata, you should probably edit it manually to add correct descriptive metadata, notably the "Description" and "Tags". Tags are split separated by commas, so it's possible to have multiple tags for each data item, like "Data, SPSS, June 2021".

File paths are automatically generated from the "file" column. Because of this, you should probably use relative paths rather than absolute paths unless you want to have a lengthy path string in Dataverse.

**Usage**

```nohighlight
usage: dv_upload_tsv.py [-h] -p PID -k KEY [-u URL] [--version] [tsv]

Uploads data sets to an *existing* Dataverse study from the contents of a TSV (tab separated value) file. Metadata, file tags, paths, etc are all read from the TSV. JSON output from the
Dataverse API is printed to stdout during the process.

positional arguments:
  tsv                TSV file to upload

optional arguments:
  -h, --help         show this help message and exit
  -p PID, --pid PID  Dataverse study persistent identifier (DOI/handle)
  -k KEY, --key KEY  API key
  -u URL, --url URL  Dataverse installation base URL. Defaults to "https://abacus.library.ubc.ca"
  --version          Show version number and exit
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

<a name='footnote' />
## Notes for Windows users

Command line scripts for Python don't necessarily behave the way they do in Linux/Mac, depending on *how* you access them. For detailed information on Windows systems, please see the [Windows testing document](windows.md)

