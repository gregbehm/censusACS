"""
Generate Detailed Tables from the US Census ACS 5-Year Summary Files
"""

import argparse
import json
import os
import pandas as pd
import requests
import sys
import zipfile


# Define helper functions

def stderr_print(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr, flush=True)


def get_config(config=None):
    """
    Create and return configuration dictionary, either read
    in from config.json, or default. 
    """

    try:
        with open(config) as fp:
            data = json.load(fp)
            cfg = {
                'year': data.get('year', '2015'),
                'states': data.get('states', ['Colorado']),
                'tables': data.get('tables', [])
            }
    except:
        # Default config dictionary
        cfg = {
            'year': '2015',
            'states': ['Colorado'],
            'tables': []
        }

    return cfg


def request_file(url):
    """
    requests.get with status check
    """
    try:
        response = requests.get(url, timeout=3.333)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        stderr_print(f'Error: Download from {url} failed. Reason: {e}')
        return None


def read_from_csv(file, names):
    """
    Customized call to pandas.read_csv for reading header-less summary files.
    """
    return pd.read_csv(file, encoding='ISO-8859-1', names=names,
                       header=None, na_values=['.', -1], dtype=str)


def read_summary_file(file, names):
    """
    Read summary estimates/margins file and return a massaged DataFrame
    ready for data extraction.
    """
    df = read_from_csv(file, names=names)
    return df.rename(columns={'SEQUENCE': 'seq', 'LOGRECNO': 'Logical Record Number'})


def get_appendix_data(df, table):
    """
    Given Appendix A DataFrame df and table name,
    return Sequence, Start, and End numbers as lists.
    """
    df = df[df['name'] == table]
    return df['seq'].tolist(), df['start'].tolist(), df['end'].tolist()


def get_by_summary_level(df, summary_level):
    """
    Given Geography file DataFrame df, return a subset DataFrame,
    filtered by Census geographic summary level.
    """
    return df[df['Summary Level'] == summary_level]


def get_templates(templates_zip_archive):
    """
    Unzip the Summary File Templates archive file; generate and
    return a dictionary mapping 'geo' and seq # to corresponding
    file column name lists.
    """
    templates = dict()
    with zipfile.ZipFile(templates_zip_archive) as z:
        # Loop through all files in archive namelist
        for name in z.namelist():
            if 'Seq' in name:
                # Generate 4-digit sequence number string
                index = name.index('Seq')
                # Drop 'Seq' and separate sequence number from file extension
                s = name[index + 3:].split('.')[0]
                # Generate number string
                key = s.zfill(4)
            elif 'Geo' in name:
                key = 'geo'
            else:
                # skip directories or other files
                continue
            with z.open(name) as f:
                df = pd.read_excel(f)
                # Extract column names from data row 0
                templates[key] = df.loc[0].tolist()
    return templates


def get_logical_records(fp, names, summary_level):
    """
    Given a CSV geo file object fp, column-names list names,
    and geo summary level value, return a DataFrame of GEO IDS
    and Logical Record Numbers from the geo file, filtered by
    the geographic summary level.
    """
    gdf = read_from_csv(fp, names=names)
    summary_geo = get_by_summary_level(gdf, summary_level)
    return summary_geo[['Geographic Identifier', 'Logical Record Number']]


def progress_report(fraction):
    # Print the current progress, given as a fraction, as a percentage.
    print(f'\rProgress: {100*fraction:.0f}% ', end='')


