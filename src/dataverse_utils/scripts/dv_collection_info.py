'''
Recursively parses a dataverse collection and
outputs study metadata for the latest version
'''
import argparse
import io
import csv
import pathlib
import sqlite3
import sys
import textwrap

import pandas as pd # I could use sqlite but why go the hassle
import dataverse_utils
import dataverse_utils.collections as dvc

def parse() -> argparse.ArgumentParser():
    '''
    Parses the arguments from the command line.

    Returns argparse.ArgumentParser
    '''
    description = textwrap.fill(textwrap.dedent(
                   '''
                   Recursively parses a dataverse collection and
                   outputs study and file metadata for the latest version.

                   If analyzing publicly available collections, a
                   dataverse API key for the target system is not
                   required.

                   Study and file output can be joined on 'pid' (studies) and
                   'dataset_pid' (files).
                   '''), 80)
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-u', '--url', default='https://abacus.library.ubc.ca',
                        help=('Dataverse installation base url. '
                              'defaults to "https://abacus.library.ubc.ca"'))
    parser.add_argument('-k', '--key', required=False,
                        help='API key', default=None)
    parser.add_argument('output',
                        help=textwrap.fill(textwrap.dedent(
                        '''
                        Output file name prefix. If tsv output is chosen,
                        files will be saved as [prefix]_studies.tsv
                        and [prefix]_files.tsv.

                        If SQLite output is chosen, it will be a single file file: [prefix].sqlite3.
                        '''),80))
    parser.add_argument('-d', '--delimiter', required=False,
                        help='Delimiter for output spreadsheet. Default: tab (\\t)',
                        default='\t')
    parser.add_argument('-i','--include-all-versions',
                        help='Include *all** versions, not just the current version',
                        action='store_true')
    parser.add_argument('-s', '--sqlite',
                        help='Save output as SQLite3 database',
                        action='store_true')
    group = parser.add_argument_group(title='Harvest options',
                                      description=textwrap.fill(
                                      ' You can obtain info for *either* a recursive crawl '
                                      'of a collection (-c, --collection) OR for a single '
                                      'Dataverse ' 'study (-p, --pid). '
                                      'These arguments are mutually exclusive.'))
    mgroup = group.add_mutually_exclusive_group(required=True)
    mgroup.add_argument('-c', '--collection',
                        help=('Dataverse collection shortname or id at the '
                             'top of the tree'))
    mgroup.add_argument('-p', '--pid',
                        help='Dataverse study persistent identifier (DOI/handle)')
    parser.add_argument('-v', '--version', action='version',
                        version=dataverse_utils.script_ver_stmt(parser.prog),
                        help='Show version number and exit')
    return parser

def fields(include_all:bool, is_file:bool, all_studies)->dict:
    '''
    Outputs appropriate header fields based on argparse values
    '''
    match (include_all, is_file):
        case (0, 0):
            fieldnames = sorted(list(set(key for study in all_studies for key in study)))
        case (1, 0):
            fieldnames = sorted(list(set(key for study in all_studies
                                         for ver in study.versions
                                         for key in study.version_metadata(ver))))
        case (0, 1):
            fieldnames = sorted(list(set(key for study in all_studies
                                         for file in study.files
                                         for key in file)))
        #this is actually an outer join
        #case (1, 1, 0):
        #    fieldnames1 = sorted(list(set(key for study in coll_me.studies
        #                  for ver in study.versions
        #                  for file in study.version_files(ver)
        #                  for key in file)))
        #    fieldnames = sorted(list(set(key for study in coll_me.studies
        #                                 for ver in study.versions
        #                                 for key in study.version_metadata(ver))))
        #    fieldnames.extend(fieldnames1)
        case (1, 1):
            fieldnames = sorted(list(set(key for study in all_studies
                          for ver in study.versions
                          for file in study.version_files(ver)
                          for key in file)))

    return fieldnames

