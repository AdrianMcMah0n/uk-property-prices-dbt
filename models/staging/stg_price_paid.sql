-- One clean, typed row per sale. Codes are decoded, and corrections in later files win:
-- the monthly files mark each row A (added), C (changed) or D (deleted).
with ranked as (
    select
        *,
        row_number() over (
            partition by transaction_id
            order by loaded_at desc, case record_status when 'D' then 0 when 'C' then 1 else 2 end
        ) as recency
    from {{ source('raw', 'price_paid') }}
)

select
    trim(both '{}' from transaction_id)                   as transaction_id,
    price::integer                                        as price_gbp,
    date_of_transfer::timestamp::date                     as sale_date,
    nullif(trim(postcode), '')                            as postcode,
    case property_type
        when 'D' then 'Detached'
        when 'S' then 'Semi-detached'
        when 'T' then 'Terraced'
        when 'F' then 'Flat / maisonette'
        else 'Other'
    end                                                   as property_type,
    old_new = 'Y'                                         as is_new_build,
    case duration when 'F' then 'Freehold' when 'L' then 'Leasehold' else 'Unknown' end as tenure,
    initcap(town_city)                                    as town,
    initcap(district)                                     as district,
    initcap(county)                                       as county,
    ppd_category_type = 'A'                               as is_standard_sale,
    source_file
from ranked
where recency = 1
  and record_status <> 'D'