def main(config=None):
    # Read config.json or default variables
    cfg = get_config(config)

    # ACS release year
    year = cfg['year']

    # Make data directories, if necessary
    sourcedir = os.path.join(os.getcwd(), 'ACS_data_' + year)
    try:
        os.mkdir(sourcedir)
    except FileExistsError:
        pass

    outdir = os.path.join(sourcedir, 'ACS_tables')
    try:
        os.mkdir(outdir)
    except FileExistsError:
        pass

    # Assign variables

    summary_level = '150'  # Block Group summary level
    summary_file_suffix = '_Tracts_Block_Groups_Only.zip'
    appendix_file = 'ACS_' + year + '_SF_5YR_Appendices.xls'
    templates_file = year + '_5yr_Summary_FileTemplates.zip'

    acs_base_url = 'https://www2.census.gov/programs-surveys/acs/summary_file/' + year
    by_state_base_url = acs_base_url + '/data/5_year_by_state/'

    # Note: The summary files (e.g. 5-year by state) are multi-MB files
    states = cfg['states']
    state_urls = [by_state_base_url + state + summary_file_suffix for state in states]

    urls = [acs_base_url + '/documentation/tech_docs/' + appendix_file,
            acs_base_url + '/data/' + templates_file,
            ] + state_urls

    # Download files, as necessary
    for url in urls:
        basename, filename = os.path.split(url)
        pathname = os.path.join(sourcedir, filename)
        if not os.path.exists(pathname):
            print(f'Requesting file {url}')
            response = request_file(url)
            if response:
                try:
                    with open(pathname, 'wb') as w:
                        w.write(response.content)
                        print(f'File {pathname} downloaded successfully')
                except OSError as e:
                    stderr_print(f'Error {e}: File write on {pathname} failed')

    # Read ACS 5-year Appendix A for Table sequence numbers, start/end records
    pathname = os.path.join(sourcedir, appendix_file)
    with open(pathname, 'rb') as r:
        appx_A = pd.read_excel(r, converters={'Summary File Sequence Number': str})
        appx_A.columns = ['name', 'title', 'restr', 'seq', 'start_end']
        try:
            appx_A['start'], appx_A['end'] = appx_A['start_end'].str.split('-', 1).str
            appx_A['start'] = pd.to_numeric(appx_A['start'])
            appx_A['end'] = pd.to_numeric(appx_A['end'])
        except ValueError as e:
            stderr_print(f'{e}')
            stderr_print(f'{e}')
            stderr_print(f'File {pathname} is corrupt or has invalid format')
            raise SystemExit(f'Exiting {__file__}')

    # Create Tables list
    tables = appx_A.drop(['restr', 'seq', 'start_end', 'start', 'end'], axis=1)
    pathname = os.path.join(outdir, 'ACS All Tables.csv')
    # Save table Names and Titles to CSV.
    tables.to_csv(pathname, index=False)
    # Now check for limited table list from input config file.
    all_tables = cfg['tables'] if cfg['tables'] else tables['name'].tolist()

    # Create the templates dictionary
    pathname = os.path.join(sourcedir, templates_file)
    templates = get_templates(pathname)

    # For each state and table name, generate output table
    for state in states:
        print(f'Building tables for {state}')
        # Unzip and open the summary files
        pathname = os.path.join(sourcedir, state + summary_file_suffix)
        try:
            with zipfile.ZipFile(pathname) as z:
                # Get Geography CSV file name
                geofile = [f for f in z.namelist()
                           if f.startswith('g') and f.endswith('csv')
                           ][0]
                # Open and read the Geography file
                try:
                    with z.open(geofile) as g:
                        # Get Geo IDs and Logical Record Numbers for this Summary Level
                        logi_recs = get_logical_records(g, templates['geo'], summary_level)
                except OSError as e:
                    stderr_print(f'Geofile error for {state}')
                    stderr_print(f'{e}')
                    continue

                # Get Estimate file names
                e = [f for f in z.namelist() if f.startswith('e')]
                # Pull sequence number from file name positions 8-11; use as dict key
                efiles = {f[8:12]: f for f in e}
                # Get Margin-of-Error file names
                m = [f for f in z.namelist() if f.startswith('m')]
                # Pull sequence number from file name positions 8-11; use as dict key
                mfiles = {f[8:12]: f for f in m}
                built = 0
                # Process all tables
                for n, table in enumerate(all_tables):
                    sequence_data = []
                    # For this table, get file sequence numbers, start/end record numbers
                    seqs, starts, ends = get_appendix_data(appx_A, table)
                    for seq, start, end in zip(seqs, starts, ends):
                        # Get summary and margin file, based on sequence number
                        template = templates[seq]
                        try:
                            efile = efiles[seq]
                            with z.open(efile) as e:
                                edf = read_summary_file(e, names=template)
                        except OSError as e:
                            stderr_print(f'Estimates file {efile} error for {state}')
                            stderr_print(f'{e}')
                            break

                        try:
                            mfile = mfiles[seq]
                            with z.open(mfile) as m:
                                mdf = read_summary_file(m, names=template)
                        except OSError as e:
                            stderr_print(f'Margins file {mfile} error for {state}')
                            stderr_print(f'{e}')
                            break

                        # Merge the estimates and margins with the logical records
                        edf = edf.merge(logi_recs).set_index('Geographic Identifier')
                        mdf = mdf.merge(logi_recs).set_index('Geographic Identifier')
                        # Keep only data columns
                        use_col_nums = list(range(start - 1, end))
                        edf = edf.iloc[:, use_col_nums]
                        mdf = mdf.iloc[:, use_col_nums]
                        # Prepend E/M to column names for Estimates/Margins-of-Error
                        edf.columns = ['E: ' + col for col in edf.columns]
                        mdf.columns = ['M: ' + col for col in mdf.columns]
                        # Join DataFrames
                        df = pd.concat([edf, mdf], axis=1)
                        # Interleave Estimate and Margin-of-Error columns
                        new_columns = [None] * (len(edf.columns) + len(mdf.columns))
                        new_columns[::2] = edf.columns
                        new_columns[1::2] = mdf.columns
                        # Reorder columns using interleaved labels
                        df = df[new_columns]
                        # Save DataFrame to list
                        sequence_data.append(df)

                    # Guard rail against file errors above
                    if sequence_data:

                        # Concatenate multiple data frames column-wise
                        df = pd.concat(sequence_data, axis=1)

                        # Reset 'Geographic Identifier' from index to column
                        df.reset_index(inplace=True)

                        # Save non-empty table as CSV
                        if not df.drop('Geographic Identifier', axis=1).dropna().empty:
                            # Conform Geo ID w/ GEOID in Census Block Group shapefiles
                            df = df.rename(columns={'Geographic Identifier': 'GEOID'})
                            # Strip GEOID to last 12 characters
                            df['GEOID'] = df['GEOID'].apply(lambda x: x[-12:])
                            pathname = os.path.join(outdir, state + table + '.csv')
                            df.to_csv(pathname, index=False)
                            built += 1

                    # Print progress percentage
                    progress_report(n / len(all_tables))

                print(f'\n{state} tables: saved {built}, dropped {n - built} empty')

        except OSError as e:
            stderr_print(f'Sumary file error for {pathname}')
            stderr_print(f'{e}')
            continue


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate US Census ACS Detailed Tables")
    parser.add_argument("-c", "--config")
    args = parser.parse_args()
    main(args.config)
