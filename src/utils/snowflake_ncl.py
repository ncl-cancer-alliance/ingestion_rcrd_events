import pandas as pd
import subprocess

import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

def create_connection(
        account, 
        user, 
        role="ANALYST", 
        warehouse="NCL_ANALYTICS_XS",
        authentication="externalbrowser",
        database="DATA_LAKE__NCL", 
        schema="ANALYST_MANAGED"
):

    """
    Creates and returns a snowflake connection object
    Args:
        account: Snowflake Account (e.g., your-org.eu-west-1 or xy12345)
        user: Snowflake Username (email)
        role: Snowflake role (default: ANALYST)
        warehouse: Warehouse to use for processing (default: NCL_ANALYSTICS_XS)
        authenication: Method of authenication (default: externalbrowser)
        database: Default database to use (default: DATA_LAKE__NCL)
        schema: Default schema to use (default: ANALYST_MANAGED)
    Returns:
        Snowflake connection object
    """
    
    return snowflake.connector.connect(
            account=account,
            user=user,
            role=role,
            warehouse=warehouse,
            authenticator=authentication,
            database=database,
            schema=schema
    )

def check_access(ctx, database, schema=False, table=False):
    """
    Check if a resource can be accessed in Snowflake using the provided connection
    Args:
        ctx: Snowflake connection object (created using ncl_snowflake.create_connection())
        database: Target database
        schema (optional): Target schema, if null then checks access to the database
        table (optional): Target table, if null then checks access to the schema
    """

    #Check the database exists in any case
    db_query = f"""
        show databases like '{database}'
    """

    db_df_res = pd.read_sql(db_query, ctx)

    #Flag if database not found
    if len(db_df_res) == 0:
        return False

    #Check if table exists
    if schema and table:
        query = f"""
            select 1
            from {database}.information_schema.tables
            where table_schema = '{schema.upper()}'
            and table_name = '{table.upper()}'
            limit 1
        """
    #Check if schema exists
    elif schema:
        query = f"""
            select 1
            from {database}.information_schema.schemata
            where schema_name = '{schema.upper()}'
            limit 1
        """
    #Check if database exists
    else:
        return True

    df_res = pd.read_sql(query, ctx)

    #Return true for schema and table check if at least 1 row found
    return len(df_res) > 0

def execute_sql(ctx, statement, sfw=False, debug=True):
    """
    Execute a given SQL statement
    Args:
        ctx: Snowflake connection object (created using ncl_snowflake.create_connection())
        statement: SQL string statement to execute
        debug (optional): If True, then on failure, the error message will be printed
    Returns:
        boolean: Returns True if the statement executes without error, False otherwise
    """

    cur = ctx.cursor()

    try:
        cur.execute(statement)
    except Exception as e:
        if debug:
            print("SQL Execution failed with this message:", e)
        
        cur.close()
        return False
    
    #Seperate handling for sfw queries
    if sfw == True:
        res = cur.fetchall()

        return res

    cur.close()
    return True

def get_user(ctx):
    """
    Function to return the active user email
    Args:
        ctx: Snowflake connection object (created using ncl_snowflake.create_connection())
    Returns:
        str: email of the current user
    """

    cur = ctx.cursor()
    cur.execute("select current_user()")
    user = cur.fetchone()[0]
    cur.close()

    return user

def create_schema(ctx, database, schema, comment=False):
    """
    Create a schema in the specified database
    Args:
        ctx: Snowflake connection object (created using ncl_snowflake.create_connection())
        database: Destination database
        schema: Destination schema
    """ 

    sql_statement = f"""
        create schema {database}.{schema}
    """

    if comment:
        sql_statement += "\n" + f"comment='{comment}'"

    execute_sql(ctx, sql_statement)

