select
    calendar.period_start,
    calendar.period_end,
    calendar.quarter_label,
    calendar.on_track_ratio,
    calendar.at_risk_ratio,
    calendar.example_payer_id,
    calendar.days_in_period,
    meta.as_of,
    meta.history_start,
    meta.seed,
    {{ datediff_days('calendar.period_start', 'meta.as_of') }} + 1 as days_elapsed
from {{ ref('stg_calendar') }} as calendar
cross join {{ ref('stg_generation_meta') }} as meta
