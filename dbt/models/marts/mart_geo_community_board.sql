WITH intermediate AS (
    SELECT *
    FROM {{ ref('int_311_service_requests') }}
)
SELECT community_board
    , COUNT(DISTINCT unique_key) AS total_requests
    , SUM(response_time) FILTER (WHERE is_response_time_valid) AS total_response_time
    , AVG(response_time) FILTER (WHERE is_response_time_valid) AS avg_response_time
    , MEDIAN(response_time) FILTER (WHERE is_response_time_valid) AS median_response_time
FROM intermediate
GROUP BY 1
