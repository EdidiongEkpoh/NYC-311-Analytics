{{ config(severity='warn') }}


-- NYC 311 data has a documented issue where closed_date precedes
-- created_date for approximately 0.2% of records (as noted in published analysis of this dataset: https://arxiv.org/html/2502.08649v2#S3.SS3.SSS0.Px3).
-- This file is used to assert that there are no records where closed_date is earlier than created_date

SELECT *
FROM {{ ref('stg_311_service_requests')}}
WHERE closed_date < created_date