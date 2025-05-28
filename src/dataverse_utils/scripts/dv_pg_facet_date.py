#!python
'''
Reads the date from a Dataverse study and forces the facet sidebar to use that
date by manually updating the Dataverse Postgres database.

This *must* be run on the server that hosts a Dataverse installation,
and the user must supply, at a minimum, the database password and
a persistent ID to be read, as well as a date type.

Requires two non-standard python libraries: psycopg2
(use psycopg2-binary to avoid installing from source) and requests.

Psycopg2 is not part of the requirements for dataverse_utils
because it is only used for the server portion of these utilities,
and hence useless for them.
'''
import argparse
import csv
import datetime
import os
import sys

import requests
try:
    import psycopg2
except ModuleNotFoundError:
    print(('Packge psycopg2 not found.'
           'Either install dataverse_utils[server] or '
           'Manually install psycopg2. \n'
           'Generally, try \'pip install psycopg2-binary\' to  '
           'install pre-compiled binaries. If unavailable for your '
           'platform, use \'pip install pysycopg2\'.'
           ))
    sys.exit()

VERSION = (0, 1, 1)
__version__ = '.'.join([str(x) for x in VERSION])

def parsely() -> argparse.ArgumentParser: #HAHA it's parsley but misspelled.
    '''
    Command line argument parser
    '''
    description = ('A utility to change the \'Production Date\' web interface facet '
            'in a Dataverse installation to one of '
            'the three acceptable date types:  \'distributionDate\', \'productionDate\', '
            'or \'dateOfDeposit\'. '
            'This must be done in the PostgreSQL database directly, so this utility must '
            'be run on the *server* that hosts a Dataverse installation. '
            'Back up your database if you are unsure.')
    epilog = ('THIS WILL EDIT YOUR POSTGRESQL DATABASE DIRECTLY. '
              'USE AT YOUR OWN RISK.')
    parser = argparse.ArgumentParser(description=description,
                                     epilog=epilog)
    parser.add_argument('pids', nargs='+', help='persistentIdentifier')
    parser.add_argument('date', choices=['distributionDate',
                                         'productionDate', 'dateOfDeposit',
                                         'dist', 'prod', 'dep'],
                        help='date type which is to be shown in the facet. '
                             'The short forms are aliases for the long forms.' )
    parser.add_argument('-d', '--dbname', help='Database name',
                        default='dvndb')
    parser.add_argument('-u', '--user', help='PostgreSQL username',
                        default='dvnapp')
    parser.add_argument('-p', '--password', help='PostgreSQL password',
                        required=True)
    exgroup = parser.add_mutually_exclusive_group()
    exgroup.add_argument('-r', '--dry-run', help='print proposed SQL to stdout',
                        action='store_true')
    exgroup.add_argument('-o', '--sql-only',
                        help=('dump sql to file called *pg_sql.sql* '
                              'in current directory. Appends to file if '
                              'it exists'),
                        action='store_true')
    parser.add_argument('-s', '--save-old',
                       help=('Dump old values to tsv called *pg_changed.tsv* '
                             'in current directory. Appends to file if '
                             'it exists'),
                        action='store_true')
    parser.add_argument('-k', '--key', help='API key for Dataverse installation.',
                        required=True)
    parser.add_argument('-w', '--url',
                        help=('URL for base Dataverse installation. Default '
                              'https://abacus.library.ubc.ca'),
                        default='https://abacus.library.ubc.ca')
    parser.add_argument('--version', action='version',
                        version='%(prog)s '+__version__,
                        help='Show version number and exit')
    return parser

def parse_dtype(dtype) -> str:
    '''
    Returns correctly formatted date type string for Dataverse API

    ---
    dtype : str
        One of the allowable values from the parser
    '''
    mapper = {'distributionDate': ['dist', 'distributionDate'],
              'productionDate' : ['prod', 'productionDate'],
              'dateOfDeposit' : ['dep', 'dateOfDeposit']}
    for key, value in mapper.items():
        if dtype in value:
            return key
    return None

