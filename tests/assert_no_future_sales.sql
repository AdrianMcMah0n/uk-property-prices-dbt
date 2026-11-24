-- Fails if a sale is dated after the day it was loaded (a parsing or source error).
select s.transaction_id, s.sale_date
from {{ ref('stg_price_paid') }} s
where s.sale_date > current_date
