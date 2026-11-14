select id as order_id, customer_id, amount from {{ ref('raw_orders') }}
