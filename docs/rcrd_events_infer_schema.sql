--File format to parse the Example file
CREATE OR REPLACE FILE FORMAT rcrd_events_infer_schema
TYPE = CSV

FIELD_DELIMITER = ','
PARSE_HEADER = TRUE
FIELD_OPTIONALLY_ENCLOSED_BY = '"';