def output(study, include_all=False, file=False)->list:
    '''
    Returns a list of appropriately selected metadata
    '''
    out = []
    match (include_all, file):
        case (0,0):
            return [study]
        case (1,0):
            for v in study.versions:
                out.append(study.version_metadata(v))
            return out
        case (0,1):
            return study.files
        case (1,1):
            for v in study.versions:
                for f in study.version_files(v):
                    out.append(f)
            return out
        ##Outer join
        #case (1,1):
        #    for v in study.versions:
        #        for f in study.version_files(v):
        #            out2 = {}
        #            out2.update(study.version_metadata(v))
        #            out2.update(f)
        #            out.append(out2)
        #        out.append(out2)
        #    return out
        case _:
            return []

def extension(args:argparse.ArgumentParser):
    '''
    Return extension for output
    '''
    extype ={'\t' : '.tsv',
             ','  : '.csv'}
    if args.sqlite:
        return '.sqlite3'
    return extype.get(args.delimiter, '.txt')

def main():
    '''
    You know what this is
    '''
    #pylint: disable=too-many-branches, too-many-locals
    args = parse().parse_args()
    if args.collection:
        coll_me = dvc.DvCollection(args.url, args.collection, args.key)
        try:
            coll_me.get_collections()
        except TypeError:
            print(f'Error with parsing collection: {args.collection}', file=sys.stderr)
            sys.exit()
        try:
            coll_me.get_studies()
            all_studies = coll_me.studies
        except dataverse_utils.collections.MetadataError as e:
            print(e, file=sys.stderr)
            sys.exit()
    else:
        try:
            all_studies = [dvc.StudyMetadata(url=args.url, pid=args.pid, key=args.key)]
        except (KeyError, dataverse_utils.collections.MetadataError) as e:
            print(e, file=sys.stderr)
            sys.exit()
    fname = {0: '_studies', 1:'_files'}
    outdata = {}
    for stud_file in range(2): # studies and files
        fieldnames= fields(args.include_all_versions, stud_file, all_studies)
        out = io.StringIO(newline='')
        writer = csv.DictWriter(out,
                                fieldnames=fieldnames,
                                delimiter=args.delimiter,
                                quoting=csv.QUOTE_MINIMAL,
                                extrasaction='ignore')
        writer.writeheader()
        for stud in all_studies:
            for row in output(stud, args.include_all_versions, stud_file):
                data = {k:v.replace('\t',' ').replace('\r\n', ' ').replace('\n',' ')
                                 if isinstance(v, str) else v
                                 for k, v in row.items()}
                writer.writerow(data)
        out.seek(0)
        outdata[fname[stud_file][1:]] = out
        if not args.sqlite:
            outf =  pathlib.Path(args.output+f'{fname[stud_file]}{extension(args)}').expanduser()
            with open(outf,
                       'w', encoding='utf-8') as f:
                print(f'Writing {str(outf)}', file=sys.stdout)
                f.write(out.read())


    if args.sqlite:
        print(f'Writing {str(pathlib.Path(args.output+extension(args)).expanduser())}',
              file=sys.stdout)
        conn = sqlite3.connect(pathlib.Path(args.output+extension(args)).expanduser())
        for k,v in outdata.items():
            x=pd.read_csv(v, delimiter=args.delimiter)
            x.to_sql(k, conn, if_exists='replace', index=0)
        cursor = conn.cursor()
        cursor.execute('DROP VIEW IF EXISTS short_combined_view;')
        query = textwrap.fill(textwrap.dedent(
                    '''CREATE VIEW short_combined_view AS
                        SELECT studies.pid AS pid,
                        studies.authorName AS author,
                        studies.title AS title,
                        studies.dateOfDeposit AS deposit_date,
                        studies.versionStatement AS version_statement,
                        files.dataFile_filename AS file_name,
                        files.dataFile_id AS file_id,
                        files.restricted AS restricted,
                        files.version AS file_version
                        FROM studies
                        INNER JOIN files ON studies.pid = files.dataset_pid;
                        '''
                    ),80)
        cursor.execute(query)
        conn.close()

if __name__ == '__main__':
    main()
