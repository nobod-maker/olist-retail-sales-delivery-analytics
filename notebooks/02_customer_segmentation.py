"""
Customer RFM Segmentation & Cohort Analysis
Segments Brazilian e-commerce customers into behavioral cohorts based on Recency,
Frequency, and Monetary quintiles. Exports scored customer segments for Power BI & Excel.
"""

import os
import sqlite3
import pandas as pd
import numpy as np

def run_rfm_segmentation():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    db_path = os.path.join(project_root, 'olist.db')
    if not os.path.exists(db_path):
        db_path = os.path.join(project_root, 'sql', 'olist.db')

    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    
    # 1. Extract Customer Purchasing History
    query = """
    SELECT 
        c.customer_unique_id,
        f.order_id,
        d.full_date AS purchase_date,
        f.price,
        f.freight_value,
        f.total_item_value,
        c.customer_state,
        c.customer_region
    FROM fact_order_items f
    JOIN dim_customers c ON f.customer_key = c.customer_key
    JOIN dim_date d ON f.order_date_key = d.date_key
    WHERE f.order_status = 'delivered';
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print("\n" + "="*70)
    print("CUSTOMER RFM SEGMENTATION ANALYSIS")
    print("="*70)
    print(f"Total delivered purchase transactions: {len(df):,}")
    
    df['purchase_date'] = pd.to_datetime(df['purchase_date'])
    reference_date = df['purchase_date'].max() + pd.Timedelta(days=1)
    print(f"Reference snapshot date: {reference_date.strftime('%Y-%m-%d')}")
    
    # 2. Compute Raw R, F, M per customer_unique_id
    rfm = df.groupby('customer_unique_id').agg(
        last_purchase_date=('purchase_date', 'max'),
        frequency=('order_id', 'nunique'),
        monetary_spend=('price', 'sum'),
        total_gmv=('total_item_value', 'sum'),
        customer_state=('customer_state', 'first'),
        customer_region=('customer_region', 'first')
    ).reset_index()
    
    rfm['recency_days'] = (reference_date - rfm['last_purchase_date']).dt.days
    
    print(f"\nUnique Customers Analyzed: {len(rfm):,}")
    print(f"Repeat Buyers (Frequency >= 2): {(rfm['frequency'] >= 2).sum():,} ({(rfm['frequency'] >= 2).mean()*100:.2f}%)")
    print(f"Max Frequency: {rfm['frequency'].max()} orders")
    print(f"Average Spend: R$ {rfm['monetary_spend'].mean():.2f}")
    
    # 3. Scoring (1 to 5)
    # Recency: 5 = most recent (lowest days), 1 = least recent
    rfm['r_score'] = pd.qcut(rfm['recency_days'], q=5, labels=[5, 4, 3, 2, 1], duplicates='drop').astype(int)
    
    # Monetary: 5 = highest spend, 1 = lowest spend
    rfm['m_score'] = pd.qcut(rfm['monetary_spend'], q=5, labels=[1, 2, 3, 4, 5], duplicates='drop').astype(int)
    
    # Frequency: mapped discretely due to high concentration of 1-time buyers
    def score_frequency(f):
        if f >= 3:
            return 5
        elif f == 2:
            return 3
        else:
            return 1
    rfm['f_score'] = rfm['frequency'].apply(score_frequency)
    
    rfm['rfm_score_str'] = rfm['r_score'].astype(str) + rfm['f_score'].astype(str) + rfm['m_score'].astype(str)
    
    # 4. Segment Assignment
    def assign_segment(row):
        r, f, m = row['r_score'], row['f_score'], row['m_score']
        if r >= 4 and f >= 3 and m >= 4:
            return 'Champions'
        elif r >= 3 and f >= 3 and m >= 2:
            return 'Loyal Customers'
        elif r >= 4 and f == 1 and m >= 2:
            return 'Potential Loyalists'
        elif r <= 2 and f >= 3 and m >= 2:
            return 'At Risk'
        elif r <= 2 and f == 1 and m <= 2:
            return 'Lost / Inactive'
        elif r <= 2 and f == 1 and m >= 3:
            return 'Hibernating High Spenders'
        elif r >= 4 and f == 1 and m == 1:
            return 'Recent New Buyers'
        else:
            return 'Promising / Needs Attention'
            
    rfm['rfm_segment'] = rfm.apply(assign_segment, axis=1)
    
    # 5. Cohort Breakdown & Summary
    summary = rfm.groupby('rfm_segment').agg(
        customer_count=('customer_unique_id', 'count'),
        avg_recency_days=('recency_days', 'mean'),
        avg_frequency=('frequency', 'mean'),
        repeat_buyer_count=('frequency', lambda x: (x >= 2).sum()),
        avg_spend_brl=('monetary_spend', 'mean'),
        total_revenue_brl=('monetary_spend', 'sum')
    ).reset_index()
    
    total_cust = len(rfm)
    total_rev = rfm['monetary_spend'].sum()
    summary['customer_share_pct'] = (summary['customer_count'] / total_cust) * 100
    summary['revenue_share_pct'] = (summary['total_revenue_brl'] / total_rev) * 100
    summary['repeat_rate_pct'] = (summary['repeat_buyer_count'] / summary['customer_count']) * 100
    summary = summary.sort_values(by='total_revenue_brl', ascending=False)
    
    print("\n--- RFM Customer Segment Breakdown ---")
    print(f"{'Segment':<28} | {'Cust %':<7} | {'Rev %':<7} | {'Avg Spend':<10} | {'Repeat %':<8} | {'Avg Recency'}")
    print("-" * 80)
    for _, row in summary.iterrows():
        print(f"{row['rfm_segment']:<28} | {row['customer_share_pct']:>6.1f}% | {row['revenue_share_pct']:>6.1f}% | R${row['avg_spend_brl']:>8.2f} | {row['repeat_rate_pct']:>7.1f}% | {row['avg_recency_days']:.1f} days")
        
    # 6. Export rfm_customer_segments.csv
    data_dir = os.path.join(project_root, 'data')
    out_csv = os.path.join(data_dir, 'rfm_customer_segments.csv')
    rfm.to_csv(out_csv, index=False)
    print(f"\nExported {len(rfm):,} scored customers to {out_csv}")
    print("="*70 + "\n")
    return rfm

if __name__ == '__main__':
    run_rfm_segmentation()
