{% macro hour_from_timestamp(column_name) -%}
    cast(extract(hour from {{ column_name }}) as integer)
{%- endmacro %}

{% macro day_of_week_number(column_name) -%}
    {%- if target.type == 'snowflake' -%}
        dayofweekiso({{ column_name }})
    {%- else -%}
        extract(isodow from {{ column_name }})
    {%- endif -%}
{%- endmacro %}

{% macro day_of_week_name(column_name) -%}
    case {{ day_of_week_number(column_name) }}
        when 1 then 'Mon'
        when 2 then 'Tue'
        when 3 then 'Wed'
        when 4 then 'Thu'
        when 5 then 'Fri'
        when 6 then 'Sat'
        when 7 then 'Sun'
    end
{%- endmacro %}

{% macro is_weekend(column_name) -%}
    case when {{ day_of_week_number(column_name) }} in (6, 7) then true else false end
{%- endmacro %}
