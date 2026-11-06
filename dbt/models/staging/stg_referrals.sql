select
    referral_id,
    member_id,
    payer_id,
    cast(referred_at as timestamp) as referred_at,
    cast(referred_at as date) as referred_on,
    visit_type,
    referral_source
from {{ source('raw', 'referrals') }}
