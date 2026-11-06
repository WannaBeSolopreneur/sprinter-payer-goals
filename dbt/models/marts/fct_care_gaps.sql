select gaps.*
from {{ ref('stg_care_gaps') }} as gaps
inner join {{ ref('dim_payer') }} as payer
    on gaps.payer_id = payer.payer_id
