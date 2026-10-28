-- ============================================================================
-- Olist Brazilian E-Commerce Analytics Platform
-- Production Analytical SQL Queries & KPI Transformations
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query 1: Monthly Revenue & Month-over-Month (MoM) Growth via LAG()
-- Business Purpose: Measure top-line revenue velocity and seasonal growth rates.
-- ----------------------------------------------------------------------------
WITH monthly_rev AS (
    SELECT 
        STRFTIME('%Y-%m', d.full_date) AS year_month,
        ROUND(SUM(f.price), 2) AS total_revenue,
        ROUND(SUM(f.total_item_value), 2) AS total_gmv,
        COUNT(DISTINCT f.order_id) AS total_orders,
        COUNT(f.order_item_key) AS total_items_sold
    FROM fact_order_items f
    JOIN dim_date d ON f.order_date_key = d.date_key
    WHERE f.order_status = 'delivered'
    GROUP BY 1
)
SELECT 
    year_month,
    total_revenue,
    total_gmv,
    total_orders,
    total_items_sold,
    LAG(total_revenue, 1) OVER (ORDER BY year_month) AS prior_month_revenue,
    ROUND(
        ((total_revenue - LAG(total_revenue, 1) OVER (ORDER BY year_month)) / 
        LAG(total_revenue, 1) OVER (ORDER BY year_month)) * 100.0, 
        2
    ) AS mom_revenue_growth_pct
FROM monthly_rev
ORDER BY year_month;

-- ----------------------------------------------------------------------------
-- Query 2: Top 10 Product Categories by Revenue & Share of Total GMV
-- Business Purpose: Identify core merchandising drivers and concentration risk.
-- ----------------------------------------------------------------------------
WITH cat_sales AS (
    SELECT 
        p.category_name_en AS category,
        COUNT(DISTINCT f.order_id) AS total_orders,
        COUNT(f.order_item_key) AS total_units_sold,
        ROUND(SUM(f.price), 2) AS total_revenue,
        ROUND(AVG(f.price), 2) AS avg_item_price
    FROM fact_order_items f
    JOIN dim_products p ON f.product_key = p.product_key
    WHERE f.order_status = 'delivered'
    GROUP BY 1
)
SELECT 
    category,
    total_orders,
    total_units_sold,
    total_revenue,
    avg_item_price,
    ROUND(total_revenue * 100.0 / SUM(total_revenue) OVER (), 2) AS gmv_share_pct,
    RANK() OVER (ORDER BY total_revenue DESC) AS category_rank
FROM cat_sales
ORDER BY total_revenue DESC
LIMIT 10;

-- ----------------------------------------------------------------------------
-- Query 3: State-Level Logistics Delivery SLA & Delay Ranking
-- Business Purpose: Benchmark regional carrier performance and pinpoint bottleneck states.
-- ----------------------------------------------------------------------------
SELECT 
    c.customer_state,
    c.customer_region,
    COUNT(DISTINCT f.order_id) AS total_delivered_orders,
    SUM(CASE WHEN f.is_late = 1 THEN 1 ELSE 0 END) AS late_orders,
    ROUND(AVG(CASE WHEN f.is_late = 1 THEN 1.0 ELSE 0.0 END) * 100.0, 2) AS late_order_pct,
    ROUND(AVG(f.actual_delivery_days), 1) AS avg_actual_delivery_days,
    ROUND(AVG(f.estimated_delivery_days), 1) AS avg_estimated_delivery_days,
    ROUND(AVG(f.delivery_delay_days), 1) AS avg_delay_days,
    ROUND(AVG(f.review_score), 2) AS avg_review_score,
    DENSE_RANK() OVER (ORDER BY AVG(CASE WHEN f.is_late = 1 THEN 1.0 ELSE 0.0 END) DESC) AS delay_risk_rank
FROM fact_order_items f
JOIN dim_customers c ON f.customer_key = c.customer_key
WHERE f.order_status = 'delivered'
GROUP BY c.customer_state, c.customer_region
ORDER BY late_order_pct DESC;

