import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Set style for publication-ready visual aesthetics
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.titlesize': 16,
    'figure.dpi': 150
})

# Custom modern color palette
PALETTE = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#3b82f6', '#ef4444', '#6b7280']

def generate_visualizations(cleaned_path, metrics_path, output_dir):
    """
    Generates and saves a suite of business visualizations for reporting.
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"Generating EDA visualizations and saving to {output_dir}...")
    
    # Load data
    df = pd.read_csv(cleaned_path)
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    
    metrics = pd.read_csv(metrics_path)
    
    # ------------------- 1. Monthly Revenue & Order Volume -------------------
    plt.figure(figsize=(12, 6))
    
    # Resample to monthly
    monthly_data = df.groupby(df['InvoiceDate'].dt.to_period('M')).agg(
        Revenue=('TotalSpend', 'sum'),
        Orders=('InvoiceNo', 'nunique')
    ).to_timestamp()
    
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Left axis: Revenue
    color = '#6366f1' # Slate Indigo
    ax1.set_xlabel('Month')
    ax1.set_ylabel('Total Revenue ($)', color=color)
    line1 = ax1.plot(monthly_data.index, monthly_data['Revenue'], color=color, marker='o', linewidth=2.5, label='Revenue')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.yaxis.set_major_formatter('${x:,.0f}')
    
    # Right axis: Orders
    ax2 = ax1.twinx()
    color = '#10b981' # Emerald Teal
    ax2.set_ylabel('Number of Orders', color=color)
    line2 = ax2.plot(monthly_data.index, monthly_data['Orders'], color=color, marker='s', linewidth=2, linestyle='--', label='Orders')
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Align legends
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left')
    
    plt.title('Monthly Revenue and Transaction Volume Trends', pad=20)
    fig.tight_layout()
    plt.savefig(os.path.join(output_dir, 'monthly_revenue_orders.png'), dpi=300)
    plt.close()
    
    # ------------------- 2. RFM Segment Distribution -------------------
    plt.figure(figsize=(10, 6))
    segment_counts = metrics['RFM_Segment'].value_counts()
    
    # Sort segments by count
    sns.barplot(
        x=segment_counts.values,
        y=segment_counts.index,
        palette="viridis",
        hue=segment_counts.index,
        legend=False
    )
    
    # Annotate bars with counts & percentages
    total_cust = len(metrics)
    for i, count in enumerate(segment_counts.values):
        pct = (count / total_cust) * 100
        plt.text(count + (total_cust * 0.005), i, f"{count:,} ({pct:.1f}%)", va='center', fontsize=9, fontweight='semibold')
        
    plt.title('Customer Distribution by RFM Segment', pad=15)
    plt.xlabel('Customer Count')
    plt.ylabel('RFM Segment')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'rfm_segment_distribution.png'), dpi=300)
    plt.close()
    
    # ------------------- 3. Predictive CLV by Segment -------------------
    plt.figure(figsize=(12, 6))
    
    # Sort categories by median CLV for better boxplot ordering
    seg_clv_order = metrics.groupby('RFM_Segment')['PredictiveCLV'].median().sort_values(ascending=False).index
    
    sns.boxplot(
        x='PredictiveCLV',
        y='RFM_Segment',
        data=metrics,
        order=seg_clv_order,
        palette="coolwarm",
        hue='RFM_Segment',
        legend=False,
        showfliers=False # Exclude extreme outliers for better scaling
    )
    
    plt.title('Predictive Customer Lifetime Value (CLV) by Segment (Excluding Outliers)', pad=15)
    plt.xlabel('Predicted CLV (12-Month Horizon, $)')
    plt.ylabel('RFM Segment')
    plt.gca().xaxis.set_major_formatter('${x:,.0f}')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'clv_by_segment_box.png'), dpi=300)
    plt.close()
    
    # ------------------- 4. Churn Risk vs. Spend Relationship -------------------
    plt.figure(figsize=(10, 6))
    
    # Scatter plot with hex bins or opacity to show density
    scatter = plt.scatter(
        metrics['Monetary'],
        metrics['ChurnProbability'],
        alpha=0.5,
        c=metrics['Recency'],
        cmap='coolwarm',
        edgecolors='none',
        s=30
    )
    
    cbar = plt.colorbar(scatter)
    cbar.set_label('Days Since Last Purchase (Recency)', rotation=270, labelpad=15)
    
    # Draw churn risk threshold (50%)
    plt.axhline(y=0.5, color='red', linestyle='--', alpha=0.7, label='Churn Threshold (50%)')
    
    plt.xscale('log') # Use log scale for monetary value because of long tail
    plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
    
    plt.title('Customer Churn Risk vs. Historical Spend', pad=15)
    plt.xlabel('Total Historical Net Spend (Monetary, Log Scale)')
    plt.ylabel('Predicted Churn Probability (Next 6 Months)')
    plt.legend(loc='lower left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'churn_risk_vs_spend.png'), dpi=300)
    plt.close()
    
    print("EDA Visualizations created successfully!")

if __name__ == "__main__":
    generate_visualizations(
        "data/cleaned_transactions.csv", 
        "data/customer_metrics.csv", 
        "data/plots"
    )
