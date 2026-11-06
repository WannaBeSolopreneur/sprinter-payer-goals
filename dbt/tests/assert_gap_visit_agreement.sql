-- An open gap has no completed visit of that type on or after the due date.
-- A closed gap has a completed visit of that type on the closed date.

select gaps.gap_id
from {{ ref('fct_care_gaps') }} as gaps
inner join {{ ref('int_calendar') }} as calendar
    on {{ gap_is_open('gaps.due_on', 'gaps.closed_on', 'gaps.gap_type', 'calendar.as_of') }}
where exists (
    select 1
    from {{ ref('fct_visits') }} as visits
    where visits.member_id = gaps.member_id
        and visits.visit_type = gaps.gap_type
        and visits.status = 'completed'
        and visits.completed_on >= gaps.due_on
        and visits.completed_on <= calendar.as_of
)

union all

select gaps.gap_id
from {{ ref('fct_care_gaps') }} as gaps
where gaps.closed_on is not null
    and not exists (
        select 1
        from {{ ref('fct_visits') }} as visits
        where visits.member_id = gaps.member_id
            and visits.visit_type = gaps.gap_type
            and visits.status = 'completed'
            and visits.completed_on = gaps.closed_on
    )
