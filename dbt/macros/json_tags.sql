{% macro json_array_lateral(column_name, alias_name) -%}
    {%- if target.type == 'snowflake' -%}
        , lateral flatten(input => parse_json({{ column_name }})) {{ alias_name }}
    {%- else -%}
        cross join lateral jsonb_array_elements({{ column_name }}) as {{ alias_name }}
    {%- endif -%}
{%- endmacro %}

{% macro json_tag_name(alias_name) -%}
    {%- if target.type == 'snowflake' -%}
        lower(trim(cast({{ alias_name }}.value:name as {{ dbt.type_string() }})))
    {%- else -%}
        lower(trim({{ alias_name }} ->> 'name'))
    {%- endif -%}
{%- endmacro %}

{% macro json_tag_count(alias_name) -%}
    {%- if target.type == 'snowflake' -%}
        cast({{ alias_name }}.value:count as integer)
    {%- else -%}
        cast({{ alias_name }} ->> 'count' as integer)
    {%- endif -%}
{%- endmacro %}
