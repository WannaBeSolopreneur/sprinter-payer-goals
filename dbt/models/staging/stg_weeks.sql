select
    cast(week_start as date) as week_start,
    cast(week_end as date) as week_end,
    cast(sort_order as integer) as sort_order
from {{ source('raw', 'weeks') }}
