select 'day_counts'
from {{ ref('int_calendar') }}
where days_elapsed <> {{ datediff_days('period_start', 'as_of') }} + 1
    or days_in_period <> {{ datediff_days('period_start', 'period_end') }} + 1
    or abs(on_track_ratio - 0.95) > 0.0000001
    or abs(at_risk_ratio - 0.80) > 0.0000001
    or as_of < period_start
    or as_of > period_end
    or example_payer_id <> '{{ var("example_payer_id") }}'

union all

select 'scheduled_in_terminal'
where exists (
    select 1
    from {{ ref('fct_terminal_visits') }}
    where status = 'scheduled'
)
