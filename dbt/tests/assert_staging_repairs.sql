-- Raw has duplicate visits, blank types, and a clock that runs backward.
-- Staging and intermediate repair them.

select 'duplicates_missing'
where (
    select count(*) - count(distinct visit_id)
    from {{ source('raw', 'visits') }}
) < 1

union all

select 'staging_not_deduped'
where (
    select count(*)
    from {{ ref('stg_visits') }}
) <> (
    select count(distinct visit_id)
    from {{ source('raw', 'visits') }}
)

union all

select 'blank_type_missing'
where (
    select count(*)
    from {{ source('raw', 'visits') }}
    where visit_type is null or length(trim(visit_type)) = 0
) < 1

union all

select visit_id
from {{ ref('int_visits') }}
where visit_type is null

union all

select 'skew_missing'
where (
    select count(*)
    from {{ source('raw', 'visits') }} as visits
    inner join {{ source('raw', 'referrals') }} as referrals
        on visits.referral_id = referrals.referral_id
    where lower(trim(visits.status)) = 'completed'
        and referrals.referred_at > visits.completed_at
) < 1

union all

select visit_id
from {{ ref('int_visits') }}
where status = 'completed'
    and (
        referred_at > completed_at
        or days_to_complete < 0
    )
