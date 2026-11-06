with pace as (
    select * from {{ ref('mart_goal_status') }} where goal_id = 'visits_completed'
),

overdue as (
    select * from {{ ref('mart_goal_status') }} where goal_id = 'members_overdue'
),

completion as (
    select * from {{ ref('mart_goal_status') }} where goal_id = 'visit_completion_rate'
),

noshow as (
    select count(*) as no_show_visits
    from {{ ref('fct_terminal_visits') }}
    where status = 'no_show'
),

er as (
    select count(*) as members
    from {{ ref('fct_er_after_miss') }}
),

waiting as (
    select count(*) as referrals
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
)

select
    payer.payer_id,
    actions.action_id,
    actions.sort_order,
    actions.title,
    actions.metric_value,
    actions.sentence
from (
    select
        'pace' as action_id,
        1 as sort_order,
        'Catch the visit pace' as title,
        pace.current_value as metric_value,
        cast(cast(round(pace.current_value, 0) as integer) as varchar)
            || ' in-home visits are completed. The quarter goal is '
            || cast(cast(round(pace.target_value, 0) as integer) as varchar)
            || '. '
            || pace.delta_label
            || '.' as sentence
    from pace

    union all

    select
        'overdue' as action_id,
        2 as sort_order,
        'Book overdue members' as title,
        overdue.current_value as metric_value,
        cast(cast(round(overdue.current_value, 0) as integer) as varchar)
            || ' members are overdue for preventive or chronic home care. The target is '
            || cast(cast(round(overdue.target_value, 0) as integer) as varchar)
            || ' or fewer. Book the oldest gaps first.' as sentence
    from overdue

    union all

    select
        'er_after_miss' as action_id,
        3 as sort_order,
        'Call after a missed visit' as title,
        er.members as metric_value,
        cast(er.members as varchar)
            || ' members had an ER visit within 30 days of a missed home visit this quarter. Call that list this week.' as sentence
    from er

    union all

    select
        'no_shows' as action_id,
        4 as sort_order,
        'Reschedule no-shows' as title,
        noshow.no_show_visits as metric_value,
        cast(noshow.no_show_visits as varchar)
            || ' visits were no-shows this quarter. Completion is '
            || cast(cast(round(completion.current_value * 100, 0) as integer) as varchar)
            || '% against an '
            || cast(cast(round(completion.target_value * 100, 0) as integer) as varchar)
            || '% target. Offer those members a new time.' as sentence
    from noshow
    cross join completion

    union all

    select
        'waiting_referrals' as action_id,
        5 as sort_order,
        'Schedule referrals with no visit' as title,
        waiting.referrals as metric_value,
        cast(waiting.referrals as varchar)
            || ' referrals are more than 14 days old and still have no visit scheduled. Put them on the schedule this week.' as sentence
    from waiting
) as actions
cross join {{ ref('dim_payer') }} as payer
