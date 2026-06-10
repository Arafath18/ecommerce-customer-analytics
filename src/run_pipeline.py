import os
import json
from datetime import datetime
import pandas as pd
import numpy as np

# Import pipeline components
from data_generator import generate_synthetic_data
from preprocessing import clean_data
from models import run_modeling_pipeline
from eda_visualizations import generate_visualizations

def aggregate_dashboard_metrics(cleaned_path, metrics_path, js_output_path):
    """
    Reads the transaction logs and customer-level analytical metrics,
    aggregates them, and writes a production-ready dashboard/data.js file.
    """
    print(f"Aggregating dashboard metrics and exporting to {js_output_path}...")
    
    # Load data
    df = pd.read_csv(cleaned_path)
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    
    metrics = pd.read_csv(metrics_path)
    
    # 1. KPIs
    total_revenue = float(df['TotalSpend'].sum())
    total_customers = int(metrics['CustomerID'].nunique())
    
    # Count of standard purchases (exclude cancellations)
    purchases = df[~df['IsCancellation']]
    total_orders = int(purchases['InvoiceNo'].nunique())
    
    aov = float(total_revenue / total_orders) if total_orders > 0 else 0.0
    
    # Overall churn rate: proportion of customers with >50% churn probability
    churn_threshold_count = int((metrics['ChurnProbability'] > 0.50).sum())
    overall_churn_rate = float(churn_threshold_count / total_customers) if total_customers > 0 else 0.0
    
    avg_clv = float(metrics['PredictiveCLV'].mean())
    
    kpi_data = {
        "total_revenue": round(total_revenue, 2),
        "total_customers": total_customers,
        "total_orders": total_orders,
        "aov": round(aov, 2),
        "overall_churn_rate": round(overall_churn_rate, 4),
        "avg_clv": round(avg_clv, 2)
    }
    
    # 2. Monthly Trends (Chronological)
    df['YearMonthStr'] = df['InvoiceDate'].dt.strftime('%Y-%m')
    monthly = df.groupby('YearMonthStr').agg(
        Revenue=('TotalSpend', 'sum'),
        Orders=('InvoiceNo', 'nunique'),
        ActiveCustomers=('CustomerID', 'nunique')
    ).reset_index()
    
    monthly_trends = []
    for _, row in monthly.sort_values('YearMonthStr').iterrows():
        monthly_trends.append({
            "month": str(row['YearMonthStr']),
            "revenue": round(float(row['Revenue']), 2),
            "orders": int(row['Orders']),
            "active_customers": int(row['ActiveCustomers'])
        })
        
    # 3. Segment Performance
    segment_perf = metrics.groupby('RFM_Segment').agg(
        Count=('CustomerID', 'count'),
        AvgRecency=('Recency', 'mean'),
        AvgFrequency=('Frequency', 'mean'),
        AvgMonetary=('Monetary', 'mean'),
        AvgChurnProb=('ChurnProbability', 'mean'),
        AvgCLV=('PredictiveCLV', 'mean')
    ).reset_index()
    
    segments_data = []
    for _, row in segment_perf.iterrows():
        name = str(row['RFM_Segment'])
        count = int(row['Count'])
        pct = float(count / total_customers)
        
        segments_data.append({
            "segment": name,
            "count": count,
            "pct": round(pct, 4),
            "avg_recency": round(float(row['AvgRecency']), 1),
            "avg_frequency": round(float(row['AvgFrequency']), 1),
            "avg_monetary": round(float(row['AvgMonetary']), 2),
            "avg_churn_prob": round(float(row['AvgChurnProb']), 4),
            "avg_clv": round(float(row['AvgCLV']), 2)
        })
        
    # 4. Top Products (by Revenue)
    # Filter out returns/cancellations for clean stats or keep net? Standard is net revenue
    product_stats = df.groupby(['StockCode', 'Description']).agg(
        Revenue=('TotalSpend', 'sum'),
        QuantitySold=('Quantity', 'sum')
    ).reset_index()
    
    top_products_df = product_stats.sort_values(by='Revenue', ascending=False).head(10)
    top_products = []
    for _, row in top_products_df.iterrows():
        top_products.append({
            "stock_code": str(row['StockCode']),
            "description": str(row['Description']),
            "revenue": round(float(row['Revenue']), 2),
            "units_sold": int(row['QuantitySold'])
        })
        
    # 5. Top Risk VIP Customers (Monetary > median VIP and Churn > 0.50)
    # Let's sort VIP/At Risk high spenders who are likely to churn
    high_value_median = metrics['Monetary'].median()
    vip_risk_df = metrics[(metrics['ChurnProbability'] > 0.50) & (metrics['Monetary'] > high_value_median * 1.5)]
    vip_risk_df = vip_risk_df.sort_values(by='Monetary', ascending=False).head(10)
    
    top_risk_vips = []
    for _, row in vip_risk_df.iterrows():
        top_risk_vips.append({
            "customer_id": int(row['CustomerID']),
            "segment": str(row['RFM_Segment']),
            "recency": int(row['Recency']),
            "frequency": int(row['Frequency']),
            "monetary": round(float(row['Monetary']), 2),
            "churn_prob": round(float(row['ChurnProbability']), 4),
            "clv": round(float(row['PredictiveCLV']), 2)
        })
        
    # 6. Country Distribution
    country_stats = df.groupby('Country').agg(
        Revenue=('TotalSpend', 'sum'),
        Customers=('CustomerID', 'nunique')
    ).reset_index()
    country_stats = country_stats.sort_values('Revenue', ascending=False).head(8)
    
    countries_data = []
    for _, row in country_stats.iterrows():
        countries_data.append({
            "country": str(row['Country']),
            "revenue": round(float(row['Revenue']), 2),
            "customers": int(row['Customers'])
        })

    # Wrap as JavaScript file
    dashboard_payload = {
        "kpis": kpi_data,
        "monthly_trends": monthly_trends,
        "segments": segments_data,
        "top_products": top_products,
        "top_risk_vips": top_risk_vips,
        "countries": countries_data,
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    os.makedirs(os.path.dirname(js_output_path), exist_ok=True)
    with open(js_output_path, 'w') as f:
        f.write("const ANALYTICS_DATA = ")
        json.dump(dashboard_payload, f, indent=2)
        f.write(";")
        
    print(f"Aggregated metrics successfully written to {js_output_path}!")


def main():
    raw_path = "data/raw_transactions.csv"
    cleaned_path = "data/cleaned_transactions.csv"
    metrics_path = "data/customer_metrics.csv"
    plot_dir = "data/plots"
    js_output_path = "dashboard/data.js"
    
    # Step 1: Generate Data
    generate_synthetic_data(raw_path)
    
    # Step 2: Clean Data
    clean_data(raw_path, cleaned_path)
    
    # Step 3: Run Modeling
    run_modeling_pipeline(cleaned_path, metrics_path)
    
    # Step 4: Generate EDA Visualizations
    generate_visualizations(cleaned_path, metrics_path, plot_dir)
    
    # Step 5: Export Dashboard Data
    aggregate_dashboard_metrics(cleaned_path, metrics_path, js_output_path)
    
    print("\n=======================================================")
    print("CUSTOMER ANALYTICS PIPELINE COMPLETED SUCCESSFULLY!")
    print("All processed datasets, models, plots, and dashboard assets are ready.")
    print("=======================================================")

if __name__ == "__main__":
    main()
