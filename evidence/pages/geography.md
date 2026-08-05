---
title: Geography
---

Does response time vary meaningfully by borough or community board,
independent of complaint type?

```borough_overall
SELECT * 
FROM nyc311.borough_overall
ORDER BY median_response_time
```

<BarChart
    data={borough_overall}
    x=borough
    y=median_response_time
    xAxisTitle="Borough"
    yAxisTitle="Median Response Time (minutes)"
    title="Median Response Time by Borough"
/>


Total requests filed, by borough:

<BarChart
    data={borough_overall}
    x=borough
    y=total_requests
    xAxisTitle="Borough"
    yAxisTitle="Total Requests"
    title="Request Volume by Borough"
/>


Staten Island has the highest median response time (728 minutes) despite
having by far the *lowest* request volume (357K, well under a fifth of
Brooklyn's ~2.8M). An inverse relationship between how many complaints a
borough files and how quickly they get resolved.


## Community Board Detail

Finer-grained view — one row per NYC community district (parks, airports,
and unresolved-district requests excluded; see note below).

```community_board_data
SELECT * 
FROM nyc311.community_board_summary
ORDER BY median_response_time
```

<DataTable data={community_board_data} rows=59>
    <Column id=community_board title="Community Board"/>
    <Column id=total_requests title="Total Requests"/>
    <Column id=median_response_time title="Median Response Time (min)" fmt="num1"/>
    <Column id=avg_response_time title="Avg Response Time (min)" fmt="num1"/>
</DataTable>

*Excludes NYC's 12 "joint interest areas" (parks and airports not
contained within any single community district, e.g. Central Park, JFK)
and requests with an unresolved district — this view is scoped to
residential service comparison specifically.*
