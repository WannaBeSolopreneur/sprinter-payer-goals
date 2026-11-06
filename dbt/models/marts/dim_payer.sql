select
    payer_id,
    payer_name,
    is_example
from {{ ref('stg_payers') }}
where payer_id = '{{ var("example_payer_id") }}'
