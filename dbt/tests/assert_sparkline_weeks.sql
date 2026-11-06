-- Sparklines use complete weeks only. A week that contains the as-of date and ends after it is out.

select week_start
from {{ ref('mart_weekly_trend') }}
where week_end > (select as_of from {{ ref('int_calendar') }})
    or {{ datediff_days('week_start', 'week_end') }} <> 6

union all

select 'partial_week'
where exists (
    select 1
    from {{ ref('mart_weekly_trend') }} as weeks
    inner join {{ ref('int_calendar') }} as calendar
        on weeks.week_start <= calendar.as_of
        and weeks.week_end > calendar.as_of
)

union all

select 'week_count'
where (
    select count(distinct week_start)
    from {{ ref('mart_weekly_trend') }}
) <> 12
