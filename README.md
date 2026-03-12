# Ingestion RCRD Events

Ingestion pipeline for the RCRD Events data supplied by the National Cancer Team via the NDRS data sharing - Data Extracts SharePoint page.

## Quick Start
 ```bash
# Clone and setup
git clone https://github.com/ncl-cancer-alliance/ingestion_cosd

#Setup virtual environment (venv)
python -m venv venv

#Enable virutal environment (venv)
Set-ExecutionPolicy Unrestricted -Scope Process;  venv\Scripts\activate

#Install the project packages to the virtual environment
pip install ./requirements.txt -r

#Manually install the snowflake-connector-python package (this prevents having to authenticate via the Snowflake browser multiple times)
pip install snowflake-connector-python[secure-local-storage]
```

To use this code, you will need to add the **NDRS data sharing - Data Extracts** SharePoint page as a shortcut in your personal OneDrive account and will need to be able to access files via this on your machine. ([Guide](https://support.microsoft.com/en-us/office/add-shortcuts-to-shared-folders-in-onedrive-d66b1347-99b7-4470-9360-ffc048d35a33)).

The expected path to the data files is (where the bold fields are set in the .env file): `C:\Users\$USERNAME$\OneDrive - NHS\NDRS data sharing - Data_Extracts\` but this can be altered in the .env file to pull data from other locations.

You will also need to set up a Snowflake Connection via Snowflake CLI to run the Snowflake CLI commands within the main.py script. The process for setting this up is outlined here (it is recommended you name the connection source "conn_rcrd_events" otherwise you will need to update your .env file with the name you chose): [Internal Scripting Guide](https://nhs.sharepoint.com/:w:/r/sites/msteams_38dd8f/Shared%20Documents/Document%20Library/Documents/Git%20Integration/Internal%20Scripting%20Guide.docx?d=wc124f806fcd8401b8d8e051ce9daab87&csf=1&web=1&e=qt05xI)

## Snowflake Setup
The tables themselves are automatically created on ingestion but the following resources need to be made in Snowflake ahead of running the code:
* The schema used to hold the destination tables, stages, and file formats
* 3 Stages (as configured in the .env file, can be created on the Snowflake website):
    * STAGE_NAME_EXAMPLE - Stage for the Example file
    * STAGE_NAME_NATIONAL - Stage for the National files
    * STAGE_NAME_CA - Stage for the Cancer Alliance files
* 2 File formats (that inform Snowflake how to parse the data files):
    * FILE_FORMAT_INFER_SCHEMA - See docs/rcrd_events_infer_schema.sql
    * FILE_FORMAT_LOAD_STAGE_DATA - See docs/rcrd_events_load_stage_data.sql

## What This Project Does
This code ingests the latest data files in the NDRS data sharing - Data_Extracts location by staging them in Snowflake and then creating the RCRD Events tables using the staged files. By default, this code only ingests the Inc_Trt files (both the national and Cancer Alliance specific ones) but can be configured in the .env file to ingest all files.

The destination table schema is currently: `DATA_LAKE__NCL.CANCER__RCRD_EVENTS`

## Usage
### Process
* Complete the Quick Start process above before running for the first time
* Enable the venv and configure the .env (see below) file accordingly
* Run the src/main.py script (this can take upto 20 minutes due to the large size of the files).

### .env Configurations
The sample.env contains suggested values for the non-credential based settings.
* Snowflake account settings:
    * SNOWFLAKE_ACCOUNT - The "Account identifier" as seen in the Account Details page on the Snowflake website
    * SNOWFLAKE_USER - Your email address
    * SNOWFLAKE_ROLE - At least "ENGINEER" is required for this code
    * SNOWFLAKE_WAREHOUSE - The warehouse to use for processing on the Snowflake client side
* Directory settings:
    * NHS_ONEDRIVE_DIR - How your OneDrive directory appears in your file explorer, typically "OneDrive - NHS"
    * DATA_SHAREPOINT_DIR - Path between the OneDrive root folder and the data files
* Destination settings:
    * SFCLI_CONNECTION_NAME - Name of the Snowflake CLI connection created as detailed in the Internal Scripting Guide
    * DATABASE - Snowflake database to store the data
    * SCHEMA - Snowflake schema to store the data
    * TABLE_NAME_CA - Table name for the Cancer Alliance data
    * STAGE_NAME_* - Stage names as detailed above
    * FILE_FORMAT_* - File formats as detailed above
* Runtime settings:
    * INGESTION_OVERWRITE - When set to True, files that already exist in the stage will be reuploaded
    * INGEST_ALL_NATIONAL_FILES - When set to True, all national files are ingested, otherwise only the Inc_Trt data file is

## Scripting Guidance

Please refer to the Internal Scripting Guide documentation for instructions on setting up coding projects including virtual environments (venv).

The Internal Scripting Guide is available here: [Internal Scripting Guide](https://nhs.sharepoint.com/:w:/r/sites/msteams_38dd8f/Shared%20Documents/Document%20Library/Documents/Git%20Integration/Internal%20Scripting%20Guide.docx?d=wc124f806fcd8401b8d8e051ce9daab87&csf=1&web=1&e=qt05xI)

## Changelog

### [1.0.0] - 2026-03-12
#### Added
- Initial release of the code


## Licence
This repository is dual licensed under the [Open Government v3]([https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) & MIT. All code can outputs are subject to Crown Copyright.

## Contact
Jake Kealey - jake.kealey@nhs.net

*The contents and structure of this template were largely based on the template used by the NCL ICB Analytics team available here: [NCL ICB Project Template](https://github.com/ncl-icb-analytics/ncl_project)*