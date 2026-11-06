select
    cast(period_start as date) as period_start,
    cast(period_end as date) as period_end,
    quarter_label,
    cast(on_track_ratio as double) as on_track_ratio,
    cast(at_risk_ratio as double) as at_risk_ratio,
    example_payer_id,
    {{ datediff_days('cast(period_start as date)', 'cast(period_end as date)') }} + 1 as days_in_period
from {{ source('raw', 'calendar') }}
