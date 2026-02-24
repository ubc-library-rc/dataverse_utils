'''
Recursively parses a dataverse collection and
outputs study metadata for the latest version
'''
import argparse
import io
import csv
import sys
import textwrap
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
                   outputs study metadata for the latest version.

                   If analyzing publicly available collections, a
                   dataverse API key for the target system is not
                   required.
                   '''), 80)
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-u', '--url', default='https://abacus.library.ubc.ca',
                        help=('Dataverse installation base url. '
                              'defaults to "https://abacus.library.ubc.ca"'))
    parser.add_argument('-k', '--key', required=False,
                        help='API key', default=None)
    parser.add_argument('-d', '--delimiter', required=False,
                        help='Delimiter for output spreadsheet. Default: tab (\\t)',
                        default='\t')
    parser.add_argument('-f', '--fields',
                        help=textwrap.fill(('Record metadata fields to output. '
                              'For all fields, use "all". '
                              'Default: title, author. for '
                              'study metadata and file label, id for file metadata' )),
                        nargs='*',
                        default=['title', 'author', 'file_label', 'id'])
    parser.add_argument('-o', '--output', help='Output file name.',
                       required=False)
    parser.add_argument('-i','--include-all-versions',
                        help='Include *all** versions, not just the current version',
                        action='store_true')
    parser.add_argument('--files',
                        help=textwrap.fill(('Show only the *files* associated with a study.'
                              'The output will contain the PID of the study '
                              'and the version (if applicable) so that study metadata '
                              'and file metadata can be linked')),
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
                        help=('Dataverse study persistent identifier (DOI/handle)'
                             'top of the tree'))
    parser.add_argument('-v', '--version', action='version',
                        version=dataverse_utils.script_ver_stmt(parser.prog),
                        help='Show version number and exit')
    return parser

def fields(args:argparse.ArgumentParser, all_studies)->dict:
    '''
    Outputs appropriate header fields based on argparse values
    '''
    #print(args)
    match (args.include_all_versions, args.files):
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

def fields_no(args:argparse.ArgumentParser, all_studies, fmeta=False)->dict:
    '''
    Outputs appropriate header fields based on argparse values
    '''
    #print(args)
    match (args.include_all_versions, args.files, fmeta):
        case (0, 0, 0):
            fieldnames = sorted(list(set(key for study in all_studies for key in study)))
        case (1, 0, 0):
            fieldnames = sorted(list(set(key for study in all_studies
                                         for ver in study.versions
                                         for key in study.version_metadata(ver))))
        case (0, 1, 0):
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
        case (1, 1, 0):
            fieldnames = sorted(list(set(key for study in all_studies
                          for ver in study.versions
                          for file in study.version_files(ver)
                          for key in file)))

        case (1, 0, 1):
            fieldnames = sorted(list(set(key for ver in all_studies[0].versions
                                     for key in all_studies[0].version_metadata(ver))))
        case (1, 1, 1):
            fieldnames = sorted(list(set(key
                      for ver in all_studies[0].versions
                      for file in all_studies[0].version_files(ver)
                      for key in file)))
        case (0, 1, 1):
            fieldnames = sorted(list(set(key for file in all_studies[0].files
                                     for key in file)))

        case (0, 0, 1):
            fieldnames = sorted(list(set(all_studies[0])))
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
                out.append(study.study_version_metadata(v))
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

def main():
    '''
    You know what this is
    '''
    #pylint: disable=too-many-branches
    args = parse().parse_args()
    if args.collection:
        coll_me  = dvc.DvCollection(args.url, args.collection, args.key)
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
        except dataverse_utils.collections.MetadataError as e:
            print(e, file=sys.stderr)
            sys.exit()
    #if 'all' in [x.lower() for x in args.fields] and args.collection:
    #    fieldnames = fields(args, all_studies)

    #if 'all' in [x.lower() for x in args.fields] and args.pid:
    #    fieldnames = fields(args, all_studies, 1)
    if 'all' in [x.lower() for x in args.fields]:
        fieldnames = fields(args, all_studies)

    else:
        fieldnames =  args.fields[2:] if args.files else args.fields[:2]

    out = io.StringIO(newline='')
    writer = csv.DictWriter(out,
                            fieldnames=fieldnames,
                            delimiter=args.delimiter,
                            quoting=csv.QUOTE_MINIMAL,
                            extrasaction='ignore')
    writer.writeheader()
    #for stud in coll_me.studies:
    for stud in all_studies:
        for row in output(stud, args.include_all_versions, args.files):
            writer.writerow({k:v.replace('\t',' ').replace('\r\n', ' ').replace('\n',' ')
                             if isinstance(v, str) else v
                             for k, v in row.items()})
    out.seek(0)
    if args.output:
        with open(args.output, mode='w', encoding='utf-8', newline='') as f:
            f.write(out.read())
            return
    else:
        print(out.read())

if __name__ == '__main__':
    main()
