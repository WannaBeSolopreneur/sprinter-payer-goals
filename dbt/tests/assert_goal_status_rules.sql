-- Status uses the calendar cutoffs. On track is 95% or better. At risk is from 80% up to that line.

with expected as (
    select
        goal_id,
        case
            when metric_kind = 'pace'
                and current_value >= target_value * days_elapsed * 1.0 / days_in_period * on_track_ratio
                then 'on_track'
            when metric_kind = 'pace'
                and current_value >= target_value * days_elapsed * 1.0 / days_in_period * at_risk_ratio
                then 'at_risk'
            when metric_kind = 'pace' then 'behind'
            when direction = 'lower'
                and current_value <= target_value / on_track_ratio
                then 'on_track'
            when direction = 'lower'
                and current_value <= target_value / at_risk_ratio
                then 'at_risk'
            when direction = 'lower' then 'behind'
            when current_value >= target_value * on_track_ratio then 'on_track'
            when current_value >= target_value * at_risk_ratio then 'at_risk'
            else 'behind'
        end as expected_status
    from {{ ref('mart_goal_status') }}
)

select goals.goal_id
from {{ ref('mart_goal_status') }} as goals
inner join expected
    on goals.goal_id = expected.goal_id
where goals.status <> expected.expected_status
    or goals.status_label is null
    or goals.delta_label is null
