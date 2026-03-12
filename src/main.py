import os

from dotenv import load_dotenv
from os import getenv

import utils.snowflake_ncl as sf

#Load environment variables
load_dotenv(override=True)

#Dictionary for destination table comments
destination_table_descriptions = {
    "Inc": "Monthly volumes of National, ICB, and Cancer alliance new cancer diagnoses (observed & working day adjusted). Demographic breakdowns by Age-group, Deprivation, Ethnicity, Gender, Route to Diagnosis, Stage at diagnosis.",
    "Inc_Trt": "Monthly volumes of National, ICB, and Cancer alliance new cancer diagnoses and Tumour resections (observed & working day adjusted). Includes proportions recorded with Early stage, Radiotherapy, SACT, and Tumour resections. Demographic breakdowns by Age-group, Deprivation, Ethnicity, Gender, Route to Diagnosis, Stage at diagnosis",
    "Stage": "Monthly volumes and proportions of National, ICB, and Cancer alliance with recorded Early stage. Demographic breakdowns by Age-group, Deprivation, Ethnicity, Gender, Route to Diagnosis.",
    "SurgAct": "Monthly volumes of National, ICB, and Cancer alliance Tumour resections (observed & working day adjusted). Demographic breakdowns by Age-group, Deprivation, Ethnicity, Gender, Route to Diagnosis.",
    "Trt": "Monthly volumes and proportions of National, ICB, and Cancer alliance with recorded Radiotherapy, SACT, and Tumour resections. Demographic breakdowns by Age-group, Deprivation, Ethnicity, Gender, Route to Diagnosis, Stage at diagnosis.",
    "Inc_Trt_CA": "Monthly volumes of ICB, Cancer alliance, and Provider new cancer diagnoses and Tumour resections (observed & working day adjusted). Includes proportions recorded with Early stage, Radiotherapy, SACT, and Tumour resections. Demographic breakdowns by Age-group, Deprivation, Ethnicity, Gender, Route to Diagnosis, Stage at diagnosis.",
    "else": "RCRD Event data."
}

def get_stage_files(stage_name):
    """
    Get a list of existing csv files in the target stage.
    Args:
        stage_name: Name of the stage
    Returns:
        list(str): List of csv files in the stage.
    """

    ctx = sf.create_connection(
        account=getenv("SNOWFLAKE_ACCOUNT"),
        user=getenv("SNOWFLAKE_USER"),
        role=getenv("SNOWFLAKE_ROLE"),
        warehouse=getenv("SNOWFLAKE_WAREHOUSE"),
        database=getenv("DATABASE"),
        schema=getenv("SCHEMA")
    )

    #Get metadata on stage
    res = sf.execute_sql(ctx, f"LIST @{stage_name}", sfw=True)

    #Extract csv filename from each metadata result
    staged_files = [x[0].split("/")[1] for x in res]
    
    return staged_files

def get_files(data_dir, file_ext=""):
    """
    Get a list of data files at the listed data_dir location.
    Args:
        data_dir: Path to data files
        file_ext (optional): Limit data files to a specific extension
    Returns:
        list(str): List of file names
    """
    dir_list = [x for x in os.listdir(data_dir) if x.endswith(file_ext)]

    #Cleanse the list
    if dir_list == []:
        e_message = f"No files were found in {data_dir}" 
        raise Exception(e_message)

    return dir_list

def get_onedrive_dir():
    #Get username
    od_dir = f"C:/Users/{os.getlogin()}/{getenv("NHS_ONEDRIVE_DIR")}/"

    if not(os.path.exists(od_dir)):
        raise Exception("OneDrive cannot be found on your machine:\n\t" + od_dir)
    
    return od_dir

