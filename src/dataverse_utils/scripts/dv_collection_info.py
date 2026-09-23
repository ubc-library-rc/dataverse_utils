'''
Recursively parses a dataverse collection and
outputs study metadata for the latest version
'''
import argparse
import datetime
import io
import csv
import logging
import pathlib
import sqlite3
import sys
import textwrap

from typing import Union

import requests
import tqdm

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

                   While an API key may not necessarily be required for public
                   data, this software requires a key.

                   Study and file output can be joined on 'pid' (studies) and
                   'dataset_pid' (files).

                   If a SQLite3 database already exists, at the stated location,
                   data will be added to it,
                   based either on the 'updates' table or the --since switch.

                   Studies will be added if updates have occurred on or after
                   the appropriate date.
                   Note that dates are UTC and begin at midnight, so
                   2026-08-20 would be 2026-08-20T00:00:00Z.
                   '''), 80)
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-u', '--url', default='https://abacus.library.ubc.ca',
                        help=('Dataverse installation base url. '
                              'defaults to "https://abacus.library.ubc.ca"'))
    parser.add_argument('-k', '--key', required=True, #should it be true?
                        help='API key', default=None)
    parser.add_argument('output',
                        help=textwrap.fill(textwrap.dedent(
                        '''
                        Output file name prefix. If output is not sqlite,
                        files will be saved as [prefix]_studies.[ct]sv
                        and [prefix]_files.[ct]sv

                        If SQLite output is chosen, it will be a single file file: [prefix].sqlite3.

                        Common sqlite3 extensions will be changed to .sqlite3.
                        If you provide the wrong format, the correct extension will
                        be appended.
                        '''),80))
    parser.add_argument('-d', '--delimiter', required=False,
                        help=textwrap.fill(textwrap.dedent(
                        '''
                        Delimiter for output spreadsheet.
                        Default: tab (\\\t). Choose between \',\' and \'\\t\'
                        '''),80),
                        choices=['\t', ','],
                        default='\t')
    parser.add_argument('--since',
                        help='Only updates since this date. Use ISO format. eg: 2026-07-02',
                        default=None,
                        required=False)
    parser.add_argument('-i','--include-all-versions',
                        help='Include *all** versions, not just the current version',
                        action='store_true')
    parser.add_argument('-s', '--sqlite',
                        help='Save output as SQLite3 database',
                        action='store_true')
    parser.add_argument('-l', '--log',
                        help=textwrap.fill(textwrap.dedent(
                        '''
                        If you would like a log, provide a log file name here.
                        If no file name is provided, no log is created.
                        '''),80),
                        default=None)
    parser.add_argument('--log-level',
                         help=textwrap.fill(textwrap.dedent(
                        '''
                        Log level. Acceptable values for log level are: debug, info,
                        warning, error, critical.
                        Default value: warning.
                        '''),80),
                        default='warning')
    parser.add_argument('--rate-limit-off',
                        action='store_true',
                        help=('Turn off rate limiter. '
                              'Requests are randomly between min and max. Default is ON.'))
    parser.add_argument('--rate-limit-min',
                        help='Minimum time before requests in seconds. Default 0.25',
                        default=0.25,
                        type=float)
    parser.add_argument('--rate-limit-max',
                        help='Maximum time between requests in seconds: Default 1',
                        default=1,
                        type=float)
    parser.add_argument('--timeout',
                        help='Timeout for lengthy requests, default 300s',
                        default=300,
                        type=float)
    parser.add_argument('-c', '--collection',
                        help=('Dataverse collection shortname or id at the '
                             'top of the tree'),
                        required=True)
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

def logme(pargs:argparse.Namespace)->logging.Logger:
    '''
    Text logger
    '''
    logger=logging.getLogger()
    l_format = logging.Formatter('%(name)s - %(asctime)s'
                                 ' - %(levelname)s - %(funcName)s - '
                                 '%(message)s')
    lookup = {'debug' : logging.DEBUG,
              'info' : logging.INFO,
              'warning': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL}
    level = lookup.get(pargs.log_level.lower(), logging.WARNING)
    logger.setLevel(level)
    if pargs.log:
        text = logging.FileHandler(pargs.log, encoding='utf-8', delay=True)
        text.setFormatter(l_format)
        logger.addHandler(text)
        return logger
    logger.addHandler(logging.NullHandler())
    return logger

def get_collection(args, logger)->(dvc.DvCollection, list):
    '''
    Recursively process a collection and get a list
    '''
    coll_me = dvc.DvCollection(args.url, args.collection, args.key,
                               rate_limit_on=not args.rate_limit_off,
                               rate_limit_min=args.rate_limit_min,
                               rate_limit_max=args.rate_limit_max,
                               timeout=args.timeout)
    try:
        coll_me.get_studies()
        all_studies = coll_me.studies
        if not all_studies: #Stupid but this happens
            print('No studies in collection', file=sys.stderr)
            logger.warning('No studies to process in collection %s', args.collection)
            sys.exit()
    except dataverse_utils.collections.MetadataError as e:
        print(e, file=sys.stderr)
        logger.critical(e)
        sys.exit()
    except TypeError as e:
        print(f'Error with parsing collection: {args.collection}', file=sys.stderr)
        logger.critical(e)
        sys.exit()
    #return coll_me, all_studies
    return all_studies

def get_individual_pid(pid :str, args:argparse.Namespace,
                       logger:logging.RootLogger, **kwargs)->list:
    '''
    Get a dvc.StudyMetadata object for an individual pid
    Parameters
    ----------
    pid : str
    args: argparse.Namespace
    logger: logging RootLogger
    kwargs
        Notably: collection_short_name and collection_name

    '''
    try:
        stud = dvc.StudyMetadata(url=args.url, pid=pid, key=args.key,
                                         rate_limit_on=True,
                                         rate_limit_min=0.25,
                                         rate_limit_max=1,
                                         **kwargs)
    except (KeyError, dataverse_utils.collections.MetadataError) as e:
        print(e, file=sys.stderr)
        logger.critical(e)
        sys.exit()
    return stud

def add_timestamp(conn:sqlite3.Connection, logger=logging.RootLogger) -> None:
    '''
    Add a timestamp after processing
    '''
    create = 'CREATE TABLE IF NOT EXISTS updates (update_time DATE)'
    cursor = conn.cursor()
    conn.commit()
    cursor.execute(create)
    logger.info('Added timestamp to %s', 'updates')
    cursor.execute('INSERT INTO updates SELECT CURRENT_TIMESTAMP')
    conn.commit()

def read_timestamp(conn:sqlite3.Connection)->Union[None, str]:
    '''
    Get the timestamp from the sqlite database if available
    '''
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE name=? AND type=?',
                   ('updates', 'table'))
    if not cursor.fetchone():
        return None
    cursor.execute('SELECT rowid, * FROM updates ORDER BY rowid DESC')
    return cursor.fetchone()['update_time']

def dict_factory(cursor:sqlite3.Cursor, row:sqlite3.Row)->dict:
    '''
    Dictionary factory
    '''
    fi = [column[0] for column in cursor.description]
    return dict(zip(fi, row))

def date_converter(instr:Union[str, None], offset_h=0, offset_m=0):
    '''
    instr : str
        SQLlite3 timestamp
    offset : int
        UTC timezone offset

    Normally there is no offset because sqlite3.CURRENT_TIMESTAMP is UTC anyway.
    '''
    sql_tstring ='%Y-%m-%d %H:%M:%S'
    #2026-06-01T00:00:00Z
    dv_tstring = '%Y-%m-%dT%H:%M:%SZ'
    time_mod = -1 if abs(offset_h) != offset_h else 1
    correction = datetime.timedelta(hours=offset_h, minutes=offset_m)
    if instr:
        #timeunit =time.strptime(instr, sql_tstring)
        timeunit = datetime.datetime.strptime(instr, sql_tstring)
    else:
        timeunit = datetime.datetime.now()
    dv_time = timeunit + time_mod * correction
    return datetime.datetime.strftime(dv_time, dv_tstring)

def cleaned_dict(indict: dict):

    '''
    Clean a dict before insertion
    '''
    #pylint: disable=cell-var-from-loop
    problem_chars = ['\t', '\n\r', '\n', '\r']
    row = list(indict.values()) #must be list because dict key is not a string
    for pr in problem_chars:
        row = list(map(lambda x: x.replace(pr, ' ').strip()
                       if isinstance(x, str) else x, row))
    #and because categories are lists
    row = map(lambda x: x if not isinstance(x, list) else str(x), row)

    return dict(zip(indict.keys(), row))

def cleaned_dict_factory(cursor:sqlite3.Cursor, row:sqlite3.Row)->dict:
    '''
    Dictionary factory, but the values have had [ctx]sv problematic values
    stripped out
    '''
    #pylint: disable=cell-var-from-loop
    #This function is not currently used
    fi = [column[0] for column in cursor.description]
    #Add further problematic character combos to this list.
    problem_chars = ['\t', '\n\r', '\n', '\r']
    #must row be a list, not a map
    for pr in problem_chars:
        row = list(map(lambda x: x.replace(pr, ' ').strip()
                       if isinstance(x, str) else x, row))
    return dict(zip(fi, row))

def get_new_pids(args:argparse.Namespace, sql_ts:str,
                        logger:logging.RootLogger) -> list:
    '''
    Updates only. Returns a list of dicts
    [{'pid':a, 'shortname':b, 'longname':c}, . . .)

    Parameters
    ----------
    args : argparse.Namespace
    sql_ts : str
        SQLite timestamp
    logger : logging.RootLogger
    '''
    session = requests.Session()
    session.mount('https://',  requests.adapters.HTTPAdapter(max_retries=dvc.RETRY))
    headers = {'X-Dataverse-key':args.key}
    headers.update(dvc.UAHEADER.copy())
    url = args.url.strip('/').lower().strip()
    url = f'https://{url}' if not url.startswith('https://') else f'{url}'
    url = url + '/api/search?q=*&type=dataset&sort=date&order=desc&per_page=250'\
          f'&show_facets=true&subtree={args.collection}'
    logger.info(url)
    then = date_converter(sql_ts)
    now = date_converter(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    undone = True
    start = 0
    data = []
    while undone:
        x = session.get(f'{url}&fq=dateSort:[{then}+TO+{now}]&start={start}',
                        headers=headers, timeout=100)
        try:
            x.raise_for_status()
        except requests.HTTPError as exc:
            logger.critical('HTTP Error %s: %s', x.status_code, x.reason)
            logger.critical(f'{url}&fq=dateSort:[{then}+TO+{now}]&start={start}')
            logger.critical(x.text)
            print(x.text, file=sys.stderr)
            raise requests.HTTPError(f'{x.status_code}: {x.reason}') from exc
        total = x.json()['data']['total_count']
        for rec in x.json()['data']['items']:
            data.append({'pid':rec['global_id'],
                        'shortname': rec['identifier_of_dataverse'],
                         'longname' :rec['name_of_dataverse']})
        start += 250
        if start > total:
            undone = False
    return data
    #https://borealisdata.ca/api/search?q=*&type=dataset&sort=date&order=desc
    #&show_facets=true&fq=dateSort:[2026-08-01T00:00:00Z+TO+2026-08-30T00:00:00Z]&per_page=1000

def create_table(conn:sqlite3.Connection, table:str,
                 columnlist:dict, logger:logging.RootLogger):
    '''
    Create tables
    '''
    cursor = conn.cursor()
    f_type = ', '.join([f'{k} {v}' for k, v in columnlist.items()])
    create = f'CREATE TABLE IF NOT EXISTS {table} ({f_type});'
    cursor.execute(create)
    logger.info('Creating table if it doesn\'t exist: %s', table)
    conn.commit()

def add_new_columns(conn:sqlite3.Connection, table:str,
                    columnlist:dict, logger:logging.RootLogger):
    '''
    Create and update tables as required
    '''
    cursor = conn.cursor()
    cursor.execute('SELECT sql FROM sqlite_master WHERE tbl_name=?', (table,))
    newcol = False
    newvals = {}
    if not cursor.fetchall():
        create_table(conn, table, columnlist, logger)
        return
    cursor.execute('SELECT sql FROM sqlite_master WHERE tbl_name=?', (table,))
    old_def = cursor.fetchone()['sql']
    old_def = old_def[old_def.find('(')+1:old_def.rfind(')')].split(',')
    for b in ['\n', '"']:
        old_def = [a.replace(b,'').strip() for a in old_def]
    old_def = {x.split(' ')[0].strip(): x.split(' ')[1].strip() for x in old_def}
    for k, v in columnlist.items():
        if k not in old_def:
            newcol = True
            newvals.update({k:v})
    #What happens if they *delete* a thing, which happens.
    #We must still keep it.
    if newcol:
        replicate(conn, table, old_def, columnlist, logger)
        logger.warning('New columns found: %s', ', '.join(newvals))
        logger.warning('Duplicating %s and adding new columns: %s', table,
                        newvals)

def replicate(conn:sqlite3.Connection, table:str,
              old_def:dict, columnlist:dict, logger:logging.RootLogger):
    '''
    Create a new table but add the contents of the old one.
    '''
    cursor = conn.cursor()
    cursor.execute("SELECT type, name, sql from sqlite_master where type='view';")
    views = cursor.fetchall()
    for view in views:
        logger.warning('Dropping view %s', view['name'])
        cursor.execute(f'DROP VIEW IF EXISTS {view["name"]};')
    conn.commit()
    logger.warning('Creating a new version of %s', table)
    cursor.execute(f'ALTER TABLE {table} RENAME TO {table}bak;')
    newcols = old_def.copy()
    newcols.update(columnlist)
    tmp = sorted(newcols)
    newcols = {a: newcols[a] for a in tmp} #alphabetize!
    create_table(conn, table, newcols, logger) #Because you want to keep all the old fields
    dupl = f"INSERT INTO {table} ({', '.join(old_def)}) SELECT {', '.join(old_def)} FROM {table}bak"
    cursor.execute(dupl)
    conn.commit()
    for view in views:
        logger.warning('Recreating view  %s', view['name'])
        cursor.execute(view['sql'])
        conn.commit()
    logger.warning('Dropping old table %s', table+'bak')
    cursor.execute(f'DROP TABLE IF EXISTS {table}bak;')
    conn.commit()

def delete_existing(pid:str, table:str, conn:sqlite3.Connection,
                    logger:logging.RootLogger)->None:
    '''
    Remove old records so that there is no conflict with old ones
    Really it should only be a version number change but that will not be as fast
    '''
    cursor = conn.cursor()
    logger.warning('Deleting info for %s: %s', table, pid)
    choose = {'studies': 'pid', 'files':'dataset_pid'}
    cursor.execute(f'DELETE FROM {table} WHERE {choose[table]} = ?',
                   (pid,))
    conn.commit()

def get_all_values(in_list)->dict:
    '''
    Returns a dict which contains one key from all the dicts plus
    a value for every key. That is, you can see the combined keys
    and get a value for every key.

    eg: [{1:'a', 2:'b'}, {3:'c'}, {1:'f', 4:'d'}] ->
    {1:'a', 2:'b', 3:'c', 4:'d'}

    Parameters
    ----------
    in_list : list
        A list of dicts
    '''
    keys =  list(set(y for x in in_list for y in x))
    keys = sorted(keys)
    valdict = {}
    for k in keys:
        for stud in in_list:
            for k, v in stud.items():
                if valdict.get(k):
                    continue
                #this can happen with things with Boolean values that are False,
                #like fileAccessRequest
                if v or isinstance(v, (bool, int)):
                    valdict.update({k:v})
                #and not everyone uses file persistentIds so it's None
            if valdict.keys() == keys:
                break # All are filled
    outdict = {}
    if len(keys) != len(valdict):
        #because some values can be None, which is stupid but true
        missing = [_ for _ in keys if _ not in valdict]
        for miss in missing:
            valdict.update({miss: None})
    for k in keys:
        outdict.update({k: valdict[k]}) #sorted, again
    return outdict

def sqlite_type(in_thing)->str:
    '''
    Output an SQLite type for an arbitrary object.

    Parameters
    ----------
    in_thing : obj
        Arbitrary value from metadata. Will return
        an SQLite 3 type for the value (not including NUMERIC)
    '''
    #https://stackoverflow.com/questions/67524641/
    #convert-multiple-isinstance-checks-to-structural-pattern-matching
    match in_thing:
        case float():
            sqlt = 'FLOAT'
        case int():
            sqlt = 'INT'
        case str():
            sqlt = 'TEXT'
        case _:
            sqlt = 'BLOB'
    return sqlt

def get_table_def(dictlist:list)->dict:
    '''
    Produce a dict with column names as keys and values
    as sqlite type

    Parameters
    ----------
    dictlist : list
        A list of dicts, generally containing study or file metadata
    '''
    sample = get_all_values(dictlist)
    outdict = {}
    for k, v in sample.items():
        outdict.update({k: sqlite_type(v)})
    for k in ['versionStatement', '']:
        if outdict.get(k):
            outdict[k] = 'TEXT'
    return outdict

def write_data(conn:sqlite3.Connection, data:dict,
               table:str, logger:logging.RootLogger)->None:
    '''
    Write data to the appropriate table
    '''
    cursor = conn.cursor()
    query = f"INSERT INTO {table} ({', '.join(data)}) VALUES ({', '.join('?' for _ in data)})"
    cursor.execute(query, tuple(_ for _ in data.values()))
    logger.info(f'Inserting data into {table}')
    logger.debug('%s: %s', query, data.items())
    conn.commit()

def create_view(conn:sqlite3.Connection, logger)->None:
    '''
    Create views
    '''
    cursor = conn.cursor()
    query = textwrap.fill(textwrap.dedent(
                '''CREATE VIEW IF NOT EXISTS short_combined_view AS
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
    conn.commit()
    logger.info('Created view: short_combined_view')