def write_old(data) -> None:
    '''
    Writes older data to a tsv file. Assumes 4 values per item:
    id, authority, identifier, publicationdate.

    publicationdate is assumed to be a datetime.datetime instance.

    ------
    Parameters:

    data : list
        Postqres query output list (ie, data = cursor.fetchall())
    '''
    flag = os.path.exists('pg_changed.tsv')
    with open('pg_changed.tsv', 'a', encoding='utf-8') as tsv:
        writer = csv.writer(tsv, delimiter='\t')
        if not flag:
            writer.writerow(['id', 'authority', 'identifier', 'publicationdate'])
        for row in data:
            #PG time format: 2021-10-21 12:07:21.616
            writer.writerow([row[0], row[1], row[2],
                    row[3].strftime('%Y-%m-%d %H:%M:%S.%f')])

def write_sql(data) -> None:
    '''
    Write SQL to file
    '''
    if not os.path.exists('pg_sql.sql'):
        flag = 0
    else:
        flag = 1
    if flag:
        with open('pg_sql.sql', encoding='utf-8') as sql:
            lines = list(sql)[:-1]
    with open('pg_sql.sql', 'w', encoding='utf-8') as sql:
        if not flag:
            sql.write('BEGIN;\n')
        if flag:
            for lin in lines:
                sql.write(lin)
        sql.write(data)
        sql.write('COMMIT;\n')

def get_datetime(datestr) -> (datetime.datetime, str):
    '''
    Return datetime from poorly formatted Dataverse dates string

    ----
    datestr : str
        Dataverse date returned by API
    '''
    if len(datestr) == 4:
        datestr += '-01-01'
    elif len(datestr) == 7:
        datestr += '-01'
    return datetime.datetime.strptime(datestr, '%Y-%m-%d'), datestr

def fetch_date_api(url, key, pid, dtype) -> str:
    '''
    Returns the requested date string from the Dataverse study record

    ----
    url : str
        Base URL of Dataverse installation
    key :str
        API key for Dataverse user
    pid : str
        Persistent identifier for Dataverse study
    dtype : str
        Date type required
    '''
    study = requests.get(f'{url}/api/datasets/:persistentId',
                          headers={'X-Dataverse-key':key},
                          params={'persistentId':pid},
                          timeout=90)
    out = study.json()
    result = [a['value'] for a in
              out['data']['latestVersion']['metadataBlocks']['citation']['fields']
              if a['typeName']==dtype]
    if result:
        return result[0]
    return None

def reindex(pid) -> dict:
    '''
    Reindexes study in place. Localhost access only.

    ----
    pid : str
        PersistentId for Dataverse study
    '''
    req = f'http://localhost:8080/api/admin/index/dataset?persistentId={pid}'
    reind = requests.get(req, timeout=30)
    return reind.json()

def main():
    '''
    The heart of the application
    '''
    parser = parsely()
    args = parser.parse_args()
    args.url = args.url.strip(' /')
    #import sys
    #print(args)
    #sys.exit()
    conn = psycopg2.connect(database=args.dbname, user=args.user,
                            password=args.password)
    cursor = conn.cursor()
    for pid in args.pids:
        authority =  pid[pid.find(':')+1:pid.find('/')].strip()
        identifier = pid[pid.find('/')+1:].strip()
        if args.save_old:
            cursor.execute(('SELECT id, authority, identifier, publicationdate '
                            'FROM dvobject WHERE authority=%s and identifier=%s'),
                            (authority, identifier))
            write_old(cursor.fetchall())

        reqdate = fetch_date_api(args.url, args.key, pid, parse_dtype(args.date))
        if not reqdate:
            print(f'Date type {parse_dtype(args.date)} not found in {pid}; skipping')
            continue
        dtime, cleandate = get_datetime(reqdate)

        outstr = ('UPDATE dvobject\n'
                  f"SET publicationdate=TO_TIMESTAMP('{cleandate}', 'YYYY-MM-DD')\n"
                  f'WHERE authority={authority} AND identifier={identifier};\n')

        if args.dry_run:
            print(outstr)
            continue

        if args.sql_only:
            write_sql(outstr)
            continue

        #TO_TIMESTAMP is handled by pyscopg2 by passing a datetime
        cursor.execute(('UPDATE dvobject SET publicationdate=%s '
                        'WHERE authority=%s AND identifier=%s;'),
                        (dtime, authority, identifier))
        conn.commit()
        print(reindex(pid))

if __name__ == '__main__':
    main()
