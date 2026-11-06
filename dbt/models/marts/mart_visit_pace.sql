with calendar as (
    select * from {{ ref('int_calendar') }}
),

goal as (
    select target_value
    from {{ ref('stg_goals') }}
    where goal_id = 'visits_completed'
),

days as (
    select spine.date_day
    from {{ ref('metric_time_spine') }} as spine
    inner join calendar
        on spine.date_day >= calendar.period_start
        and spine.date_day <= calendar.period_end
),

daily as (
    select
        completed_on as date_day,
        count(*) as completed_visits
    from {{ ref('fct_completed_visits') }}
    group by 1
),

running as (
    select
        days.date_day,
        sum(coalesce(daily.completed_visits, 0)) over (
            order by days.date_day
        ) as cumulative_through_day
    from days
    left join daily
        on days.date_day = daily.date_day
)

select
    payer.payer_id,
    running.date_day,
    case
        when running.date_day <= calendar.as_of then running.cumulative_through_day
    end as cumulative_actual,
    goal.target_value * (
        {{ datediff_days('calendar.period_start', 'running.date_day') }} + 1
    ) * 1.0 / calendar.days_in_period as cumulative_pace,
    case when running.date_day <= calendar.as_of then 1 else 0 end as is_elapsed
from running
cross join calendar
cross join goal
cross join {{ ref('dim_payer') }} as payer
