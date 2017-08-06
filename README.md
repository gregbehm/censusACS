# US Census American Community Survey data table builder

*"The U.S. Census Bureau's American Community Survey (ACS) is an ongoing survey that provides vital information on a yearly basis about our nation and its people. Information from the survey generates data that help determine how more than $400 billion in federal and state funds are distributed each year."*  
-- [https://www.census.gov/programs-surveys/acs/about.html]

Data from the ACS are published annually, aggregated as 1-year, 3-year, and 5-year estimates. Data from the survey are released at various geographical levels, the most detailed of which is the Census Block Group, a statistical division of the census tract, typically containing between 600 and 3,000 people.

Only the ACS 5-year estimates are published for Block Groups, which implies the 5-year data give the most detailed geographical resolution for demographic analysis.

ACS data tables are accessible in various ways, including the browser-based American FactFinder tool, FTP, and recently-introduced APIs.

The most comprehensive ACS data are contained in the ACS Summary File, a set of comma-delimited text files that contain all of the detailed tables for the ACS.

See the online *Guidance for Data Users* at https://www.census.gov/programs-surveys/acs/guidance.html for more information. 

**This project accesses and processes the ACS Summary File into detailed subject tables, according to the user's request for Year, State, and Detailed Table names.**

The document *How To construct ACS tables from Summary Files.docx* included with this repo provides explanation for constructing detailed tables from the ACS Summary File.

**The following excerpt from** *How To construct ACS tables from Summary Files.docx* **illustrates the logical flow of the censusACS.py python code.** 

#### Step-by-step example for creating Table B01002, “Median Age By Sex,” for all Colorado Census Block Groups.
1.	From Appendix A in file ACS_2015_SF_5YR_Appendices.xls, find the row containing table B01002 in the “Table Number” column. 
Note: Occasionally, but rarely, a table spans multiple sequence files, so be sure to look for all rows for a given table number.
2.	Record the row information found in Step #1 — Table Number (B01002), Table Title (Median Age By Sex), Geography Restrictions (none), Summary File Sequence Number (0003), Summary File Starting and Ending Positions (100-102) — for later use.
3.	From geography file g20155co.csv in Summary File Colorado_Tracts_Block_Groups_Only.zip, filter for and save the 3,532 rows containing Block Group summary level value (150) in the third column.
4.	From the geography file template 2015_SFGeoFileTemplate.xls in 2015_5yr_Summary_FileTemplates.zip, use Row #2 for the descriptive column names to associate with the geo data collected in Step #3 above.
5.	Using the “Logical Record Number” and “Geographic Identifier” columns for the block group data from Step #3, form a new table with these columns only.
6.	Referencing the Summary File Sequence Number 0003 from Step #2, open files e20155co0003000.txt and m20155co0003000.txt from the Summary File archive Colorado_Tracts_Block_Groups_Only.zip.
7.	Use the logical record numbers from the table constructed in Step #5 to locate the corresponding rows (matching column 6) in the estimate and margins files opened in Step #6.
8.	For each row in the estimate and margins files, obtain survey data values from the columns between the Summary File Starting and Ending Positions (inclusive) obtained from Appendix A in Step #2.
9.	Use the appropriate template file (e.g. Seq3.xls) from file 2015_5yr_Summary_FileTemplates.zip to get descriptive column names to associate with the survey data collected in Step #8.
10.	Merge by Logical Record Number the tables created in Step #5 and Step #9, then form a final output table by retaining only the Geographic Identifier column, estimate columns, and margin-of-error columns.
11.	Save the output table to a CSV file or database.