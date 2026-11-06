-- Each action number is the mart number, and the sentence contains that number.

with checks as (
    select
        'pace' as action_id,
        current_value as expected_value
    from {{ ref('mart_goal_status') }}
    where goal_id = 'visits_completed'

    union all

    select
        'overdue' as action_id,
        current_value as expected_value
    from {{ ref('mart_goal_status') }}
    where goal_id = 'members_overdue'

    union all

    select
        'er_after_miss' as action_id,
        count(*) * 1.0 as expected_value
    from {{ ref('fct_er_after_miss') }}

    union all

    select
        'no_shows' as action_id,
        count(*) * 1.0 as expected_value
    from {{ ref('fct_terminal_visits') }}
    where status = 'no_show'

    union all

    select
        'waiting_referrals' as action_id,
        (
            select count(*) * 1.0
            from {{ ref('stg_referrals') }} as referrals
            inner join {{ ref('dim_payer') }} as payer
                on referrals.payer_id = payer.payer_id
            inner join {{ ref('int_calendar') }} as calendar
                on {{ datediff_days('referrals.referred_on', 'calendar.as_of') }} > 14
            where not exists (
                select 1
                from {{ ref('fct_visits') }} as visits
                where visits.referral_id = referrals.referral_id
            )
        ) as expected_value
)

select actions.action_id
from {{ ref('mart_actions_this_week') }} as actions
inner join checks
    on actions.action_id = checks.action_id
where abs(actions.metric_value - checks.expected_value) > 0.001
    or position(cast(cast(round(actions.metric_value, 0) as integer) as varchar) in actions.sentence) = 0

union all

select 'action_count'
where (
    select count(*)
    from {{ ref('mart_actions_this_week') }}
) < 3
or (
    select count(*)
    from {{ ref('mart_actions_this_week') }}
) > 5