def categorise_files(files):

    """
    Group a list of files into national, cancer_alliance, or other.
    Args:
        files: List of files
    Returns:
        dict: Dictionary containing a list of files for each category
    """

    #Define categories
    files_sorted = {
        "national": [],
        "cas": [],
        "example": [],
        "other": []
    }

    #Categorise each file individually
    for file_name in files:

        flag__rcrd_file = file_name.startswith("RCRD_")
        flag__national_file = "_Eng_" in file_name
        flag__ingest_all = getenv("INGEST_ALL_NATIONAL_FILES")=="True"
        flag__national_inc_trt = "_Inc_Trt_" in file_name
        flag__example_file = file_name.startswith("Example_")

        if flag__rcrd_file and flag__national_file:
            if flag__ingest_all or flag__national_inc_trt:
                files_sorted["national"].append(file_name)

        elif flag__rcrd_file:
            files_sorted["cas"].append(file_name)

        elif flag__example_file:
            files_sorted["example"].append(file_name)
        
        else:
            files_sorted["other"].append(file_name)

    return files_sorted

def ingest_file_group(
        data_dir, 
        files, 
        destination_stage, 
        overwrite=False, 
        warning=False):

    """
    Ingestion handler for a file group (national or cancer alliance files).
    Args:
        data_dir: Directory of the files
        files: List of files in the file group
        destination_stage: Name of the stage to ingest the files to
        overwrite: When True replaces existing file with the same name
        warning: When True, the terminal will warn you when a file already exists
    """

    existing_files = get_stage_files(destination_stage)
    #Remove ".gz" from file suffix in the staged files (so they end in .csv)
    existing_csv_files = [x[:-3] for x in existing_files]

    for file_name in files:
        if file_name in existing_csv_files and overwrite == False:
            if warning:
                print(
                    f"{file_name} already exists in staging.", 
                    "Set INGESTION_OVERWRITE to 'True' in the .env file if you want to overwrite existing files."
                )
            continue

        print(f"Uploading {file_name}...")
        sf.stage_file(
            file_path=data_dir + file_name, 
            destination_stage=destination_stage,
            connection_name=getenv("SFCLI_CONNECTION_NAME"),
            overwrite=overwrite
        )

def ingestion(overwrite=False, warning=False):
    """
    Ingestion handler for all files.
    Args:
        overwrite: When True replaces existing file with the same name
        warning: When True, the terminal will warn you when a file already exists
    """

    data_dir = get_onedrive_dir() + getenv("DATA_SHAREPOINT_DIR") + "/"

    files = get_files(data_dir, file_ext="csv")
    files_sorted = categorise_files(files)

    #Example File (for deriving the schema of the other tables)
    ingest_file_group(
        data_dir, 
        files=files_sorted["example"], 
        destination_stage=getenv("STAGE_NAME_EXAMPLE"), 
        overwrite=overwrite,
        warning=warning
    )

    #National Files
    ingest_file_group(
        data_dir, 
        files=files_sorted["national"], 
        destination_stage=getenv("STAGE_NAME_NATIONAL"), 
        overwrite=overwrite,
        warning=warning
    )

    #Cancer Alliance Files
    ingest_file_group(
        data_dir, 
        files=files_sorted["cas"], 
        destination_stage=getenv("STAGE_NAME_CA"), 
        overwrite=overwrite,
        warning=warning
    )

def target_example_file_for_schema():
    """
    Pulls the Example file (containing dummy data) to derive the schema.
    Code assumes there is only 1 Example file in the stage
    Returns:
        str: Location of the example file in the Example stage
    """
    staged_files = get_stage_files(getenv("STAGE_NAME_EXAMPLE"))
    return "@" + getenv("STAGE_NAME_EXAMPLE") + "/" + staged_files[0]

