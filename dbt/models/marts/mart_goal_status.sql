with calendar as (
    select * from {{ ref('int_calendar') }}
),

actuals as (
    select
        'visits_completed' as goal_id,
        count(*) * 1.0 as current_value
    from {{ ref('fct_completed_visits') }}

    union all

    select
        'median_days' as goal_id,
        percentile_cont(0.5) within group (order by days_to_complete) as current_value
    from {{ ref('fct_completed_visits') }}

    union all

    select
        'members_overdue' as goal_id,
        sum(is_overdue) * 1.0 as current_value
    from {{ ref('fct_members') }}

    union all

    select
        'visit_completion_rate' as goal_id,
        sum(case when status = 'completed' then 1 else 0 end) * 1.0
            / nullif(count(*), 0) as current_value
    from {{ ref('fct_terminal_visits') }}
),

scored as (
    select
        goals.goal_id,
        goals.label,
        goals.subtitle,
        goals.spark_caption,
        goals.unit,
        goals.unit_singular,
        goals.unit_plural,
        goals.metric_kind,
        goals.direction,
        goals.sort_order,
        actuals.current_value,
        goals.target_value,
        calendar.as_of,
        calendar.quarter_label,
        calendar.days_elapsed,
        calendar.days_in_period,
        calendar.on_track_ratio,
        calendar.at_risk_ratio,
        case
            when goals.direction = 'lower' then goals.target_value / nullif(actuals.current_value, 0)
            else actuals.current_value / nullif(goals.target_value, 0)
        end as progress_ratio,
        case
            when goals.metric_kind = 'pace'
                then calendar.days_elapsed * 1.0 / calendar.days_in_period
        end as pace_ratio,
        case
            when goals.metric_kind = 'pace'
                then goals.target_value * calendar.days_elapsed * 1.0 / calendar.days_in_period
        end as pace_value,
        case
            when goals.metric_kind = 'pace'
                and actuals.current_value
                    >= goals.target_value
                    * calendar.days_elapsed * 1.0 / calendar.days_in_period
                    * calendar.on_track_ratio
                then 'on_track'
            when goals.metric_kind = 'pace'
                and actuals.current_value
                    >= goals.target_value
                    * calendar.days_elapsed * 1.0 / calendar.days_in_period
                    * calendar.at_risk_ratio
                then 'at_risk'
            when goals.metric_kind = 'pace' then 'behind'
            when goals.direction = 'lower'
                and actuals.current_value <= goals.target_value / calendar.on_track_ratio
                then 'on_track'
            when goals.direction = 'lower'
                and actuals.current_value <= goals.target_value / calendar.at_risk_ratio
                then 'at_risk'
            when goals.direction = 'lower' then 'behind'
            when actuals.current_value >= goals.target_value * calendar.on_track_ratio
                then 'on_track'
            when actuals.current_value >= goals.target_value * calendar.at_risk_ratio
                then 'at_risk'
            else 'behind'
        end as status
    from {{ ref('stg_goals') }} as goals
    inner join actuals
        on goals.goal_id = actuals.goal_id
    cross join calendar
)

select
    payer.payer_id,
    scored.goal_id,
    scored.label,
    scored.subtitle,
    scored.spark_caption,
    scored.unit,
    scored.unit_singular,
    scored.unit_plural,
    scored.metric_kind,
    scored.direction,
    scored.sort_order,
    case when scored.sort_order = 1 then 'primary' else 'support' end as tile_role,
    scored.current_value,
    scored.target_value,
    scored.as_of,
    scored.quarter_label,
    scored.days_elapsed,
    scored.days_in_period,
    scored.on_track_ratio,
    scored.at_risk_ratio,
    scored.progress_ratio,
    scored.pace_ratio,
    scored.pace_value,
    case
        when scored.metric_kind = 'pace' then scored.current_value / nullif(scored.pace_value, 0)
    end as pct_of_pace,
    scored.status,
    case scored.status
        when 'on_track' then 'On track'
        when 'at_risk' then 'At risk'
        else 'Behind'
    end as status_label,
    case
        when scored.metric_kind = 'pace'
            and cast(round(abs(scored.current_value - scored.pace_value), 0) as integer) = 0
            then 'On the pace line'
        when scored.metric_kind = 'pace' and scored.current_value >= scored.pace_value
            then 'Ahead of pace by ' || case
                when cast(round(scored.current_value - scored.pace_value, 0) as integer) = 1
                    then '1 ' || scored.unit_singular
                else cast(cast(round(scored.current_value - scored.pace_value, 0) as integer) as varchar)
                    || ' ' || scored.unit_plural
            end
        when scored.metric_kind = 'pace'
            then 'Behind pace by ' || case
                when cast(round(scored.pace_value - scored.current_value, 0) as integer) = 1
                    then '1 ' || scored.unit_singular
                else cast(cast(round(scored.pace_value - scored.current_value, 0) as integer) as varchar)
                    || ' ' || scored.unit_plural
            end
        when scored.unit = 'percent'
            and cast(round(abs(scored.current_value - scored.target_value) * 100, 0) as integer) = 0
            then 'On the target'
        when scored.unit = 'percent' and scored.current_value >= scored.target_value
            then 'Above the target by ' || case
                when cast(round((scored.current_value - scored.target_value) * 100, 0) as integer) = 1
                    then '1 point'
                else cast(cast(round((scored.current_value - scored.target_value) * 100, 0) as integer) as varchar)
                    || ' points'
            end
        when scored.unit = 'percent'
            then 'Short of the target by ' || case
                when cast(round((scored.target_value - scored.current_value) * 100, 0) as integer) = 1
                    then '1 point'
                else cast(cast(round((scored.target_value - scored.current_value) * 100, 0) as integer) as varchar)
                    || ' points'
            end
        when scored.direction = 'lower'
            and cast(round(abs(scored.current_value - scored.target_value), 0) as integer) = 0
            then 'On the target'
        when scored.direction = 'lower' and scored.current_value <= scored.target_value
            then 'Under the target by ' || case
                when cast(round(scored.target_value - scored.current_value, 0) as integer) = 1
                    then '1 ' || scored.unit_singular
                else cast(cast(round(scored.target_value - scored.current_value, 0) as integer) as varchar)
                    || ' ' || scored.unit_plural
            end
        when scored.direction = 'lower'
            then 'Over the target by ' || case
                when cast(round(scored.current_value - scored.target_value, 0) as integer) = 1
                    then '1 ' || scored.unit_singular
                else cast(cast(round(scored.current_value - scored.target_value, 0) as integer) as varchar)
                    || ' ' || scored.unit_plural
            end
        when cast(round(abs(scored.current_value - scored.target_value), 0) as integer) = 0
            then 'On the target'
        when scored.current_value >= scored.target_value
            then 'Above the target by ' || case
                when cast(round(scored.current_value - scored.target_value, 0) as integer) = 1
                    then '1 ' || scored.unit_singular
                else cast(cast(round(scored.current_value - scored.target_value, 0) as integer) as varchar)
                    || ' ' || scored.unit_plural
            end
        else 'Short of the target by ' || case
            when cast(round(scored.target_value - scored.current_value, 0) as integer) = 1
                then '1 ' || scored.unit_singular
            else cast(cast(round(scored.target_value - scored.current_value, 0) as integer) as varchar)
                || ' ' || scored.unit_plural
        end
    end as delta_label
from scored
cross join {{ ref('dim_payer') }} as payer
