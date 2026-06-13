{% macro surrogate_key(fields) -%}
md5(
    {%- for field in fields -%}
        coalesce(cast({{ field }} as {{ dbt.type_string() }}), '')
        {%- if not loop.last %} || '|' || {% endif -%}
    {%- endfor -%}
)
{%- endmacro %}
