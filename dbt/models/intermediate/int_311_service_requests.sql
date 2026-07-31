WITH staging AS (
    SELECT *
    FROM {{ ref('stg_311_service_requests') }}
)
SELECT *
    , DATEDIFF('minute', created_date, closed_date) AS response_time
    , (closed_date IS NOT NULL AND closed_date >= created_date) AS is_response_time_valid
    , DAYNAME(created_date) AS day_of_week
    , CASE 
        WHEN DATEPART('hour', created_date) BETWEEN 5 AND 11 THEN 'Morning'
        WHEN DATEPART('hour', created_date) BETWEEN 12 AND 16 THEN 'Afternoon'
        WHEN DATEPART('hour', created_date) BETWEEN 17 AND 20 THEN 'Evening'
        ELSE 'Night'
      END AS time_of_day
    , DAYNAME(created_date) IN ('Saturday', 'Sunday') AS is_weekend
FROM staging 