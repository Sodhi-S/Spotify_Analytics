{% macro tag_list_agg(expression) -%}
    {%- if target.type == 'snowflake' -%}
        listagg(distinct {{ expression }}, ',')
    {%- else -%}
        string_agg(distinct {{ expression }}, ',')
    {%- endif -%}
{%- endmacro %}