-- ----------------------------------------------------------------------------
-- Query 4: Customer Repeat Purchase Rate & Lifetime Value Analysis
-- Business Purpose: Measure customer retention, loyalty, and spend expansion.
-- ----------------------------------------------------------------------------
WITH customer_orders AS (
    SELECT 
        c.customer_unique_id,
        COUNT(DISTINCT f.order_id) AS total_orders,
        SUM(f.price) AS total_spend
    FROM fact_order_items f
    JOIN dim_customers c ON f.customer_key = c.customer_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT 
    COUNT(customer_unique_id) AS total_unique_customers,
    SUM(CASE WHEN total_orders >= 2 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(SUM(CASE WHEN total_orders >= 2 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(customer_unique_id), 2) AS repeat_purchase_rate_pct,
    ROUND(AVG(CASE WHEN total_orders >= 2 THEN total_spend END), 2) AS avg_repeat_customer_spend,
    ROUND(AVG(CASE WHEN total_orders = 1 THEN total_spend END), 2) AS avg_one_time_customer_spend,
    ROUND(
        (AVG(CASE WHEN total_orders >= 2 THEN total_spend END) - AVG(CASE WHEN total_orders = 1 THEN total_spend END)) * 100.0 / 
        AVG(CASE WHEN total_orders = 1 THEN total_spend END), 
        2
    ) AS repeat_customer_spend_lift_pct
FROM customer_orders;

-- ----------------------------------------------------------------------------
-- Query 5: Seller Operations Scorecard & Dual Performance Ranking
-- Business Purpose: Identify high-volume merchants with high vs low satisfaction ratings.
-- ----------------------------------------------------------------------------
WITH seller_metrics AS (
    SELECT 
        s.seller_id,
        s.seller_state,
        s.seller_region,
        COUNT(DISTINCT f.order_id) AS total_orders,
        COUNT(f.order_item_key) AS total_items_sold,
        ROUND(SUM(f.price), 2) AS total_revenue,
        ROUND(AVG(f.review_score), 2) AS avg_review_score,
        ROUND(AVG(CASE WHEN f.is_late = 1 THEN 1.0 ELSE 0.0 END) * 100.0, 2) AS late_fulfillment_pct
    FROM fact_order_items f
    JOIN dim_sellers s ON f.seller_key = s.seller_key
    WHERE f.order_status = 'delivered'
    GROUP BY s.seller_id, s.seller_state, s.seller_region
    HAVING COUNT(DISTINCT f.order_id) >= 10
)
SELECT 
    seller_id,
    seller_state,
    seller_region,
    total_orders,
    total_items_sold,
    total_revenue,
    avg_review_score,
    late_fulfillment_pct,
    RANK() OVER (ORDER BY total_revenue DESC) AS revenue_rank,
    DENSE_RANK() OVER (ORDER BY avg_review_score DESC) AS satisfaction_rank
FROM seller_metrics
ORDER BY total_revenue DESC
LIMIT 50;

-- ----------------------------------------------------------------------------
-- Query 6: Quantitative Impact of Shipping Delays on Customer Review Scores
-- Business Purpose: Provide definitive empirical evidence for executive operations.
-- ----------------------------------------------------------------------------
SELECT 
    CASE 
        WHEN f.is_late = 1 THEN 'Late Delivery (> Promised SLA)'
        ELSE 'On-Time / Early Delivery (<= SLA)'
    END AS delivery_performance,
    COUNT(DISTINCT f.order_id) AS total_orders,
    ROUND(AVG(f.review_score), 3) AS avg_review_score,
    ROUND(SUM(CASE WHEN f.review_score = 5 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 2) AS five_star_pct,
    ROUND(SUM(CASE WHEN f.review_score = 4 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 2) AS four_star_pct,
    ROUND(SUM(CASE WHEN f.review_score = 3 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 2) AS three_star_pct,
    ROUND(SUM(CASE WHEN f.review_score = 2 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 2) AS two_star_pct,
    ROUND(SUM(CASE WHEN f.review_score = 1 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 2) AS one_star_pct
FROM fact_order_items f
WHERE f.order_status = 'delivered'
  AND f.review_score IS NOT NULL
GROUP BY 1;
