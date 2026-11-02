# Business rules and assumptions

1. All dates use ISO `YYYY-MM-DD`; timestamps are not modeled.
2. `orders.status = 'cancelled'` excludes the order from sales and profit metrics.
3. `discount` is a fraction, e.g. `0.10` means 10%.
4. `returns.refund_amount` is the recorded monetary refund; a return can include only part of an item's quantity.
5. For net sales, aggregate refunds by `order_item_id` before joining to item rows if multiple return rows are possible.
6. Payments may be split. Aggregate payments by `order_id` before joining them to order items.
7. `customer_lifetime_value` means historical cumulative net sales, not predictive future value.
8. The semantic catalog is OKF-inspired. Formal conformance is not asserted.
