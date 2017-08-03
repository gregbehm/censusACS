# US Census American Community Survey data table builder

The U.S. Census Bureau's American Community Survey (ACS) is an ongoing survey that provides vital information on a yearly basis about our nation and its people. Information from the survey generates data that help determine how more than $400 billion in federal and state funds are distributed each year.

Data from the ACS are published annually, aggregated as 1-year, 3-year, and 5-year estimates. Data from the survey are released at various geographical levels, the most detailed of which is the Census Block Group, a statistical division of the census tract, typically containing between 600 and 3,000 people.

Only the ACS 5-year estimates are published for Block Groups, which implies the 5-year data give the most detailed geographical resolution for demographic analysis.

ACS data tables are accessible in various ways, including the browser-based American FactFinder tool, FTP, and recently-introduced APIs.

The most comprehensive ACS data are contained in the ACS Summary File, a set of comma-delimited text files that contain all of the detailed tables for the ACS.

See the online *Guidance for Data Users* at https://www.census.gov/programs-surveys/acs/guidance.html for more information. 

This project accesses and processes the ACS Summary File into detailed subject tables, according to the user's request for Year, State, and Detailed Table names.
