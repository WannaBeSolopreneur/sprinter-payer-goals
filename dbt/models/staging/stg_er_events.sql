select
    event_id,
    member_id,
    payer_id,
    missed_visit_id,
    cast(event_at as timestamp) as event_at,
    cast(event_at as date) as event_on
from {{ source('raw', 'er_events') }}
