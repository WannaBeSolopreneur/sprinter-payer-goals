{{ config(materialized='view') }}

with digits as (
    select 0 as digit
    union all select 1
    union all select 2
    union all select 3
    union all select 4
    union all select 5
    union all select 6
    union all select 7
    union all select 8
    union all select 9
),

numbers as (
    select ones.digit + 10 * tens.digit + 100 * hundreds.digit as day_offset
    from digits as ones
    cross join digits as tens
    cross join digits as hundreds
),

bounds as (
    select
        history_start,
        period_end,
        {{ datediff_days('history_start', 'period_end') }} as span_days
    from {{ ref('int_calendar') }}
)

select
    {{ date_add_days('bounds.history_start', 'numbers.day_offset') }} as date_day
from numbers
cross join bounds
where numbers.day_offset <= bounds.span_days
