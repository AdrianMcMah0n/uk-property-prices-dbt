-- Sales and typical (median) price per month and property type.
select
    sale_month,
    property_type,
    count(*)                                                         as sales,
    percentile_cont(0.5) within group (order by price_gbp)::integer  as median_price_gbp,
    round(avg(price_gbp))::integer                                   as mean_price_gbp
from {{ ref('fct_sales') }}
group by sale_month, property_type
