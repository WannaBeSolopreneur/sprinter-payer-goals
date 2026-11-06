-- The goal table matches the fact tables. A second formula on the page would fail this.

with calendar as (
    select * from {{ ref('int_calendar') }}
),

expected as (
    select
        'visits_completed' as goal_id,
        (select count(*) * 1.0 from {{ ref('fct_completed_visits') }}) as expected_value

    union all

    select
        'median_days' as goal_id,
        (
            select percentile_cont(0.5) within group (order by days_to_complete)
            from {{ ref('fct_completed_visits') }}
        ) as expected_value

    union all

    select
        'members_overdue' as goal_id,
        (
            select count(distinct member_id) * 1.0
            from {{ ref('fct_care_gaps') }} as gaps
            cross join calendar
            where gaps.gap_type in ('preventive', 'chronic')
                and gaps.due_on <= calendar.as_of
                and (gaps.closed_on is null or gaps.closed_on > calendar.as_of)
        ) as expected_value

    union all

    select
        'visit_completion_rate' as goal_id,
        (
            select sum(case when status = 'completed' then 1 else 0 end) * 1.0 / nullif(count(*), 0)
            from {{ ref('fct_terminal_visits') }}
        ) as expected_value
)

select goals.goal_id
from {{ ref('mart_goal_status') }} as goals
inner join expected
    on goals.goal_id = expected.goal_id
where abs(goals.current_value - expected.expected_value) > 0.00001

union all

select 'overdue_flag'
where (
    select sum(is_overdue)
    from {{ ref('fct_members') }}
) <> (
    select current_value
    from {{ ref('mart_goal_status') }}
    where goal_id = 'members_overdue'
)

union all

select 'goal_count'
where (select count(*) from {{ ref('mart_goal_status') }}) <> 4

union all

select 'pace_rows'
where (
    select count(*)
    from {{ ref('mart_visit_pace') }}
) <> (
    select days_in_period
    from {{ ref('int_calendar') }}
)

union all

select 'trend_grain'
where (
    select count(*)
    from (
        select goal_id, week_start
        from {{ ref('mart_weekly_trend') }}
        group by 1, 2
        having count(*) > 1
    ) as dupes
) > 0
