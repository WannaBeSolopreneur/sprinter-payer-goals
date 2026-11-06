{% macro gap_is_open(due_on, closed_on, gap_type, as_of) -%}
(
    {{ gap_type }} in ('preventive', 'chronic')
    and {{ due_on }} <= {{ as_of }}
    and ({{ closed_on }} is null or {{ closed_on }} > {{ as_of }})
)
{%- endmacro %}
