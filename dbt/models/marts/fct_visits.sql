select visits.*
from {{ ref('int_visits') }} as visits
inner join {{ ref('dim_payer') }} as payer
    on visits.payer_id = payer.payer_id
