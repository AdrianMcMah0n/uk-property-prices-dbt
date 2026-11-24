-- Fails if any sale has a zero or negative price.
select transaction_id, price_gbp
from {{ ref('stg_price_paid') }}
where price_gbp <= 0
