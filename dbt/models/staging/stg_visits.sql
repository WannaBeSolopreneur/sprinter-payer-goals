with ranked as (
    select
        visit_id,
        referral_id,
        member_id,
        payer_id,
        nullif(trim(visit_type), '') as visit_type_raw,
        lower(trim(status)) as status,
        cast(scheduled_at as timestamp) as scheduled_at,
        cast(completed_at as timestamp) as completed_at,
        cast(outcome_at as timestamp) as outcome_at,
        cast(ingest_at as timestamp) as ingest_at,
        cast(source_row as integer) as source_row,
        row_number() over (
            partition by visit_id
            order by cast(ingest_at as timestamp) desc, cast(source_row as integer) desc
        ) as copy_rank
    from {{ source('raw', 'visits') }}
)

select
    visit_id,
    referral_id,
    member_id,
    payer_id,
    visit_type_raw,
    status,
    scheduled_at,
    completed_at,
    outcome_at
from ranked
where copy_rank = 1
