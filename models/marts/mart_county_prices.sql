-- One row per county: how many sales, typical price, and the mix of what sold.
select
    county,
    count(*)                                                                 as sales,
    percentile_cont(0.5) within group (order by price_gbp)::integer          as median_price_gbp,
    round(100.0 * avg(case when is_new_build then 1 else 0 end), 1)          as new_build_pct,
    round(100.0 * avg(case when property_type = 'Flat / maisonette' then 1 else 0 end), 1) as flats_pct,
    min(sale_date)                                                           as first_sale,
    max(sale_date)                                                           as last_sale
from {{ ref('fct_sales') }}
group by county
