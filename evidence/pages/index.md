---
title: NYC 311 Service Requests
---

**What drives response time and complaint volume across New York City?**

An end-to-end analytics project on NYC's 311 service request data —
noise complaints, potholes, heating outages, and hundreds of other
categories — structurally similar to a support-ticket or ops dataset in
industry. This dashboard looks at two angles:

```totals
SELECT COUNT(DISTINCT borough) AS boroughs
    , SUM(total_requests) AS total_requests
from nyc311.borough_summary
```


<Value data={totals} column=total_requests /> requests analyzed across
<Value data={totals} column=boroughs /> boroughs.


(7,711 requests (under 0.1%) have no specified borough and are
excluded from the borough and district-level comparisons elsewhere in
this dashboard; they are included here in the overall total, though.)


## [Geography →](/geography)
Does response time vary meaningfully by borough or community board,
independent of complaint type?

## [Seasonality →](/seasonality)
What's cyclical (time of day, day of week, month) versus what's a
genuine trend in complaint volume over time?

---

Full pipeline (scheduled ingestion, tested dbt transformation layer,
CI) documented in the
[project README](https://github.com/EdidiongEkpoh/NYC-311-Analytics).