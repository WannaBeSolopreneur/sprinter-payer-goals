select
    gap_id,
    member_id,
    payer_id,
    gap_type,
    cast(due_on as date) as due_on,
    cast(closed_on as date) as closed_on
from {{ source('raw', 'care_gaps') }}