def make_tsv(conn:sqlite3.Connection,args: argparse.ArgumentParser,
              table:str, logger:logging.RootLogger)->io.StringIO:
    '''
    Output a StringIO [n]sv of a selected table (or view).
    '''
    cursor = conn.cursor()
    cursor.execute(f'SELECT * from {table}')
    data = cursor.fetchall()
    out = io.StringIO(newline='')
    logger.info('Making spreadsheet for %s with delimiter %s', table, args.delimiter)
    writer = csv.DictWriter(out, fieldnames=data[0].keys(),
                            quoting=csv.QUOTE_MINIMAL,
                            delimiter=args.delimiter,
                            extrasaction='ignore')
    writer.writeheader()
    for row in data:
        writer.writerow(row)
    out.seek(0)
    return out

def clean_filename(args):
    '''
    Return a suffixless base path'
    '''
    suff = pathlib.Path(args.output).suffix.lower()
    instr = args.output
    if suff in extension(args):
        instr = instr[:-len(suff)]
    return instr

def main(par:argparse.ArgumentParser=None):
    '''
    Replacement
    '''
    #pylint: disable=too-many-branches, too-many-locals, too-many-statements
    args = parse().parse_args() if not par else par().parse_args()
    logger = logme(args)
    args.output = clean_filename(args)
    dbase_file = pathlib.Path(args.output+extension(args)).expanduser()\
            if args.output and args.sqlite else None
    dbase =':memory:' if not args.sqlite else dbase_file
    conn = sqlite3.connect(dbase)
    conn.row_factory = dict_factory
    cur2 = conn.cursor()
    sql_ts = read_timestamp(conn) if not args.since \
              else f'{args.since} 00:00:00' if args.since else None

    if not sql_ts:
        #get it all because there's no timestamp
        #collection, all_studies = get_collection(args, logger)
        all_studies = get_collection(args, logger)

    else:
        updates  = get_new_pids(args, sql_ts, logger)
        all_studies = []
        for stud in tqdm.tqdm(iterable=updates,
                              desc='studies',
                              unit='study',
                              bar_format=dvc.BAR_FORMAT):
            s = get_individual_pid(stud['pid'], args, logger,
                                   collection_short_name=stud['shortname'],
                                   collection_name=stud['longname'])
            #s['collection_short_name'] = stud['shortname']
            #s['collection_name'] = stud['longname']
            all_studies.append(s)
    if not all_studies:
        msg = 'Nothing to do — no studies'
        print(msg, file=sys.stderr)
        logger.warning(msg)
        add_timestamp(conn, logger)
        sys.exit()
    fname = {0: '_studies', 1:'_files'}
    #outdata = {}
    for stud_file in range(2):
        #SUPERSEDED fieldnames = fields(args.include_all_versions, stud_file, all_studies)
        fields_dict = [output(stud, args.include_all_versions, stud_file) for stud in all_studies]
        fields_dict = [y for x in fields_dict for y in x]
        #Now fields_dict is a flat list of records so we can extract names and types
        tabledef = get_table_def(fields_dict)
        create_table(conn, fname[stud_file][1:], tabledef, logger)
        add_new_columns(conn, fname[stud_file][1:], tabledef, logger)
        cur2.execute('SELECT pid from studies')
        pidlist = [_.get('pid') for _ in cur2.fetchall()]
        #fields_dict, while flat, is kind of useless for writing because we have to delete
        #the PID only once, so we're going back to all_studies.
        for stud in all_studies:
            #going back to all_studies
            #delete first and pray there is no error.
            if stud.pid in pidlist:
                delete_existing(stud.pid, fname[stud_file][1:], conn, logger)
            for row in output(stud, args.include_all_versions, stud_file):
                #should data be cleaned? Yes, because the old databases
                #contain cleaned data and it's a PITA if you need to export
                #But now it's a function!
                row = cleaned_dict(row)
                write_data(conn, row, fname[stud_file][1:], logger)

    add_timestamp(conn, logger)
    create_view(conn, logger)
    cur2.execute('VACUUM;')
    conn.commit()
    if not args.sqlite:
        for table in fname.values():
            t = make_tsv(conn, args, table[1:], logger)
            fname =  pathlib.Path(args.output+table+extension(args)).expanduser()
            with open(fname, mode='w', encoding='utf-8') as f:
                f.write(t.read())

if __name__ == '__main__':
    main()
