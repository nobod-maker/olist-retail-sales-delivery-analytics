-- ============================================================================
-- Olist Brazilian E-Commerce Analytics Platform
-- Star-Schema Dimensional Model DDL (SQLite / DuckDB Compatible)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. Dimension: Date (Calendar Hierarchy)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,           -- Format: YYYYMMDD
    full_date DATE NOT NULL UNIQUE,          -- ISO Date: YYYY-MM-DD
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    week_of_year INTEGER NOT NULL,
    day_of_month INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    is_weekend INTEGER NOT NULL              -- 1 = Saturday/Sunday, 0 = Weekday
);

-- ----------------------------------------------------------------------------
-- 2. Dimension: Customers (Demographics & Macro-Regions)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS dim_customers;
CREATE TABLE dim_customers (
    customer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL UNIQUE,        -- Transactional order-level token
    customer_unique_id TEXT NOT NULL,       -- Natural individual person identifier
    customer_zip_code_prefix TEXT NOT NULL,
    customer_city TEXT NOT NULL,
    customer_state TEXT NOT NULL,
    customer_region TEXT NOT NULL            -- Southeast, South, Northeast, North, Central-West
);

CREATE INDEX IF NOT EXISTS idx_dim_cust_unique ON dim_customers(customer_unique_id);
CREATE INDEX IF NOT EXISTS idx_dim_cust_state ON dim_customers(customer_state);

-- ----------------------------------------------------------------------------
-- 3. Dimension: Products (Attributes, Categorization & Weight Tiers)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products (
    product_key INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL UNIQUE,
    category_name_pt TEXT,
    category_name_en TEXT,
    product_weight_g INTEGER,
    product_volume_cm3 INTEGER,
    weight_tier TEXT                         -- Light (<1kg), Medium (1-5kg), Heavy (>5kg)
);

CREATE INDEX IF NOT EXISTS idx_dim_prod_cat ON dim_products(category_name_en);

-- ----------------------------------------------------------------------------
-- 4. Dimension: Sellers (Merchants & Geographical Hubs)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS dim_sellers;
CREATE TABLE dim_sellers (
    seller_key INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id TEXT NOT NULL UNIQUE,
    seller_zip_code_prefix TEXT NOT NULL,
    seller_city TEXT NOT NULL,
    seller_state TEXT NOT NULL,
    seller_region TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dim_seller_state ON dim_sellers(seller_state);

-- ----------------------------------------------------------------------------
-- 5. Fact Table: Order Items (Transactions, SLA Delays & Reviews)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS fact_order_items;
CREATE TABLE fact_order_items (
    order_item_key INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,                  -- Degenerate Dimension
    order_item_id INTEGER NOT NULL,          -- Degenerate Dimension
    order_status TEXT NOT NULL,              -- Degenerate Dimension (delivered, shipped, etc.)
    order_date_key INTEGER NOT NULL,         -- FK -> dim_date.date_key
    delivery_date_key INTEGER,               -- FK -> dim_date.date_key (NULL if not delivered)
    estimated_date_key INTEGER NOT NULL,     -- FK -> dim_date.date_key
    customer_key INTEGER NOT NULL,           -- FK -> dim_customers.customer_key
    product_key INTEGER NOT NULL,            -- FK -> dim_products.product_key
    seller_key INTEGER NOT NULL,             -- FK -> dim_sellers.seller_key
    price REAL NOT NULL,
    freight_value REAL NOT NULL,
    total_item_value REAL NOT NULL,          -- price + freight_value
    delivery_delay_days INTEGER,             -- delivered_date - estimated_date (>0 = late)
    actual_delivery_days INTEGER,            -- delivered_date - purchase_date
    estimated_delivery_days INTEGER,         -- estimated_date - purchase_date
    is_late INTEGER NOT NULL DEFAULT 0,      -- 1 = late, 0 = on-time / early
    review_score INTEGER,                    -- Customer CSAT score (1 to 5)
    FOREIGN KEY (order_date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (delivery_date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (estimated_date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (customer_key) REFERENCES dim_customers(customer_key),
    FOREIGN KEY (product_key) REFERENCES dim_products(product_key),
    FOREIGN KEY (seller_key) REFERENCES dim_sellers(seller_key)
);

CREATE INDEX IF NOT EXISTS idx_fact_order ON fact_order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_fact_order_date ON fact_order_items(order_date_key);
CREATE INDEX IF NOT EXISTS idx_fact_customer ON fact_order_items(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_product ON fact_order_items(product_key);
CREATE INDEX IF NOT EXISTS idx_fact_seller ON fact_order_items(seller_key);
CREATE INDEX IF NOT EXISTS idx_fact_is_late ON fact_order_items(is_late);

-- ----------------------------------------------------------------------------
-- 6. Master Reporting View: vw_order_master
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_order_master;
CREATE VIEW vw_order_master AS
SELECT 
    f.order_item_key,
    f.order_id,
    f.order_item_id,
    f.order_status,
    d_ord.full_date AS order_purchase_date,
    d_ord.year AS order_year,
    d_ord.month AS order_month,
    d_ord.month_name AS order_month_name,
    d_ord.quarter AS order_quarter,
    d_del.full_date AS order_delivered_date,
    d_est.full_date AS order_estimated_date,
    c.customer_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    c.customer_region,
    p.product_id,
    COALESCE(p.category_name_en, p.category_name_pt, 'Unknown') AS product_category,
    p.weight_tier,
    s.seller_id,
    s.seller_city,
    s.seller_state,
    s.seller_region,
    f.price,
    f.freight_value,
    f.total_item_value,
    f.delivery_delay_days,
    f.actual_delivery_days,
    f.estimated_delivery_days,
    f.is_late,
    f.review_score
FROM fact_order_items f
JOIN dim_date d_ord ON f.order_date_key = d_ord.date_key
LEFT JOIN dim_date d_del ON f.delivery_date_key = d_del.date_key
JOIN dim_date d_est ON f.estimated_date_key = d_est.date_key
JOIN dim_customers c ON f.customer_key = c.customer_key
JOIN dim_products p ON f.product_key = p.product_key
JOIN dim_sellers s ON f.seller_key = s.seller_key;
