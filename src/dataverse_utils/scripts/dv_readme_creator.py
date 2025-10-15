'''
Creates a README file in either PDF or Markdown formats from a
Dataverse study. Requires a valid API key.
'''
import argparse
import pathlib
import sys
import textwrap
import dataverse_utils
import dataverse_utils.collections as c

FTYPE = 'File extension must be one of .pdf, .md or .txt (case insensitive).'

def parse() -> argparse.ArgumentParser():
    '''
    Parses the arguments from the command line.

    Returns argparse.ArgumentParser
    '''
    description = textwrap.dedent(
                   '''
                   Creates a README file from a Dataverse study,
                   in Markdown or PDF format. An API is *required* to use
                   this utility, as it must work with draft studies.
                   ''')
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-u', '--url', default='borealisdata.ca',
                        help=('Dataverse installation base url. '
                              'defaults to "borealisdata.ca"'))
    parser.add_argument('-p', '--pid',
                        help='Persistent ID of study (ie, doi or hdl)',
                        type=str,
                        required=True)
    parser.add_argument('-k', '--key', required=True,
                        help='API key', default=None)
    parser.add_argument('outfile',
                        help = f'Output file. {FTYPE}')
    parser.add_argument('-v', '--version', action='version',
                        version=dataverse_utils.script_ver_stmt(parser.prog),
                        help='Show version number and exit')
    return parser

def valid_pid(inst:str)->bool:
    '''
    Check for proper formatting of a doi/hdl
    '''
    if inst[:4] in ['doi:', 'hdl:'] and inst.count('/')==2:
        return True
    return False

def valid_outfile(infil:str)->bool:
    '''
    Ensures that it's possible to write the file
    '''
    whar = pathlib.Path(infil)
    if whar.suffix.lower() not in ['.pdf', '.md', '.txt']:
        return False
    return whar.parent.expanduser().absolute().exists()

def main():
    '''
    You know what this is
    '''
    args = parse().parse_args()

    verify = {args.pid: (valid_pid,
                         'Invalid PID. PIDs begin with hdl: or doi: '
                         'and contain two slashes ("/").'),
              args.outfile: (valid_outfile, FTYPE)}

    for k, v in verify.items():
        if not v[0](k):
            print(v[1])
            sys.exit()

    fpath = pathlib.Path(args.outfile).expanduser().absolute()
    study = c.StudyMetadata(url=args.url, pid=args.pid, key=args.key)
    study_rm = c.ReadmeCreator(study)
    if fpath.suffix.lower() == '.pdf':
        study_rm.write_pdf(str(fpath))
        sys.exit()
    study_rm.write_md(str(fpath))

if __name__ == '__main__':
    main()
