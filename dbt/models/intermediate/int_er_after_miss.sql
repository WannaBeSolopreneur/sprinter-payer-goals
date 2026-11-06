select
    events.event_id,
    events.member_id,
    events.payer_id,
    events.missed_visit_id,
    events.event_on,
    visits.outcome_on as missed_on
from {{ ref('stg_er_events') }} as events
inner join {{ ref('int_visits') }} as visits
    on events.missed_visit_id = visits.visit_id
where visits.status in ('canceled', 'no_show')
    and {{ datediff_days('visits.outcome_on', 'events.event_on') }} between 1 and 30
    and not exists (
        select 1
        from {{ ref('int_visits') }} as later
        where later.member_id = visits.member_id
            and later.payer_id = visits.payer_id
            and later.status = 'completed'
            and later.completed_on > visits.outcome_on
            and later.completed_on < events.event_on
    )
