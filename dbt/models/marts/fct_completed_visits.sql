select visits.*
from {{ ref('fct_visits') }} as visits
inner join {{ ref('int_calendar') }} as calendar
    on visits.completed_on >= calendar.period_start
    and visits.completed_on <= calendar.as_of
where visits.status = 'completed'
