# ## Generate Detailed Tables from the US Census ACS 5-Year Summary Files

import argparse
import json
import os
import pandas as pd
import requests
import sys
import zipfile


# Define helper functions

def get_config(config=None):
    """
    Create and return configuration dictionary, either read
    in from config.json, or default. 
    """

    try:
        with open(config, 'r') as fp:
            data = json.load(fp)
            cfg = {'year': data.get('year', '2015'),
                   'summary_level': data.get('summary_level', '150'),  # Block Group summary level: 150
                   'states': data.get('states', {'Colorado': 'co'}),
                   'tables': data.get('tables', [])
                   }
    except:
        # Default config dictionary
        cfg = {'year': '2015',
               'summary_level': '150',  # Block Group summary level: 150
               'states': {'Colorado': 'co'},
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
        print(f'Error: Download from {url} failed. Reason: {e}')
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
                index = name.find('Seq')
                # Separate sequence from filename extension
                a = name[index:].split('.')[0]
                # Drop 'Seq' and generate number string
                key = a.replace('Seq', '').zfill(4)
            elif 'Geo' in name:
                key = 'geo'
            else:
                # skip directory names
                continue
            with z.open(name) as f:
                df = pd.read_excel(f)
                # Extract column names from Row 0
                templates[key] = df.loc[0].tolist()
    return templates


def main(config=None):
    # Read config.json or default variables
    cfg = get_config(config)

    # ACS release year
    year = cfg['year']

    # Define Census Summary Level info.
    summary_level = cfg['summary_level']
    summary_file_suffix = '_Tracts_Block_Groups_Only.zip'

    sourcedir = os.path.join(os.getcwd(), 'ACS_data_' + year)
    if not os.path.exists(sourcedir):
        os.mkdir(sourcedir)

    appendix_file = 'ACS_' + year + '_SF_5YR_Appendices.xls'
    templates_file = year + '_5yr_Summary_FileTemplates.zip'

    outdir = os.path.join(sourcedir, 'ACS_tables')
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    # Note: The summary files (e.g. 5-year by state) are multi-MB files
    states = cfg['states']

    # Download files, as necessary

    acs_base_url = 'https://www2.census.gov/programs-surveys/acs/summary_file/' + year
    by_state_base_url = acs_base_url + '/data/5_year_by_state/'

    state_urls = [by_state_base_url + state + summary_file_suffix for state in states]

    urls = [acs_base_url + '/documentation/tech_docs/' + appendix_file,
            acs_base_url + '/data/' + templates_file,
            ] + state_urls

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
                except:
                    print(f'Error: File write on {pathname} failed')

    # Read ACS 5-year Appendix A for Table sequence numbers, start/end records

    pathname = os.path.join(sourcedir, appendix_file)
    with open(pathname, 'rb') as r:
        appendix_A = pd.read_excel(r, converters={'Summary File Sequence Number': str})
        appendix_A.columns = ['name', 'title', 'restr', 'seq', 'start_end']
        # Validate that Sequence and Start-End columns contain no NaN entries.
        assert_msg = f'File {appendix_file} is corrupt: NaN Sequence or Start/End data retrieved.'
        assert appendix_A['seq'].isnull().sum() == 0 and appendix_A['start_end'].isnull().sum() == 0, assert_msg
        appendix_A['start'], appendix_A['end'] = appendix_A['start_end'].str.split('-', 1).str
        appendix_A['start'] = pd.to_numeric(appendix_A['start'])
        appendix_A['end'] = pd.to_numeric(appendix_A['end'])

    # Create Tables list
    tables = appendix_A.drop(['restr', 'seq', 'start_end', 'start', 'end'], axis=1)
    pathname = os.path.join(outdir, 'ACS All Tables.csv')
    # Save table Names and Titles to CSV.
    tables.to_csv(pathname, index=False)
    # Now check for limited table list from input config file.
    all_tables = cfg['tables'] if cfg['tables'] else tables['name'].tolist()

    # Create templates dictionary
    pathname = os.path.join(sourcedir, templates_file)
    templates = get_templates(pathname)

    # For each state and table name, generate output table
    for state, state_code in states.items():
        print(f'Building tables for {state}')
        # Unzip and open the summary files
        filename = os.path.join(sourcedir, state + summary_file_suffix)
        with zipfile.ZipFile(filename) as z:
            # Get Estimate file names
            e = [f for f in z.namelist() if f.startswith('e')]
            # Pull sequence number from positions 8-11; use as dict key
            efiles = {f[8:12]: f for f in e}
            # Get Margin-of-Error file names
            m = [f for f in z.namelist() if f.startswith('m')]
            # Pull sequence number from positions 8-11; use as dict key
            mfiles = {f[8:12]: f for f in m}
            # Get Geography file name
            geofile = [f for f in z.namelist() if f.startswith('g') and f.endswith('csv')][0]
            # Open and read the Geography file
            with z.open(geofile) as g:

                # Get Geo IDs and Logical Record Numbers for this Summary Level
                gdf = read_from_csv(g, names=templates['geo'])
                summary_geo = get_by_summary_level(gdf, summary_level)
                logical_recs = summary_geo[['Geographic Identifier', 'Logical Record Number']]

                built, empty = 0, 0
                # Process all tables
                for table in all_tables:
                    sequence_data = []
                    # For this table, get file sequence numbers, start/end record numbers
                    seqs, starts, ends = get_appendix_data(appendix_A, table)
                    for seq, start, end in zip(seqs, starts, ends):
                        # Get summary and margin file, based on sequence number
                        efile = efiles[seq]
                        mfile = mfiles[seq]
                        with z.open(efile) as e:
                            with z.open(mfile) as m:
                                template = templates[seq]
                                edf = read_summary_file(e, names=template)
                                mdf = read_summary_file(m, names=template)
                                # Merge the estimates and margins with the logical records
                                edf = edf.merge(logical_recs).set_index('Geographic Identifier')
                                mdf = mdf.merge(logical_recs).set_index('Geographic Identifier')
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

                    # Concatenate multiple data frames column-wise
                    df = pd.concat(sequence_data, axis=1)

                    # reset_index moves 'Geographic Identifier' from index to column
                    df.reset_index(inplace=True)

                    # Save non-empty table as CSV
                    if not df.drop('Geographic Identifier', axis=1).dropna().empty:
                        built += 1
                        # Conform Geographic ID with GEOID in Census Block Group shapefiles
                        df.rename(columns={'Geographic Identifier': 'GEOID'}, inplace=True)
                        # Strip GEOID to last 12 characters
                        df['GEOID'] = df['GEOID'].apply(lambda x: x[-12:])
                        pathname = os.path.join(outdir, state + table + '.csv')
                        df.to_csv(pathname, index=False)
                        print('.', end='')
                        sys.stdout.flush()
                    else:
                        empty += 1

                print()
                print('Saved {} tables and dropped {} empty tables for {}'.format(built, empty, state))
                # for table in all_tables


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate US Census ACS Detailed Tables")
    parser.add_argument("-c", "--config")
    args = parser.parse_args()

    main(args.config)
    # main()