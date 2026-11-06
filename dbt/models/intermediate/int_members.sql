select
    members.member_id,
    members.payer_id,
    members.state_code,
    members.line_of_business,
    members.enrolled_on,
    members.has_chronic,
    case
        when exists (
            select 1
            from {{ ref('stg_care_gaps') }} as gaps
            where gaps.member_id = members.member_id
                and {{ gap_is_open('gaps.due_on', 'gaps.closed_on', 'gaps.gap_type', 'calendar.as_of') }}
        ) then 1
        else 0
    end as is_overdue
from {{ ref('stg_members') }} as members
cross join {{ ref('int_calendar') }} as calendar
