-- Standard residential sales only (category A). Category B covers repossessions, buy-to-let
-- and transfers to companies, which would distort typical prices.
select
    transaction_id,
    sale_date,
    date_trunc('month', sale_date)::date as sale_month,
    price_gbp,
    property_type,
    is_new_build,
    tenure,
    town,
    district,
    county,
    split_part(postcode, ' ', 1)          as postcode_area
from {{ ref('stg_price_paid') }}
where is_standard_sale
