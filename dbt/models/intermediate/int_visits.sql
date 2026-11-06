with joined as (
    select
        visits.visit_id,
        visits.referral_id,
        visits.member_id,
        visits.payer_id,
        coalesce(visits.visit_type_raw, referrals.visit_type) as visit_type,
        visits.status,
        case
            when visits.status = 'completed'
                and referrals.referred_at > visits.completed_at
                then visits.completed_at
            else referrals.referred_at
        end as referred_at,
        referrals.referral_source,
        visits.scheduled_at,
        visits.completed_at,
        visits.outcome_at
    from {{ ref('stg_visits') }} as visits
    inner join {{ ref('stg_referrals') }} as referrals
        on visits.referral_id = referrals.referral_id
)

select
    joined.visit_id,
    joined.referral_id,
    joined.member_id,
    joined.payer_id,
    joined.visit_type,
    joined.status,
    joined.referred_at,
    joined.referral_source,
    joined.scheduled_at,
    joined.completed_at,
    joined.outcome_at,
    cast(joined.completed_at as date) as completed_on,
    case
        when joined.status = 'completed' then cast(joined.completed_at as date)
        when joined.status in ('canceled', 'no_show') then cast(joined.outcome_at as date)
    end as outcome_on,
    case
        when joined.status = 'completed' then
            {{ datediff_days('cast(joined.referred_at as date)', 'cast(joined.completed_at as date)') }}
    end as days_to_complete
from joined
