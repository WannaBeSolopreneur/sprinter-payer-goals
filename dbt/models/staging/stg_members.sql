select
    member_id,
    payer_id,
    state_code,
    line_of_business,
    cast(enrolled_on as date) as enrolled_on,
    cast(has_chronic as integer) as has_chronic
from {{ source('raw', 'members') }}
