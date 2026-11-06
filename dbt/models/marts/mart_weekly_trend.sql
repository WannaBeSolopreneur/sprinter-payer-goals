with weeks as (
    select * from {{ ref('stg_weeks') }}
),

median_days as (
    select
        'median_days' as goal_id,
        weeks.week_start,
        weeks.week_end,
        weeks.sort_order,
        percentile_cont(0.5) within group (order by visits.days_to_complete) as trend_value
    from weeks
    inner join {{ ref('fct_visits') }} as visits
        on visits.status = 'completed'
        and visits.completed_on >= weeks.week_start
        and visits.completed_on <= weeks.week_end
    group by weeks.week_start, weeks.week_end, weeks.sort_order
),

completion as (
    select
        'visit_completion_rate' as goal_id,
        weeks.week_start,
        weeks.week_end,
        weeks.sort_order,
        sum(case when visits.status = 'completed' then 1 else 0 end) * 1.0
            / nullif(count(*), 0) as trend_value
    from weeks
    inner join {{ ref('fct_visits') }} as visits
        on visits.status in ('completed', 'canceled', 'no_show')
        and visits.outcome_on >= weeks.week_start
        and visits.outcome_on <= weeks.week_end
    group by weeks.week_start, weeks.week_end, weeks.sort_order
),

overdue as (
    select
        'members_overdue' as goal_id,
        weeks.week_start,
        weeks.week_end,
        weeks.sort_order,
        count(distinct gaps.member_id) * 1.0 as trend_value
    from weeks
    inner join {{ ref('fct_care_gaps') }} as gaps
        on gaps.gap_type in ('preventive', 'chronic')
        and gaps.due_on <= weeks.week_end
        and (gaps.closed_on is null or gaps.closed_on > weeks.week_end)
    group by weeks.week_start, weeks.week_end, weeks.sort_order
)

select
    payer.payer_id,
    trends.goal_id,
    trends.week_start,
    trends.week_end,
    trends.sort_order,
    trends.trend_value
from (
    select * from median_days
    union all
    select * from completion
    union all
    select * from overdue
) as trends
cross join {{ ref('dim_payer') }} as payer
