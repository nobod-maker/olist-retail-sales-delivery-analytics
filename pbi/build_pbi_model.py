"""
Enterprise Power BI Modern PBIR & TMDL Semantic Model Builder
Generates schema-compliant PBIR (Power BI Enhanced Report Format) and TMDL (Tabular Model Definition Language)
for Olist Retail Command Center with Fabric schemas, star-schema relationships, and DAX measures.
"""

import os
import json
from pathlib import Path

def build_pbi_project():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    pbi_dir = os.path.join(project_root, 'pbi')
    
    report_name = "Olist_Retail_Command_Center"
    pbip_file = os.path.join(pbi_dir, f"{report_name}.pbip")
    report_dir = os.path.join(pbi_dir, f"{report_name}.Report")
    semantic_dir = os.path.join(pbi_dir, f"{report_name}.SemanticModel")
    
    # Ensure directories exist
    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(os.path.join(report_dir, 'definition'), exist_ok=True)
    os.makedirs(os.path.join(report_dir, 'definition', 'pages'), exist_ok=True)
    os.makedirs(semantic_dir, exist_ok=True)
    os.makedirs(os.path.join(semantic_dir, 'definition'), exist_ok=True)
    os.makedirs(os.path.join(semantic_dir, 'definition', 'tables'), exist_ok=True)
    
    print("Building modern Power BI PBIR & TMDL project...")

    # 1. Root .pbip File
    pbip_content = {
        "version": "1.0",
        "artifacts": [
            { "report": { "path": f"{report_name}.Report" } }
        ],
        "settings": {}
    }
    with open(pbip_file, 'w', encoding='utf-8') as f:
        json.dump(pbip_content, f, indent=2)
    print(f"Created {pbip_file}")

    # 2. Report definition.pbir
    pbir_content = {
        "version": "4.0",
        "datasetReference": {
            "byPath": {
                "path": f"../{report_name}.SemanticModel"
            }
        }
    }
    with open(os.path.join(report_dir, 'definition.pbir'), 'w', encoding='utf-8') as f:
        json.dump(pbir_content, f, indent=2)

    # 3. Report .platform
    report_platform = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {
            "type": "Report",
            "displayName": "Olist Retail Command Center"
        },
        "config": {
            "version": "2.0",
            "logicalId": "00000000-0000-0000-0000-000000000001"
        }
    }
    with open(os.path.join(report_dir, '.platform'), 'w', encoding='utf-8') as f:
        json.dump(report_platform, f, indent=2)

    # 4. Report definition/version.json
    version_content = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0"
    }
    with open(os.path.join(report_dir, 'definition', 'version.json'), 'w', encoding='utf-8') as f:
        json.dump(version_content, f, indent=2)

    # 5. Report definition/report.json
    report_json_content = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.2.0/schema.json",
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU02",
                "reportVersionAtImport": "5.55"
            }
        },
        "layoutOptimization": "None",
        "settings": {
            "useStylableVisualContainerHeader": True,
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True
        }
    }
    with open(os.path.join(report_dir, 'definition', 'report.json'), 'w', encoding='utf-8') as f:
        json.dump(report_json_content, f, indent=2)

    # 6. Report Pages definition
    pages_list = [
        ("page_exec", "Executive KPI Command Center"),
        ("page_sla", "Delivery & Logistics SLA"),
        ("page_rfm", "Customer Value & RFM Segmentation"),
        ("page_sellers", "Seller Operations & Scorecard")
    ]
    pages_json_content = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p[0] for p in pages_list]
    }
    with open(os.path.join(report_dir, 'definition', 'pages', 'pages.json'), 'w', encoding='utf-8') as f:
        json.dump(pages_json_content, f, indent=2)

    # Create page definitions and sample visual containers
    for page_id, display_name in pages_list:
        p_dir = os.path.join(report_dir, 'definition', 'pages', page_id)
        v_dir = os.path.join(p_dir, 'visuals')
        os.makedirs(v_dir, exist_ok=True)
        
        page_def = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
            "name": page_id,
            "displayName": display_name,
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280
        }
        with open(os.path.join(p_dir, 'page.json'), 'w', encoding='utf-8') as f:
            json.dump(page_def, f, indent=2)

        # Create sample KPI visual in each page
        vis_def = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json",
            "name": f"card_{page_id}",
            "position": {
                "x": 20,
                "y": 20,
                "z": 1000,
                "height": 120,
                "width": 240,
                "tabOrder": 1000
            },
            "visual": {
                "visualType": "card",
                "query": {
                    "queryState": {
                        "Values": {
                            "projections": ["Total GMV"]
                        }
                    }
                },
                "drillFilterOtherVisuals": True
            }
        }
        vis_subdir = os.path.join(v_dir, f"vis_{page_id}_01")
        os.makedirs(vis_subdir, exist_ok=True)
        with open(os.path.join(vis_subdir, 'visual.json'), 'w', encoding='utf-8') as f:
            json.dump(vis_def, f, indent=2)

    # 7. Semantic Model definition.pbism
    pbism_content = {
        "version": "1.0",
        "settings": {}
    }
    with open(os.path.join(semantic_dir, 'definition.pbism'), 'w', encoding='utf-8') as f:
        json.dump(pbism_content, f, indent=2)

    # 8. Semantic Model .platform
    semantic_platform = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {
            "type": "SemanticModel",
            "displayName": "Olist Retail Semantic Model"
        },
        "config": {
            "version": "2.0",
            "logicalId": "00000000-0000-0000-0000-000000000002"
        }
    }
    with open(os.path.join(semantic_dir, '.platform'), 'w', encoding='utf-8') as f:
        json.dump(semantic_platform, f, indent=2)

    # 9. TMDL model.tmdl
    model_tmdl = """model Model
\tculture: en-US
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tsourceQueryCulture: en-US
\tdataAccessOptions
\t\tlegacyRedirects
\t\treturnErrorValuesAsNull

annotation __PBI_TimeIntelligenceEnabled = 1
annotation PBIDesktopVersion = 2.138.1004.0 (24.11)
"""
    with open(os.path.join(semantic_dir, 'definition', 'model.tmdl'), 'w', encoding='utf-8') as f:
        f.write(model_tmdl)

    # 10. TMDL relationships.tmdl
    relationships_tmdl = """relationship Rel_Fact_OrderDate
\tfromColumn: fact_order_items.order_date_key
\ttoColumn: dim_date.date_key

relationship Rel_Fact_DeliveryDate
\tisActive: false
\tfromColumn: fact_order_items.delivery_date_key
\ttoColumn: dim_date.date_key

relationship Rel_Fact_EstimatedDate
\tisActive: false
\tfromColumn: fact_order_items.estimated_date_key
\ttoColumn: dim_date.date_key

relationship Rel_Fact_Customer
\tfromColumn: fact_order_items.customer_key
\ttoColumn: dim_customers.customer_key

relationship Rel_Fact_Product
\tfromColumn: fact_order_items.product_key
\ttoColumn: dim_products.product_key

relationship Rel_Fact_Seller
\tfromColumn: fact_order_items.seller_key
\ttoColumn: dim_sellers.seller_key
"""
    with open(os.path.join(semantic_dir, 'definition', 'relationships.tmdl'), 'w', encoding='utf-8') as f:
        f.write(relationships_tmdl)

    # 11. TMDL Table definitions (tables/*.tmdl)
    # dim_date
    dim_date_tmdl = """table dim_date
\tlineageTag: 10000000-0000-0000-0000-000000000001

\tcolumn date_key
\t\tdataType: int64
\t\tisKey
\t\tformatString: 0
\t\tsourceColumn: date_key

\tcolumn full_date
\t\tdataType: dateTime
\t\tformatString: yyyy-mm-dd
\t\tsourceColumn: full_date

\tcolumn year
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: year

\tcolumn quarter
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: quarter

\tcolumn month
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: month

\tcolumn month_name
\t\tdataType: string
\t\tsourceColumn: month_name

\tcolumn week_of_year
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: week_of_year

\tcolumn day_of_month
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: day_of_month

\tcolumn day_name
\t\tdataType: string
\t\tsourceColumn: day_name

\tcolumn is_weekend
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: is_weekend

\tpartition dim_date = m
\t\tmode: import
\t\tsource = 
\t\t\tlet
\t\t\t\tSource = Csv.Document(File.Contents("data/dim_date.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
\t\t\t\t#"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
\t\t\tin
\t\t\t\t#"Promoted Headers"
"""
    with open(os.path.join(semantic_dir, 'definition', 'tables', 'dim_date.tmdl'), 'w', encoding='utf-8') as f:
        f.write(dim_date_tmdl)

    # dim_customers
    dim_customers_tmdl = """table dim_customers
\tlineageTag: 10000000-0000-0000-0000-000000000002

\tcolumn customer_key
\t\tdataType: int64
\t\tisKey
\t\tformatString: 0
\t\tsourceColumn: customer_key

\tcolumn customer_id
\t\tdataType: string
\t\tsourceColumn: customer_id

\tcolumn customer_unique_id
\t\tdataType: string
\t\tsourceColumn: customer_unique_id

\tcolumn customer_city
\t\tdataType: string
\t\tsourceColumn: customer_city

\tcolumn customer_state
\t\tdataType: string
\t\tsourceColumn: customer_state

\tcolumn customer_region
\t\tdataType: string
\t\tsourceColumn: customer_region

\tpartition dim_customers = m
\t\tmode: import
\t\tsource = 
\t\t\tlet
\t\t\t\tSource = Csv.Document(File.Contents("data/olist_customers_dataset.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
\t\t\t\t#"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
\t\t\tin
\t\t\t\t#"Promoted Headers"
"""
    with open(os.path.join(semantic_dir, 'definition', 'tables', 'dim_customers.tmdl'), 'w', encoding='utf-8') as f:
        f.write(dim_customers_tmdl)

    # dim_products
    dim_products_tmdl = """table dim_products
\tlineageTag: 10000000-0000-0000-0000-000000000003

\tcolumn product_key
\t\tdataType: int64
\t\tisKey
\t\tformatString: 0
\t\tsourceColumn: product_key

\tcolumn product_id
\t\tdataType: string
\t\tsourceColumn: product_id

\tcolumn category_name_en
\t\tdataType: string
\t\tsourceColumn: category_name_en

\tcolumn product_weight_g
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: product_weight_g

\tcolumn product_volume_cm3
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: product_volume_cm3

\tcolumn weight_tier
\t\tdataType: string
\t\tsourceColumn: weight_tier

\tpartition dim_products = m
\t\tmode: import
\t\tsource = 
\t\t\tlet
\t\t\t\tSource = Csv.Document(File.Contents("data/olist_products_dataset.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
\t\t\t\t#"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
\t\t\tin
\t\t\t\t#"Promoted Headers"
"""
    with open(os.path.join(semantic_dir, 'definition', 'tables', 'dim_products.tmdl'), 'w', encoding='utf-8') as f:
        f.write(dim_products_tmdl)

    # dim_sellers
    dim_sellers_tmdl = """table dim_sellers
\tlineageTag: 10000000-0000-0000-0000-000000000004

\tcolumn seller_key
\t\tdataType: int64
\t\tisKey
\t\tformatString: 0
\t\tsourceColumn: seller_key

\tcolumn seller_id
\t\tdataType: string
\t\tsourceColumn: seller_id

\tcolumn seller_city
\t\tdataType: string
\t\tsourceColumn: seller_city

\tcolumn seller_state
\t\tdataType: string
\t\tsourceColumn: seller_state

\tcolumn seller_region
\t\tdataType: string
\t\tsourceColumn: seller_region

\tpartition dim_sellers = m
\t\tmode: import
\t\tsource = 
\t\t\tlet
\t\t\t\tSource = Csv.Document(File.Contents("data/olist_sellers_dataset.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
\t\t\t\t#"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
\t\t\tin
\t\t\t\t#"Promoted Headers"
"""
    with open(os.path.join(semantic_dir, 'definition', 'tables', 'dim_sellers.tmdl'), 'w', encoding='utf-8') as f:
        f.write(dim_sellers_tmdl)

    # fact_order_items with measures
    fact_order_items_tmdl = """table fact_order_items
\tlineageTag: 10000000-0000-0000-0000-000000000005

\tcolumn order_item_key
\t\tdataType: int64
\t\tisKey
\t\tformatString: 0
\t\tsourceColumn: order_item_key

\tcolumn order_id
\t\tdataType: string
\t\tsourceColumn: order_id

\tcolumn order_item_id
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: order_item_id

\tcolumn order_status
\t\tdataType: string
\t\tsourceColumn: order_status

\tcolumn order_date_key
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: order_date_key

\tcolumn delivery_date_key
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: delivery_date_key

\tcolumn estimated_date_key
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: estimated_date_key

\tcolumn customer_key
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: customer_key

\tcolumn product_key
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: product_key

\tcolumn seller_key
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: seller_key

\tcolumn price
\t\tdataType: double
\t\tformatString: "$#,##0.00"
\t\tsourceColumn: price

\tcolumn freight_value
\t\tdataType: double
\t\tformatString: "$#,##0.00"
\t\tsourceColumn: freight_value

\tcolumn total_item_value
\t\tdataType: double
\t\tformatString: "$#,##0.00"
\t\tsourceColumn: total_item_value

\tcolumn delivery_delay_days
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: delivery_delay_days

\tcolumn actual_delivery_days
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: actual_delivery_days

\tcolumn estimated_delivery_days
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: estimated_delivery_days

\tcolumn is_late
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: is_late

\tcolumn review_score
\t\tdataType: int64
\t\tformatString: 0
\t\tsourceColumn: review_score

\tmeasure 'Total Revenue' = SUM(fact_order_items[price])
\t\tformatString: "$#,##0.00"

\tmeasure 'Total Freight' = SUM(fact_order_items[freight_value])
\t\tformatString: "$#,##0.00"

\tmeasure 'Total GMV' = [Total Revenue] + [Total Freight]
\t\tformatString: "$#,##0.00"

\tmeasure 'Total Orders' = DISTINCTCOUNT(fact_order_items[order_id])
\t\tformatString: "#,##0"

\tmeasure 'Average Order Value' = DIVIDE([Total Revenue], [Total Orders], 0.0)
\t\tformatString: "$#,##0.00"

\tmeasure 'Total Delivered Orders' = CALCULATE([Total Orders], fact_order_items[order_status] = "delivered")
\t\tformatString: "#,##0"

\tmeasure 'Late Orders' = CALCULATE([Total Orders], fact_order_items[is_late] = 1, fact_order_items[order_status] = "delivered")
\t\tformatString: "#,##0"

\tmeasure 'Late Delivery %' = DIVIDE([Late Orders], [Total Delivered Orders], 0.0)
\t\tformatString: "0.0%"

\tmeasure 'On-Time Delivery %' = 1.0 - [Late Delivery %]
\t\tformatString: "0.0%"

\tmeasure 'Avg Delivery Delay Days' = AVERAGE(fact_order_items[delivery_delay_days])
\t\tformatString: "0.0"

\tmeasure 'Avg Review Score' = AVERAGE(fact_order_items[review_score])
\t\tformatString: "0.00"

\tpartition fact_order_items = m
\t\tmode: import
\t\tsource = 
\t\t\tlet
\t\t\t\tSource = Csv.Document(File.Contents("data/vw_order_master.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
\t\t\t\t#"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
\t\t\tin
\t\t\t\t#"Promoted Headers"
"""
    with open(os.path.join(semantic_dir, 'definition', 'tables', 'fact_order_items.tmdl'), 'w', encoding='utf-8') as f:
        f.write(fact_order_items_tmdl)

    # 12. Create measures.dax
    measures_dax_content = """// ============================================================================
// Olist Brazilian E-Commerce Analytics Platform
// Enterprise DAX Measures Repository
// ============================================================================

// --- 1. CORE REVENUE & VOLUME MEASURES ---
[Total Revenue] = 
SUM(fact_order_items[price])

[Total Freight] = 
SUM(fact_order_items[freight_value])

[Total GMV] = 
[Total Revenue] + [Total Freight]

[Total Orders] = 
DISTINCTCOUNT(fact_order_items[order_id])

[Total Items Sold] = 
COUNT(fact_order_items[order_item_key])

[Average Order Value] = 
DIVIDE([Total Revenue], [Total Orders], 0.0)

[Average Items Per Order] = 
DIVIDE([Total Items Sold], [Total Orders], 0.0)

// --- 2. TIME INTELLIGENCE & MOM GROWTH ---
[Revenue Prior Month] = 
CALCULATE(
    [Total Revenue],
    DATEADD(dim_date[full_date], -1, MONTH)
)

[Revenue MoM Growth %] = 
VAR CurrentRevenue = [Total Revenue]
VAR PriorRevenue = [Revenue Prior Month]
RETURN
DIVIDE(CurrentRevenue - PriorRevenue, PriorRevenue, 0.0)

[Orders Prior Month] = 
CALCULATE(
    [Total Orders],
    DATEADD(dim_date[full_date], -1, MONTH)
)

[Orders MoM Growth %] = 
VAR CurrentOrders = [Total Orders]
VAR PriorOrders = [Orders Prior Month]
RETURN
DIVIDE(CurrentOrders - PriorOrders, PriorOrders, 0.0)

// --- 3. LOGISTICS & SLA DELIVERY PERFORMANCE ---
[Total Delivered Orders] = 
CALCULATE(
    [Total Orders],
    fact_order_items[order_status] = "delivered"
)

[Late Orders] = 
CALCULATE(
    [Total Orders],
    fact_order_items[is_late] = 1,
    fact_order_items[order_status] = "delivered"
)

[On-Time Orders] = 
CALCULATE(
    [Total Orders],
    fact_order_items[is_late] = 0,
    fact_order_items[order_status] = "delivered"
)

[Late Delivery %] = 
DIVIDE([Late Orders], [Total Delivered Orders], 0.0)

[On-Time Delivery %] = 
DIVIDE([On-Time Orders], [Total Delivered Orders], 0.0)

[Avg Actual Delivery Days] = 
AVERAGE(fact_order_items[actual_delivery_days])

[Avg Estimated Delivery Days] = 
AVERAGE(fact_order_items[estimated_delivery_days])

[Avg Delivery Delay Days] = 
AVERAGE(fact_order_items[delivery_delay_days])

// --- 4. CUSTOMER SATISFACTION (CSAT) & REVIEWS ---
[Avg Review Score] = 
AVERAGE(fact_order_items[review_score])

[5-Star Reviews Count] = 
CALCULATE(
    COUNT(fact_order_items[order_item_key]),
    fact_order_items[review_score] = 5
)

[1-Star Reviews Count] = 
CALCULATE(
    COUNT(fact_order_items[order_item_key]),
    fact_order_items[review_score] = 1
)

[5-Star Review %] = 
DIVIDE([5-Star Reviews Count], COUNT(fact_order_items[review_score]), 0.0)

[1-Star Review %] = 
DIVIDE([1-Star Reviews Count], COUNT(fact_order_items[review_score]), 0.0)

// --- 5. CUSTOMER RETENTION & COHORTS ---
[Total Unique Customers] = 
DISTINCTCOUNT(dim_customers[customer_unique_id])

[Repeat Customers] = 
CALCULATE(
    DISTINCTCOUNT(dim_customers[customer_unique_id]),
    FILTER(
        VALUES(dim_customers[customer_unique_id]),
        CALCULATE([Total Orders]) >= 2
    )
)

[Repeat Customer Rate %] = 
DIVIDE([Repeat Customers], [Total Unique Customers], 0.0)
"""
    with open(os.path.join(pbi_dir, 'measures.dax'), 'w', encoding='utf-8') as f:
        f.write(measures_dax_content)

    print("[SUCCESS] Modern Power BI PBIR and TMDL structure generated.")

if __name__ == '__main__':
    build_pbi_project()