def create_rcrd_table(
        ctx,
        schema_file,
        destination_table_name,
        metric_id
):
    """
    Function to create a destination RCRD_EVENTS table.
    Uses the Example file for reference.
    Args:
        ctx: Snowflake connection object
        schema_file: Location of the example file to derive the schema
        destination_table_name: Table name to create
        metric_id: ID of the metric to load the relevant table description
    """
    
    #Get table description from global dictionary
    global destination_table_descriptions

    if metric_id in destination_table_descriptions.keys():
        table_desc_body = destination_table_descriptions[metric_id]
    else:
        table_desc_body = destination_table_descriptions["else"]

    table_desc_source = "Source: https://digital.nhs.uk/ndrs/data/data-sets/rcrd"
    table_desc_contact = "Contact: " + getenv("SNOWFLAKE_USER")

    table_desc_full = table_desc_body + "\n" + table_desc_source + "\n" + table_desc_contact

    #derive schema of data and recreate the table
    query_derive_schema = f"""
        CREATE OR REPLACE TABLE {destination_table_name.upper()}
        COMMENT = '{table_desc_full}'
        USING TEMPLATE (
            SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
            FROM TABLE(
                INFER_SCHEMA(
                    LOCATION=> '{schema_file}',
                    FILE_FORMAT=> '{getenv("FILE_FORMAT_INFER_SCHEMA")}'
                )
            )
        );
    """

    sf.execute_sql(ctx, query_derive_schema)

def stage_to_table(ctx, schema_file, stage_name, group):
    """
    Move the latest data in a stage into tables.
    Args:
        ctx: Snowflake connection object
        schema_file: Location of the example file to derive the schema
        stage_name: Name of the stage to process
        group: Either "national" or "cas" so they be handled differently  
    """
    #Get all files in the stage
    staged_files = get_stage_files(stage_name)

    #For national files, only allow all files if set in the .env
    if group == "national" and getenv("INGEST_ALL_NATIONAL_FILES") != "True":
        staged_files = [x for x in staged_files if "_Inc_Trt_" in x]

    #Read the date element of the filename to get the latest file date
    latest_period = max(
        [
            x.split(".csv")[0][-4:] 
            for x 
            in staged_files 
            if x.split(".csv")[0][-4:].isnumeric()
        ]
    )

    #Get all files with the latest date
    target_files = [x for x in staged_files if latest_period + ".csv" in x]

    #For cas (Cancer Alliance files), create 1 table used by all files
    if group == "cas":

        destination_table_name = getenv("TABLE_NAME_CA")

        create_rcrd_table(
            ctx, 
            schema_file=schema_file,
            destination_table_name=destination_table_name,
            metric_id = "Inc_Trt_CA"
        )

    for file_name in target_files:

        print("Loading", file_name + "...")

        #For national (National files), create 1 table per file
        if group == "national":
            #Table metadata
            destination_table_name = "NATIONAL__" + file_name.split("_Eng_")[0]
        
            create_rcrd_table(
                ctx, 
                schema_file=schema_file,
                destination_table_name=destination_table_name,
                metric_id = destination_table_name.split("RCRD_")[1]
            )

        #Load the staged data
        file_location = "@" + stage_name + "/" + file_name

        query_load_staged_data = f"""
            COPY INTO {destination_table_name.upper()}
            FROM {file_location}
            FILE_FORMAT = {getenv("FILE_FORMAT_LOAD_STAGE_DATA")};        
        """

        sf.execute_sql(ctx, query_load_staged_data)

#Ingest the latest available data
ingestion(overwrite=getenv("INGESTION_OVERWRITE")=="True", warning=False)

#Process the example file
example_file = target_example_file_for_schema()

ctx = sf.create_connection(
        account=getenv("SNOWFLAKE_ACCOUNT"),
        user=getenv("SNOWFLAKE_USER"),
        role=getenv("SNOWFLAKE_ROLE"),
        warehouse=getenv("SNOWFLAKE_WAREHOUSE"),
        database=getenv("DATABASE"),
        schema=getenv("SCHEMA")
    )

#Stage the National data
stage_to_table(
    ctx, 
    example_file, 
    stage_name=getenv("STAGE_NAME_NATIONAL"), 
    group="national"
)

#Stage the Cancer Alliance data
stage_to_table(
    ctx, 
    example_file, 
    stage_name=getenv("STAGE_NAME_CA"), 
    group="cas"
)