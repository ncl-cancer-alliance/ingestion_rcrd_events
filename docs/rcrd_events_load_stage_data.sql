--File format to ingest the data files
CREATE OR REPLACE FILE FORMAT rcrd_events_load_stage_data
TYPE = CSV

FIELD_DELIMITER = ','
SKIP_HEADER = 1
FIELD_OPTIONALLY_ENCLOSED_BY = '"';