-- Isolation is real only if the other payers exist upstream.

select 'northwind_visits'
where (
    select count(*)
    from {{ ref('int_visits') }}
    where payer_id = 'payer_northwind'
) < 500

union all

select 'cedarridge_visits'
where (
    select count(*)
    from {{ ref('int_visits') }}
    where payer_id = 'payer_cedarridge'
) < 500

union all

select 'other_overdue'
where (
    select count(*)
    from {{ ref('int_members') }}
    where payer_id <> '{{ var("example_payer_id") }}'
        and is_overdue = 1
) < 50

union all

select 'other_er'
where (
    select count(*)
    from {{ ref('int_er_after_miss') }}
    where payer_id <> '{{ var("example_payer_id") }}'
) < 5
