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
-- NYC has 59 real community districts + 12 "joint interest areas" (JIAs --
-- parks/airports not contained within any single CD, e.g. Central Park,
-- JFK, LaGuardia) that also carry a community_board-shaped value in this
-- data. Excluded here since this mart is meant to answer a residential
-- service-equity question, and a park/airport isn't a resident.
-- "Unspecified" rows (borough known, district unresolved, or fully
-- unspecified) excluded for the same reason -- not a real district.
WHERE community_board NOT LIKE '%Unspecified%'
  AND community_board NOT IN (
      '26 BRONX', '27 BRONX', '28 BRONX',
      '55 BROOKLYN', '56 BROOKLYN',
      '64 MANHATTAN',
      '80 QUEENS', '81 QUEENS', '82 QUEENS', '83 QUEENS', '84 QUEENS',
      '95 STATEN ISLAND'
  )
GROUP BY 1
