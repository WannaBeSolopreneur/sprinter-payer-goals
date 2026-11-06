select
    goal_id,
    label,
    subtitle,
    spark_caption,
    unit,
    unit_singular,
    unit_plural,
    metric_kind,
    direction,
    cast(target_value as double) as target_value,
    cast(sort_order as integer) as sort_order
from {{ source('raw', 'goals') }}
