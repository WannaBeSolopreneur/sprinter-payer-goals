-- Published marts contain only the example payer.

select payer_id from {{ ref('fct_visits') }}
where payer_id <> '{{ var("example_payer_id") }}'

union all

select payer_id from {{ ref('fct_members') }}
where payer_id <> '{{ var("example_payer_id") }}'

union all

select payer_id from {{ ref('fct_care_gaps') }}
where payer_id <> '{{ var("example_payer_id") }}'

union all

select payer_id from {{ ref('fct_completed_visits') }}
where payer_id <> '{{ var("example_payer_id") }}'

union all

select payer_id from {{ ref('fct_terminal_visits') }}
where payer_id <> '{{ var("example_payer_id") }}'

union all

select payer_id from {{ ref('fct_er_after_miss') }}
where payer_id <> '{{ var("example_payer_id") }}'

union all

select payer_id from {{ ref('mart_goal_status') }}
where payer_id <> '{{ var("example_payer_id") }}'

union all

select payer_id from {{ ref('mart_visit_pace') }}
where payer_id <> '{{ var("example_payer_id") }}'

union all

select payer_id from {{ ref('mart_weekly_trend') }}
where payer_id <> '{{ var("example_payer_id") }}'

union all

select payer_id from {{ ref('mart_actions_this_week') }}
where payer_id <> '{{ var("example_payer_id") }}'

union all

select 'dim_payer_count'
where (select count(*) from {{ ref('dim_payer') }}) <> 1

union all

select payer_id from {{ ref('dim_payer') }}
where payer_id <> '{{ var("example_payer_id") }}'
