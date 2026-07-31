WITH source AS (
    SELECT *
    FROM {{ source('raw_311', 'service_requests') }}
)
-- Prevents duplicated keys that bypassed ingestion by keeping the most recently created date per key.
, most_recent_id AS (
    SELECT *
        , ROW_NUMBER() OVER (
            PARTITION BY unique_key
            ORDER BY created_date DESC
        ) AS rn
    FROM source 
)
, deduplicated AS (
    SELECT *
    FROM most_recent_id
    WHERE rn = 1
)
, renamed_and_cast AS (
    SELECT CAST(unique_key AS VARCHAR) AS unique_key
        , CAST(created_date AS TIMESTAMP) AS created_date
        , CAST(closed_date AS TIMESTAMP) AS closed_date
        , CAST(agency AS VARCHAR) AS agency
        , CAST(agency_name AS VARCHAR) AS agency_name
        , CAST(complaint_type AS VARCHAR) AS complaint_type
        , CAST(descriptor AS VARCHAR) AS descriptor
        , CAST(location_type AS VARCHAR) AS location_type
        , CAST(incident_zip AS VARCHAR) AS incident_zip 
        , CAST(incident_address AS VARCHAR) AS incident_address 
        , CAST(street_name AS VARCHAR) AS street_name 
        , CAST(borough AS VARCHAR) AS borough
        , CAST(status AS VARCHAR) AS status 
        , CAST(resolution_action_updated_date AS TIMESTAMP) AS resolution_action_updated_date
        , CAST(community_board AS VARCHAR) AS community_board
        , CAST(open_data_channel_type AS VARCHAR) AS open_data_channel_type
        , CAST(latitude AS FLOAT) AS latitude
        , CAST(longitude AS FLOAT) AS longitude
    FROM deduplicated
)
SELECT *
FROM renamed_and_cast