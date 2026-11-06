-- Cumulative actual never falls, stops on the as-of date, and matches the visit goal.

with ordered as (
    select
        date_day,
        cumulative_actual,
        lag(cumulative_actual) over (order by date_day) as previous_actual
    from {{ ref('mart_visit_pace') }}
    where cumulative_actual is not null
)

select date_day
from ordered
where previous_actual is not null
    and cumulative_actual < previous_actual

union all

select date_day
from {{ ref('mart_visit_pace') }}
where date_day > (select as_of from {{ ref('int_calendar') }})
    and cumulative_actual is not null

union all

select date_day
from {{ ref('mart_visit_pace') }}
where date_day = (select as_of from {{ ref('int_calendar') }})
    and cumulative_actual <> (
        select current_value
        from {{ ref('mart_goal_status') }}
        where goal_id = 'visits_completed'
    )

union all

select date_day
from {{ ref('mart_visit_pace') }}
where date_day = (select period_end from {{ ref('int_calendar') }})
    and abs(
        cumulative_pace - (
            select target_value
            from {{ ref('stg_goals') }}
            where goal_id = 'visits_completed'
        )
    ) > 0.01
