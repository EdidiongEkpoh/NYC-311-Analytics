---
title: Seasonality
---

What's cyclical (time of day, day of week, month) versus what's a
genuine trend in complaint volume over time?

```monthly_volume
SELECT period
    , SUM(total_requests) AS total_requests
FROM nyc311.monthly_volume
GROUP BY 1
ORDER BY 1
```

<LineChart
    data={monthly_volume}
    x=period
    y=total_requests
    xFmt="mmm yyyy"
    xAxisTitle="Month"
    yAxisTitle="Total Requests"
    title="Monthly Request Volume"
/>

## Time of Day x Day of Week

```weekday_hour_pivot
select
    day_of_week,
    case day_of_week
        when 'Monday' then 1 when 'Tuesday' then 2 when 'Wednesday' then 3
        when 'Thursday' then 4 when 'Friday' then 5 when 'Saturday' then 6
        else 7
    end as day_sort,
    sum(total_requests) filter (where time_of_day = 'Morning') as morning,
    sum(total_requests) filter (where time_of_day = 'Afternoon') as afternoon,
    sum(total_requests) filter (where time_of_day = 'Evening') as evening,
    sum(total_requests) filter (where time_of_day = 'Night') as night
from nyc311.weekday_hour_heatmap
group by day_of_week
order by day_sort
```

<DataTable data={weekday_hour_pivot}>
    <Column id=day_of_week title="Day"/>
    <Column id=morning title="Morning"/>
    <Column id=afternoon title="Afternoon"/>
    <Column id=evening title="Evening"/>
    <Column id=night title="Night"/>
</DataTable>


Night complaints spike sharply on weekends. Saturday (395K) and Sunday
(409K) run well above every weekday's Night total (270–310K) while
weekend Morning/Afternoon volumes are correspondingly lower than
weekdays. Consistent with noise/party complaints replacing routine
daytime request types (street conditions, parking) on weekend nights.