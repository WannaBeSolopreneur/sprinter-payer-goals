select
    cast(seed as integer) as seed,
    cast(as_of as date) as as_of,
    cast(history_start as date) as history_start,
    example_payer_id
from {{ source('raw', 'generation_meta') }}
