select members.*
from {{ ref('int_members') }} as members
inner join {{ ref('dim_payer') }} as payer
    on members.payer_id = payer.payer_id
