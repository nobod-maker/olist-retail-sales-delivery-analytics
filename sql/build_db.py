"""
Build and Populate Olist SQLite Database (olist.db)
Executes star-schema DDL, loads and transforms synthetic/raw CSVs into dimensions and facts,
validates analytical queries, and creates the reporting view.
"""

import os
import sys
import sqlite3
import shutil
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

STATE_REGIONS = {
    'SP': 'Southeast', 'RJ': 'Southeast', 'MG': 'Southeast', 'ES': 'Southeast',
    'RS': 'South', 'PR': 'South', 'SC': 'South',
    'BA': 'Northeast', 'PE': 'Northeast', 'CE': 'Northeast', 'MA': 'Northeast',
    'PB': 'Northeast', 'RN': 'Northeast', 'AL': 'Northeast', 'PI': 'Northeast', 'SE': 'Northeast',
    'DF': 'Central-West', 'GO': 'Central-West', 'MT': 'Central-West', 'MS': 'Central-West',
    'PA': 'North', 'AM': 'North', 'RO': 'North', 'TO': 'North', 'AC': 'North', 'AP': 'North', 'RR': 'North'
}

def to_date_key(dt_val):
    if pd.isna(dt_val) or dt_val is None:
        return None
    if isinstance(dt_val, str):
        try:
            dt = datetime.strptime(dt_val[:10], '%Y-%m-%d')
        except ValueError:
            return None
    elif isinstance(dt_val, (datetime, pd.Timestamp)):
        dt = dt_val
    else:
        return None
    return int(dt.strftime('%Y%m%d'))

