select
    payer_id,
    payer_name,
    cast(is_example as integer) as is_example
from {{ source('raw', 'payers') }}
