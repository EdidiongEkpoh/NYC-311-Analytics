


SELECT *
FROM {{ ref('int_311_service_requests') }}
WHERE is_response_time_valid = true
    AND response_time < 0