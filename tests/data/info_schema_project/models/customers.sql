select id as customer_id, name from {{ ref('raw_customers') }}