def create_table(
        ctx, 
        database, 
        schema, 
        table,
        replace=False,
        column_info=False,
        table_description=False,
        debug=False):
    """
    Create a table in the Snowflake environment
    Args:
        ctx: Snowflake connection object (created using ncl_snowflake.create_connection())
        database: Destination database
        schema: Destination schema
        table: Destination table
        replace (optional): If True then replace existing table
        column_info (optional): Either:
            Array of column names (assumes data type is string for all columns)
            Dictionary containing column information:
                - Keys: Column Names
                - "data_type": Snowflake data type for the column
                - "comment": Comment for the column
        table_description (optional): Description for the created table
        debug (optional): When True, the create table SQL statement is printed in the terminal
    """

    #Build the CREATE table query line by line
    create_table_sql = ""

    create_table_prefix = "create"
    if replace:
        create_table_prefix += " or replace"
    create_table_prefix += f" table {database}.{schema}.{table} (\n"

    create_table_sql += create_table_prefix 

    #Parse column_info to get column names and types for the new table
    if type(column_info) == dict:
        for col in column_info.keys():
            col_line = col
            if "data_type" in column_info[col]:
                col_line += "\t" + column_info[col]["data_type"]
            else:
                col_line += "\t string"

            if "comment" in column_info[col]:
                col_line += "\tcomment '" + column_info[col]["comment"] +"'"
            col_line += ",\n"

            create_table_sql += col_line

    elif type(column_info) == list:
        for col in column_info:
            create_table_sql += col + "\tstring,\n"

    #Remove the trailing , from the last row and close the column declaration
    create_table_sql = create_table_sql[:-2] + "\n"
    create_table_sql += ")\n"

    #Add table description
    if table_description:
        description_line = f"comment = '{table_description}'\n"
        create_table_sql += description_line

    if debug:
        print(create_table_sql)
    else:
        execute_sql(ctx, create_table_sql)

def upload_df(
        ctx,
        df, 
        table_name, 
        database="DATA_LAKE__NCL", 
        schema="ANALYST_MANAGED",
        replace=False,
        table_columns=False,
        table_description=False,
        debug=True
):
    """
    Upload a given dataframe to Snowflake
    Args:
        ctx: Snowflake connection object (created using ncl_snowflake.create_connection())
        df: Pandas dataframe of the data to upload
        table_name: Destination table name
        database (optional): Destination database, defaults to DATA_LAKE__NCL
        schema (optional): Destination schema, defaults to ANALYST_MANAGED
        replace (optional): If True then replace existing contents of destination, otherwise append
    Returns:
        boolean: True if the upload was successful, False otherwise
    """

    #Does the schema exist?
    if not check_access(ctx, database, schema):
        create_schema(ctx, database, schema, comment=f"Contact: {get_user(ctx)}")

    #Does the table exist?
    if not check_access(ctx, database, schema, table_name):
        
        if not(table_columns):
            raise Exception(f"Error: Table {table_name} cannot be created without provided table_columns")

        if table_description == False:
            table_description = f"Contact: {get_user(ctx)}"

        create_table(
            ctx, 
            database, 
            schema, 
            table=table_name,
            column_info=table_columns,
            table_description=table_description)

    cur = ctx.cursor()

    try:
        # Upload DataFrame
        success, nchunks, nrows, _ = write_pandas(
            conn=ctx,
            df=df,
            table_name=table_name.upper(),
            schema=schema.upper(),
            database=database.upper(),
            overwrite=replace
        )

        if not success:
            raise Exception("Failed to write DataFrame to Snowflake.")
        if debug:
            print(f"Uploaded {nrows} rows to {database}.{schema}.{table_name}")
    except Exception as e:
        success = False
        print("Data ingestion failed with error:", e)

    finally:
        cur.close()
    
    return success

def stage_file(file_path, destination_stage, connection_name="default", overwrite=False):

    """
    Stage a named file to a provided stage.
    Args:
        file_path: List of files,
        destination_stage: Name of the destination stage
        connection_name: Name of the Snowflake connection (default: "default")
    """

    cmd = [
        "snow",
        "stage",
        "copy",
        file_path,
        "@" + destination_stage + "/",
        "--connection", connection_name,
        "--parallel", "4",
        "--auto-compress",
    ]

    #Logic for if the new file should replace an existing one
    if overwrite:
        cmd.append("--overwrite")

    subprocess.run(cmd, check=True)