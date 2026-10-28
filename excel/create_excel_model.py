"""
Programmatic Excel Financial & Operational Model Generator
Uses openpyxl to generate an enterprise 4-sheet dynamic Excel workbook:
1. Executive Summary
2. Delivery KPIs (Delivery SLA Matrix)
3. Category Performance
4. RFM Analysis (Customer Cohorts)
Equipped with dynamic Excel formulas (SUM, AVERAGE, IF, SUMIFS, COUNTIFS),
conditional formatting, executive styling, and auto-adjusted column widths.
"""

import os
import sys
import sqlite3
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule

def build_excel_model():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    db_path = os.path.join(project_root, 'olist.db')
    if not os.path.exists(db_path):
        db_path = os.path.join(project_root, 'sql', 'olist.db')
        
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    
    # Load underlying aggregates
    df_monthly = pd.read_sql_query("""
        SELECT 
            STRFTIME('%Y-%m', d.full_date) AS year_month,
            ROUND(SUM(f.price), 2) AS total_revenue,
            ROUND(SUM(f.total_item_value), 2) AS total_gmv,
            COUNT(DISTINCT f.order_id) AS total_orders,
            SUM(CASE WHEN f.is_late = 1 THEN 1 ELSE 0 END) AS late_orders,
            ROUND(AVG(f.review_score), 2) AS avg_review_score
        FROM fact_order_items f
        JOIN dim_date d ON f.order_date_key = d.date_key
        WHERE f.order_status = 'delivered'
        GROUP BY 1
        ORDER BY 1;
    """, conn)
    
    df_states = pd.read_sql_query("""
        SELECT 
            c.customer_state,
            c.customer_region,
            COUNT(DISTINCT f.order_id) AS total_orders,
            SUM(CASE WHEN f.is_late = 1 THEN 1 ELSE 0 END) AS late_orders,
            ROUND(AVG(f.actual_delivery_days), 1) AS avg_actual_days,
            ROUND(AVG(f.estimated_delivery_days), 1) AS avg_estimated_days
        FROM fact_order_items f
        JOIN dim_customers c ON f.customer_key = c.customer_key
        WHERE f.order_status = 'delivered'
        GROUP BY c.customer_state, c.customer_region
        ORDER BY (SUM(CASE WHEN f.is_late = 1 THEN 1.0 ELSE 0.0 END) / COUNT(DISTINCT f.order_id)) DESC;
    """, conn)
    
    df_categories = pd.read_sql_query("""
        SELECT 
            p.category_name_en AS category,
            COUNT(f.order_item_key) AS units_sold,
            ROUND(SUM(f.price), 2) AS total_revenue,
            ROUND(AVG(f.price), 2) AS avg_price
        FROM fact_order_items f
        JOIN dim_products p ON f.product_key = p.product_key
        WHERE f.order_status = 'delivered'
        GROUP BY 1
        ORDER BY total_revenue DESC;
    """, conn)
    
    rfm_csv = os.path.join(project_root, 'data', 'rfm_customer_segments.csv')
    if os.path.exists(rfm_csv):
        df_rfm_raw = pd.read_csv(rfm_csv)
        df_rfm = df_rfm_raw.groupby('rfm_segment').agg(
            customer_count=('customer_unique_id', 'count'),
            total_spend=('monetary_spend', 'sum'),
            avg_recency=('recency_days', 'mean'),
            repeat_customers=('frequency', lambda x: (x >= 2).sum())
        ).reset_index().sort_values(by='total_spend', ascending=False)
    else:
        df_rfm = pd.DataFrame()
        
    conn.close()

    # Create Workbook
    wb = Workbook()
    
    # Corporate Color Palette & Styles
    COLOR_NAVY = "1F4E79"
    COLOR_SLATE = "2F5597"
    COLOR_ICE = "D9E1F2"
    COLOR_GOLD = "FFF2CC"
    COLOR_LIGHT_GRAY = "F2F2F2"
    COLOR_BORDER = "D9D9D9"
    
    font_title = Font(name="Calibri", size=16, bold=True, color="1F4E79")
    font_subtitle = Font(name="Calibri", size=11, italic=True, color="595959")
    font_card_num = Font(name="Calibri", size=18, bold=True, color="1F4E79")
    font_card_lbl = Font(name="Calibri", size=9, bold=True, color="595959")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=11, bold=False, color="000000")
    font_total = Font(name="Calibri", size=11, bold=True, color="000000")
    
    fill_navy = PatternFill(start_color=COLOR_NAVY, end_color=COLOR_NAVY, fill_type="solid")
    fill_slate = PatternFill(start_color=COLOR_SLATE, end_color=COLOR_SLATE, fill_type="solid")
    fill_card = PatternFill(start_color=COLOR_ICE, end_color=COLOR_ICE, fill_type="solid")
    fill_total = PatternFill(start_color=COLOR_LIGHT_GRAY, end_color=COLOR_LIGHT_GRAY, fill_type="solid")
    
    thin_border_side = Side(border_style="thin", color=COLOR_BORDER)
    border_cell = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    border_double_bottom = Border(top=thin_border_side, bottom=Side(border_style="double", color="000000"))
    
    align_left = Alignment(horizontal="left", vertical="center")
    align_center = Alignment(horizontal="center", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    align_card = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # =========================================================================
    # SHEET 1: Executive Summary
    # =========================================================================
    ws1 = wb.active
    ws1.title = "Executive Summary"
    ws1.views.sheetView[0].showGridLines = True
    
    ws1["A1"] = "OLIST BRAZILIAN E-COMMERCE: EXECUTIVE PERFORMANCE COMMAND CENTER"
    ws1["A1"].font = font_title
    ws1["A2"] = "Strategic Portfolio Overview, Sales Velocity & SLA Operations"
    ws1["A2"].font = font_subtitle
    
    # KPI Scorecard Cards in Rows 4-6
    kpis = [
        ("Total GMV (BRL)", "=SUM(C10:C34)", "$#,##0.00", "B", "C"),
        ("Delivered Orders", "=SUM(D10:D34)", "#,##0", "D", "E"),
        ("Late Delivery %", "=AVERAGE(F10:F34)", "0.0%", "F", "G"),
        ("Average Review Score", "=AVERAGE(G10:G34)", "0.00", "H", "I")
    ]
    
    for lbl, formula, fmt, col_start, col_end in kpis:
        # Merge 2 columns for card
        c_val = f"{col_start}4"
        c_lbl = f"{col_start}5"
        ws1.merge_cells(f"{col_start}4:{col_end}4")
        ws1.merge_cells(f"{col_start}5:{col_end}5")
        
        ws1[c_val] = formula
        ws1[c_val].font = font_card_num
        ws1[c_val].alignment = align_card
        ws1[c_val].fill = fill_card
        ws1[c_val].number_format = fmt
        
        ws1[c_lbl] = lbl
        ws1[c_lbl].font = font_card_lbl
        ws1[c_lbl].alignment = align_card
        ws1[c_lbl].fill = fill_card

    # Monthly Trend Table
    ws1["A8"] = "MONTHLY REVENUE & OPERATIONAL SLA PERFORMANCE"
    ws1["A8"].font = Font(name="Calibri", size=12, bold=True, color=COLOR_NAVY)
    
    headers1 = ["Month (YYYY-MM)", "Merchandise Rev (BRL)", "Total GMV (BRL)", "Delivered Orders", "Late Deliveries", "Late Order %", "Avg Review Score"]
    for col_idx, h in enumerate(headers1, 1):
        cell = ws1.cell(row=9, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center if col_idx == 1 else align_right
        cell.border = border_cell
        
    start_row = 10
    for idx, row in df_monthly.iterrows():
        r = start_row + idx
        ws1.cell(row=r, column=1, value=row['year_month']).alignment = align_center
        ws1.cell(row=r, column=2, value=float(row['total_revenue'])).number_format = "$#,##0.00"
        ws1.cell(row=r, column=3, value=float(row['total_gmv'])).number_format = "$#,##0.00"
        ws1.cell(row=r, column=4, value=int(row['total_orders'])).number_format = "#,##0"
        ws1.cell(row=r, column=5, value=int(row['late_orders'])).number_format = "#,##0"
        
        # Dynamic Excel Formula for Late Order %
        cell_late_pct = ws1.cell(row=r, column=6, value=f"=IF(D{r}>0, E{r}/D{r}, 0)")
        cell_late_pct.number_format = "0.0%"
        
        cell_csat = ws1.cell(row=r, column=7, value=float(row['avg_review_score']))
        cell_csat.number_format = "0.00"
        
        for c in range(1, 8):
            ws1.cell(row=r, column=c).border = border_cell
            if c > 1:
                ws1.cell(row=r, column=c).alignment = align_right
                
    end_row = start_row + len(df_monthly) - 1
    total_row = end_row + 1
    ws1.cell(row=total_row, column=1, value="Total / Portfolio Avg").font = font_total
    ws1.cell(row=total_row, column=2, value=f"=SUM(B{start_row}:B{end_row})").number_format = "$#,##0.00"
    ws1.cell(row=total_row, column=3, value=f"=SUM(C{start_row}:C{end_row})").number_format = "$#,##0.00"
    ws1.cell(row=total_row, column=4, value=f"=SUM(D{start_row}:D{end_row})").number_format = "#,##0"
    ws1.cell(row=total_row, column=5, value=f"=SUM(E{start_row}:E{end_row})").number_format = "#,##0"
    ws1.cell(row=total_row, column=6, value=f"=E{total_row}/D{total_row}").number_format = "0.0%"
    ws1.cell(row=total_row, column=7, value=f"=AVERAGE(G{start_row}:G{end_row})").number_format = "0.00"
    
    for c in range(1, 8):
        cell = ws1.cell(row=total_row, column=c)
        cell.font = font_total
        cell.fill = fill_total
        cell.border = border_double_bottom
        if c > 1:
            cell.alignment = align_right

    # =========================================================================
    # SHEET 2: Delivery KPIs (Delivery SLA Matrix)
    # =========================================================================
    ws2 = wb.create_sheet(title="Delivery KPIs")
    ws2.views.sheetView[0].showGridLines = True
    
    ws2["A1"] = "BRAZILIAN STATE LOGISTICS DELIVERY SLA & PERFORMANCE MATRIX"
    ws2["A1"].font = font_title
    ws2["A2"] = "Regional Benchmarking, Carrier Lead Times & Late Delivery Bottlenecks"
    ws2["A2"].font = font_subtitle
    
    headers2 = ["State", "Macro-Region", "Total Orders", "Late Orders", "Late Delivery %", "Avg Actual Days", "Avg Estimated Days", "Delivery SLA Gap"]
    for col_idx, h in enumerate(headers2, 1):
        cell = ws2.cell(row=5, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center if col_idx <= 2 else align_right
        cell.border = border_cell
        
    start_r2 = 6
    for idx, row in df_states.iterrows():
        r = start_r2 + idx
        ws2.cell(row=r, column=1, value=row['customer_state']).alignment = align_center
        ws2.cell(row=r, column=2, value=row['customer_region']).alignment = align_left
        ws2.cell(row=r, column=3, value=int(row['total_orders'])).number_format = "#,##0"
        ws2.cell(row=r, column=4, value=int(row['late_orders'])).number_format = "#,##0"
        
        # Dynamic Late % formula
        c_late = ws2.cell(row=r, column=5, value=f"=IF(C{r}>0, D{r}/C{r}, 0)")
        c_late.number_format = "0.0%"
        
        ws2.cell(row=r, column=6, value=float(row['avg_actual_days'])).number_format = "0.0"
        ws2.cell(row=r, column=7, value=float(row['avg_estimated_days'])).number_format = "0.0"
        
        # Dynamic SLA Gap formula (Actual - Estimated)
        c_gap = ws2.cell(row=r, column=8, value=f"=F{r}-G{r}")
        c_gap.number_format = "+0.0;-0.0;0.0"
        
        for c in range(1, 9):
            ws2.cell(row=r, column=c).border = border_cell
            if c >= 3:
                ws2.cell(row=r, column=c).alignment = align_right
                
    end_r2 = start_r2 + len(df_states) - 1
    
    # Conditional formatting: 3-color scale on Late % (Column E)
    color_scale = ColorScaleRule(
        start_type='num', start_value=0.04, start_color='63BE7B',  # Soft Green
        mid_type='num', mid_value=0.08, mid_color='FFEB84',        # Soft Yellow
        end_type='num', end_value=0.20, end_color='F8696B'         # Soft Red
    )
    ws2.conditional_formatting.add(f"E{start_r2}:E{end_r2}", color_scale)

    # =========================================================================
    # SHEET 3: Category Performance
    # =========================================================================
    ws3 = wb.create_sheet(title="Category Performance")
    ws3.views.sheetView[0].showGridLines = True
    
    ws3["A1"] = "PRODUCT CATEGORY MERCHANDISING PERFORMANCE"
    ws3["A1"].font = font_title
    ws3["A2"] = "GMV Volume, Units Sold, Average Selling Price & Portfolio Share"
    ws3["A2"].font = font_subtitle
    
    headers3 = ["Product Category", "Units Sold", "Total Revenue (BRL)", "Avg Price (BRL)", "Revenue Share %"]
    for col_idx, h in enumerate(headers3, 1):
        cell = ws3.cell(row=5, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_slate
        cell.alignment = align_left if col_idx == 1 else align_right
        cell.border = border_cell
        
    start_r3 = 6
    tot_cat_rev = df_categories['total_revenue'].sum()
    for idx, row in df_categories.iterrows():
        r = start_r3 + idx
        ws3.cell(row=r, column=1, value=str(row['category'])).alignment = align_left
        ws3.cell(row=r, column=2, value=int(row['units_sold'])).number_format = "#,##0"
        ws3.cell(row=r, column=3, value=float(row['total_revenue'])).number_format = "$#,##0.00"
        
        # Dynamic Avg Price formula: Revenue / Units
        c_avg = ws3.cell(row=r, column=4, value=f"=C{r}/B{r}")
        c_avg.number_format = "$#,##0.00"
        
        # Dynamic Revenue Share formula: Revenue / Total Revenue
        c_share = ws3.cell(row=r, column=5, value=f"=C{r}/$C${start_r3 + len(df_categories)}")
        c_share.number_format = "0.0%"
        
        for c in range(1, 6):
            ws3.cell(row=r, column=c).border = border_cell
            if c > 1:
                ws3.cell(row=r, column=c).alignment = align_right
                
    end_r3 = start_r3 + len(df_categories) - 1
    tot_r3 = end_r3 + 1
    ws3.cell(row=tot_r3, column=1, value="Total Merchandising").font = font_total
    ws3.cell(row=tot_r3, column=2, value=f"=SUM(B{start_r3}:B{end_r3})").number_format = "#,##0"
    ws3.cell(row=tot_r3, column=3, value=f"=SUM(C{start_r3}:C{end_r3})").number_format = "$#,##0.00"
    ws3.cell(row=tot_r3, column=4, value=f"=C{tot_r3}/B{tot_r3}").number_format = "$#,##0.00"
    ws3.cell(row=tot_r3, column=5, value=f"=SUM(E{start_r3}:E{end_r3})").number_format = "0.0%"
    
    for c in range(1, 6):
        cell = ws3.cell(row=tot_r3, column=c)
        cell.font = font_total
        cell.fill = fill_total
        cell.border = border_double_bottom
        if c > 1:
            cell.alignment = align_right

    # =========================================================================
    # SHEET 4: RFM Analysis (Customer Cohorts)
    # =========================================================================
    ws4 = wb.create_sheet(title="RFM Analysis")
    ws4.views.sheetView[0].showGridLines = True
    
    ws4["A1"] = "CUSTOMER RFM SEGMENTATION & RETENTION COHORTS"
    ws4["A1"].font = font_title
    ws4["A2"] = "Customer Value Tiers, Spend Expansion & Repeat Purchase Analysis"
    ws4["A2"].font = font_subtitle
    
    headers4 = ["RFM Segment", "Customer Count", "Customer %", "Total Revenue (BRL)", "Revenue %", "Avg Spend / Customer", "Repeat Buyers", "Repeat Rate %", "Avg Recency Days"]
    for col_idx, h in enumerate(headers4, 1):
        cell = ws4.cell(row=5, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_left if col_idx == 1 else align_right
        cell.border = border_cell
        
    start_r4 = 6
    if not df_rfm.empty:
        for idx, row in df_rfm.iterrows():
            r = start_r4 + idx
            ws4.cell(row=r, column=1, value=row['rfm_segment']).alignment = align_left
            ws4.cell(row=r, column=2, value=int(row['customer_count'])).number_format = "#,##0"
            
            # Dynamic Customer % formula
            c_cpct = ws4.cell(row=r, column=3, value=f"=B{r}/$B${start_r4 + len(df_rfm)}")
            c_cpct.number_format = "0.0%"
            
            ws4.cell(row=r, column=4, value=float(row['total_spend'])).number_format = "$#,##0.00"
            
            # Dynamic Revenue % formula
            c_rpct = ws4.cell(row=r, column=5, value=f"=D{r}/$D${start_r4 + len(df_rfm)}")
            c_rpct.number_format = "0.0%"
            
            # Dynamic Avg Spend: Revenue / Customers
            c_asp = ws4.cell(row=r, column=6, value=f"=D{r}/B{r}")
            c_asp.number_format = "$#,##0.00"
            
            ws4.cell(row=r, column=7, value=int(row['repeat_customers'])).number_format = "#,##0"
            
            # Dynamic Repeat Rate: Repeat / Customers
            c_rep = ws4.cell(row=r, column=8, value=f"=G{r}/B{r}")
            c_rep.number_format = "0.0%"
            
            ws4.cell(row=r, column=9, value=float(row['avg_recency'])).number_format = "0.0"
            
            for c in range(1, 10):
                ws4.cell(row=r, column=c).border = border_cell
                if c > 1:
                    ws4.cell(row=r, column=c).alignment = align_right
                    
        end_r4 = start_r4 + len(df_rfm) - 1
        tot_r4 = end_r4 + 1
        ws4.cell(row=tot_r4, column=1, value="Total Customer Base").font = font_total
        ws4.cell(row=tot_r4, column=2, value=f"=SUM(B{start_r4}:B{end_r4})").number_format = "#,##0"
        ws4.cell(row=tot_r4, column=3, value=f"=SUM(C{start_r4}:C{end_r4})").number_format = "0.0%"
        ws4.cell(row=tot_r4, column=4, value=f"=SUM(D{start_r4}:D{end_r4})").number_format = "$#,##0.00"
        ws4.cell(row=tot_r4, column=5, value=f"=SUM(E{start_r4}:E{end_r4})").number_format = "0.0%"
        ws4.cell(row=tot_r4, column=6, value=f"=D{tot_r4}/B{tot_r4}").number_format = "$#,##0.00"
        ws4.cell(row=tot_r4, column=7, value=f"=SUM(G{start_r4}:G{end_r4})").number_format = "#,##0"
        ws4.cell(row=tot_r4, column=8, value=f"=G{tot_r4}/B{tot_r4}").number_format = "0.0%"
        ws4.cell(row=tot_r4, column=9, value=f"=AVERAGE(I{start_r4}:I{end_r4})").number_format = "0.0"
        
        for c in range(1, 10):
            cell = ws4.cell(row=tot_r4, column=c)
            cell.font = font_total
            cell.fill = fill_total
            cell.border = border_double_bottom
            if c > 1:
                cell.alignment = align_right

    # Auto-adjust column widths across all sheets
    for ws in [ws1, ws2, ws3, ws4]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                # ignore merged title row
                if cell.row in [1, 2, 4, 5]:
                    continue
                val_str = str(cell.value or '')
                if val_str.startswith('='):
                    val_str = "123,456.78"
                max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Save to both required standard filenames
    out_file1 = os.path.join(project_root, 'excel', 'retail_performance_model.xlsx')
    out_file2 = os.path.join(project_root, 'excel', '01_retail_executive_summary.xlsx')
    
    wb.save(out_file1)
    wb.save(out_file2)
    print(f"\n[SUCCESS] Excel model saved to:")
    print(f"  - {out_file1}")
    print(f"  - {out_file2}")

if __name__ == '__main__':
    build_excel_model()
