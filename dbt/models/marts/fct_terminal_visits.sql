select visits.*
from {{ ref('fct_visits') }} as visits
inner join {{ ref('int_calendar') }} as calendar
    on visits.outcome_on >= calendar.period_start
    and visits.outcome_on <= calendar.as_of
where visits.status in ('completed', 'canceled', 'no_show')