def build_database():
    start_time = time.time()
    
    # Determine base directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    data_dir = os.path.join(project_root, 'data')
    sql_dir = script_dir
    
    db_path = os.path.join(sql_dir, 'olist.db')
    root_db_path = os.path.join(project_root, 'olist.db')
    
    print(f"Building Olist SQLite database at {db_path}...")
    
    # Remove existing DB if present to ensure clean rebuild
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Execute schema.sql
    schema_path = os.path.join(sql_dir, 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)
    conn.commit()
    print("Star-schema DDL executed successfully.")
    
    # 2. Populate dim_date
    print("Populating dim_date (2016-01-01 to 2018-12-31)...")
    cur_date = datetime(2016, 1, 1)
    end_date = datetime(2018, 12, 31)
    date_records = []
    
    while cur_date <= end_date:
        d_key = int(cur_date.strftime('%Y%m%d'))
        full_d = cur_date.strftime('%Y-%m-%d')
        year = cur_date.year
        quarter = (cur_date.month - 1) // 3 + 1
        month = cur_date.month
        month_name = cur_date.strftime('%B')
        week_num = int(cur_date.strftime('%W')) + 1
        day_m = cur_date.day
        day_w = cur_date.weekday() + 1 # 1 = Monday, 7 = Sunday
        day_name = cur_date.strftime('%A')
        is_wknd = 1 if cur_date.weekday() >= 5 else 0
        
        date_records.append((
            d_key, full_d, year, quarter, month, month_name,
            week_num, day_m, day_w, day_name, is_wknd
        ))
        cur_date += timedelta(days=1)
        
    cursor.executemany("""
        INSERT INTO dim_date (
            date_key, full_date, year, quarter, month, month_name,
            week_of_year, day_of_month, day_of_week, day_name, is_weekend
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, date_records)
    conn.commit()
    print(f"Inserted {len(date_records)} calendar dates into dim_date.")
    
    # 3. Populate dim_customers
    print("Populating dim_customers...")
    df_customers = pd.read_csv(os.path.join(data_dir, 'olist_customers_dataset.csv'))
    df_customers['customer_region'] = df_customers['customer_state'].map(lambda s: STATE_REGIONS.get(s, 'Other'))
    
    cust_records = []
    for _, row in df_customers.iterrows():
        cust_records.append((
            row['customer_id'],
            row['customer_unique_id'],
            str(row['customer_zip_code_prefix']),
            row['customer_city'],
            row['customer_state'],
            row['customer_region']
        ))
        
    cursor.executemany("""
        INSERT INTO dim_customers (
            customer_id, customer_unique_id, customer_zip_code_prefix,
            customer_city, customer_state, customer_region
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, cust_records)
    conn.commit()
    print(f"Inserted {len(cust_records)} records into dim_customers.")
    
    # 4. Populate dim_products
    print("Populating dim_products...")
    df_products = pd.read_csv(os.path.join(data_dir, 'olist_products_dataset.csv'))
    df_trans = pd.read_csv(os.path.join(data_dir, 'product_category_name_translation.csv'))
    
    trans_map = dict(zip(df_trans['product_category_name'], df_trans['product_category_name_english']))
    
    prod_records = []
    for _, row in df_products.iterrows():
        cat_pt = row['product_category_name'] if pd.notna(row['product_category_name']) else None
        cat_en = trans_map.get(cat_pt, cat_pt)
        weight_g = int(row['product_weight_g']) if pd.notna(row['product_weight_g']) else 0
        l = float(row['product_length_cm']) if pd.notna(row['product_length_cm']) else 0
        h = float(row['product_height_cm']) if pd.notna(row['product_height_cm']) else 0
        w = float(row['product_width_cm']) if pd.notna(row['product_width_cm']) else 0
        vol_cm3 = int(l * h * w)
        
        if weight_g < 1000:
            weight_tier = 'Light (<1kg)'
        elif weight_g <= 5000:
            weight_tier = 'Medium (1-5kg)'
        else:
            weight_tier = 'Heavy (>5kg)'
            
        prod_records.append((
            row['product_id'],
            cat_pt,
            cat_en,
            weight_g,
            vol_cm3,
            weight_tier
        ))
        
    cursor.executemany("""
        INSERT INTO dim_products (
            product_id, category_name_pt, category_name_en,
            product_weight_g, product_volume_cm3, weight_tier
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, prod_records)
    conn.commit()
    print(f"Inserted {len(prod_records)} records into dim_products.")
    
    # 5. Populate dim_sellers
    print("Populating dim_sellers...")
    df_sellers = pd.read_csv(os.path.join(data_dir, 'olist_sellers_dataset.csv'))
    df_sellers['seller_region'] = df_sellers['seller_state'].map(lambda s: STATE_REGIONS.get(s, 'Other'))
    
    seller_records = []
    for _, row in df_sellers.iterrows():
        seller_records.append((
            row['seller_id'],
            str(row['seller_zip_code_prefix']),
            row['seller_city'],
            row['seller_state'],
            row['seller_region']
        ))
        
    cursor.executemany("""
        INSERT INTO dim_sellers (
            seller_id, seller_zip_code_prefix, seller_city,
            seller_state, seller_region
        ) VALUES (?, ?, ?, ?, ?)
    """, seller_records)
    conn.commit()
    print(f"Inserted {len(seller_records)} records into dim_sellers.")
    
    # Create lookup maps for surrogate keys
    cursor.execute("SELECT customer_id, customer_key FROM dim_customers;")
    cust_key_map = dict(cursor.fetchall())
    
    cursor.execute("SELECT product_id, product_key FROM dim_products;")
    prod_key_map = dict(cursor.fetchall())
    
    cursor.execute("SELECT seller_id, seller_key FROM dim_sellers;")
    seller_key_map = dict(cursor.fetchall())
    
    # 6. Populate fact_order_items
    print("Populating fact_order_items...")
    df_orders = pd.read_csv(os.path.join(data_dir, 'olist_orders_dataset.csv'))
    df_items = pd.read_csv(os.path.join(data_dir, 'olist_order_items_dataset.csv'))
    df_reviews = pd.read_csv(os.path.join(data_dir, 'olist_order_reviews_dataset.csv'))
    
    # De-duplicate reviews per order by taking average or latest review score
    rev_map = df_reviews.groupby('order_id')['review_score'].mean().round().to_dict()
    
    orders_map = df_orders.set_index('order_id').to_dict(orient='index')
    
    fact_records = []
    for _, row in df_items.iterrows():
        oid = row['order_id']
        o_info = orders_map.get(oid)
        if not o_info:
            continue
            
        c_key = cust_key_map.get(o_info['customer_id'])
        p_key = prod_key_map.get(row['product_id'])
        s_key = seller_key_map.get(row['seller_id'])
        
        if not c_key or not p_key or not s_key:
            continue
            
        purch_dt = pd.to_datetime(o_info['order_purchase_timestamp'])
        est_dt = pd.to_datetime(o_info['order_estimated_delivery_date'])
        del_dt = pd.to_datetime(o_info['order_delivered_customer_date']) if pd.notna(o_info['order_delivered_customer_date']) else None
        
        order_date_key = to_date_key(purch_dt)
        est_date_key = to_date_key(est_dt)
        del_date_key = to_date_key(del_dt) if del_dt else None
        
        price = float(row['price'])
        freight = float(row['freight_value'])
        total_val = round(price + freight, 2)
        
        if del_dt and pd.notna(del_dt):
            delay_days = (del_dt.date() - est_dt.date()).days
            act_days = (del_dt.date() - purch_dt.date()).days
            is_late = 1 if delay_days > 0 else 0
        else:
            delay_days = None
            act_days = None
            is_late = 0
            
        est_days = (est_dt.date() - purch_dt.date()).days
        score = int(rev_map.get(oid)) if oid in rev_map else None
        
        fact_records.append((
            oid,
            int(row['order_item_id']),
            o_info['order_status'],
            order_date_key,
            del_date_key,
            est_date_key,
            c_key,
            p_key,
            s_key,
            price,
            freight,
            total_val,
            delay_days,
            act_days,
            est_days,
            is_late,
            score
        ))
        
    cursor.executemany("""
        INSERT INTO fact_order_items (
            order_id, order_item_id, order_status,
            order_date_key, delivery_date_key, estimated_date_key,
            customer_key, product_key, seller_key,
            price, freight_value, total_item_value,
            delivery_delay_days, actual_delivery_days, estimated_delivery_days,
            is_late, review_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, fact_records)
    conn.commit()
    print(f"Inserted {len(fact_records)} records into fact_order_items.")
    
    # Copy DB to project root so tools expecting olist.db at project root can find it
    shutil.copyfile(db_path, root_db_path)
    print(f"Copied olist.db to {root_db_path}")
    
    # 7. Test Analytical Queries from queries.sql
    print("\n=== EXECUTING & TESTING QUERIES FROM queries.sql ===")
    queries_file = os.path.join(sql_dir, 'queries.sql')
    with open(queries_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Split queries by semicolon outside CTE comments
    raw_queries = [q.strip() for q in content.split(';') if q.strip() and not q.strip().startswith('--')]
    
    query_names = [
        "Query 1: Monthly Revenue & MoM Growth",
        "Query 2: Top 10 Product Categories by GMV",
        "Query 3: State Delivery SLA & Delay Ranking",
        "Query 4: Customer Repeat Purchase Rate",
        "Query 5: Seller Operations Scorecard",
        "Query 6: Shipping Delay vs Review Scores"
    ]
    
    q_idx = 0
    for block in raw_queries:
        lines = [l for l in block.split('\n') if not l.strip().startswith('--')]
        clean_q = '\n'.join(lines).strip()
        if not clean_q:
            continue
            
        q_label = query_names[q_idx] if q_idx < len(query_names) else f"Query {q_idx+1}"
        q_start = time.time()
        df_res = pd.read_sql_query(clean_q, conn)
        q_duration = (time.time() - q_start) * 1000
        
        print(f"\n[PASS] {q_label} ({len(df_res)} rows returned in {q_duration:.1f}ms)")
        print(df_res.head(3).to_string(index=False))
        assert len(df_res) > 0, f"{q_label} returned 0 rows!"
        q_idx += 1
        
    # 8. Export vw_order_master to CSV for Power BI / modeling ingestion
    print("\nExporting vw_order_master.csv...")
    vw_df = pd.read_sql_query("SELECT * FROM vw_order_master LIMIT 50000;", conn)
    csv_out = os.path.join(data_dir, 'vw_order_master.csv')
    vw_df.to_csv(csv_out, index=False)
    print(f"Exported {len(vw_df):,} rows to {csv_out}")
    
    conn.close()
    elapsed = time.time() - start_time
    print(f"\n[SUCCESS] Olist SQLite database and queries built and verified in {elapsed:.2f} seconds.")

if __name__ == '__main__':
    build_database()
