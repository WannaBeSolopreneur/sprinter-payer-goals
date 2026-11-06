select
    events.payer_id,
    events.member_id,
    min(events.event_id) as event_id,
    min(events.missed_visit_id) as missed_visit_id,
    min(events.missed_on) as missed_on,
    min(events.event_on) as event_on
from {{ ref('int_er_after_miss') }} as events
inner join {{ ref('dim_payer') }} as payer
    on events.payer_id = payer.payer_id
inner join {{ ref('int_calendar') }} as calendar
    on events.missed_on >= calendar.period_start
    and events.missed_on <= calendar.as_of
    and events.event_on <= calendar.as_of
group by events.payer_id, events.member_id
