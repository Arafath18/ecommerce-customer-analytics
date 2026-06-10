import sqlite3
import pandas as pd

def run_sqlite_verification(transactions_csv, metrics_csv, output_report_path):
    print("Initializing SQLite database for verification...")
    # Create in-memory database
    conn = sqlite3.connect(':memory:')
    
    # Load CSVs
    print(f"Loading cleaned transactions from {transactions_csv}...")
    df_trans = pd.read_csv(transactions_csv)
    # Ensure Date is parsed as string for SQLite strftime
    df_trans['InvoiceDate'] = pd.to_datetime(df_trans['InvoiceDate']).dt.strftime('%Y-%m-%d %H:%M:%S')
    df_trans.to_sql('sales_transactions', conn, index=False, if_exists='replace')
    
    print(f"Loading customer metrics from {metrics_csv}...")
    df_metrics = pd.read_csv(metrics_csv)
    df_metrics.to_sql('customer_metrics', conn, index=False, if_exists='replace')
    
    queries = {
        "1. Monthly Revenue & Growth (MoM)": """
            WITH monthly_revenue AS (
                SELECT 
                    strftime('%Y-%m', InvoiceDate) as YearMonth,
                    ROUND(SUM(TotalSpend), 2) as Revenue,
                    COUNT(DISTINCT InvoiceNo) as OrderCount,
                    COUNT(DISTINCT CustomerID) as ActiveCustomers
                FROM sales_transactions
                WHERE CustomerID IS NOT NULL
                GROUP BY 1
            ),
            revenue_lag AS (
                SELECT 
                    YearMonth,
                    Revenue,
                    OrderCount,
                    ActiveCustomers,
                    LAG(Revenue) OVER (ORDER BY YearMonth) as PreviousMonthRevenue
                FROM monthly_revenue
            )
            SELECT 
                YearMonth,
                Revenue,
                OrderCount,
                ActiveCustomers,
                ROUND(PreviousMonthRevenue, 2) as PrevMonthRevenue,
                ROUND(((Revenue - PreviousMonthRevenue) / PreviousMonthRevenue) * 100.0, 2) as MoMGrowthPct
            FROM revenue_lag
            ORDER BY YearMonth;
        """,
        
        "2. Cohort Retention (MoM) - First 5 Cohorts, First 6 Months": """
            WITH customer_cohort AS (
                SELECT 
                    CustomerID,
                    strftime('%Y-%m-01', MIN(InvoiceDate)) as CohortMonth
                FROM sales_transactions
                WHERE CustomerID IS NOT NULL AND Quantity > 0
                GROUP BY CustomerID
            ),
            customer_activity AS (
                SELECT DISTINCT
                    t.CustomerID,
                    c.CohortMonth,
                    strftime('%Y-%m-01', t.InvoiceDate) as ActivityMonth
                FROM sales_transactions t
                JOIN customer_cohort c ON t.CustomerID = c.CustomerID
                WHERE t.Quantity > 0
            ),
            cohort_size AS (
                SELECT 
                    CohortMonth,
                    COUNT(DISTINCT CustomerID) as CohortSize
                FROM customer_cohort
                GROUP BY CohortMonth
            ),
            cohort_periods AS (
                SELECT 
                    CustomerID,
                    CohortMonth,
                    ActivityMonth,
                    (cast(strftime('%Y', ActivityMonth) as integer) - cast(strftime('%Y', CohortMonth) as integer)) * 12 + 
                    (cast(strftime('%m', ActivityMonth) as integer) - cast(strftime('%m', CohortMonth) as integer)) as PeriodIndex
                FROM customer_activity
            )
            SELECT 
                p.CohortMonth,
                s.CohortSize,
                p.PeriodIndex as MonthOffset,
                COUNT(DISTINCT p.CustomerID) as ActiveCustomers,
                ROUND((COUNT(DISTINCT p.CustomerID) * 100.0) / s.CohortSize, 2) as RetentionPct
            FROM cohort_periods p
            JOIN cohort_size s ON p.CohortMonth = s.CohortMonth
            WHERE p.CohortMonth <= '2024-10-01' AND p.PeriodIndex <= 5
            GROUP BY p.CohortMonth, s.CohortSize, p.PeriodIndex
            ORDER BY p.CohortMonth, p.PeriodIndex;
        """,
        
        "3. Product Pareto Analysis (80/20 Rule) - Top 10 Products": """
            WITH product_revenue AS (
                SELECT 
                    StockCode,
                    Description,
                    SUM(TotalSpend) as ProductRevenue
                FROM sales_transactions
                WHERE Quantity > 0
                GROUP BY StockCode, Description
            ),
            ranked_products AS (
                SELECT 
                    StockCode,
                    Description,
                    ProductRevenue,
                    SUM(ProductRevenue) OVER (ORDER BY ProductRevenue DESC) as CumulativeRevenue,
                    SUM(ProductRevenue) OVER () as TotalRevenue,
                    ROW_NUMBER() OVER (ORDER BY ProductRevenue DESC) as ProductRank,
                    COUNT(*) OVER () as TotalProductCount
                FROM product_revenue
            )
            SELECT 
                StockCode,
                Description,
                ROUND(ProductRevenue, 2) as Revenue,
                ROUND((ProductRevenue * 100.0) / TotalRevenue, 2) as RevenueContributionPct,
                ROUND((CumulativeRevenue * 100.0) / TotalRevenue, 2) as CumulativeRevenuePct,
                ROUND((ProductRank * 100.0) / TotalProductCount, 2) as CumulativeProductPct
            FROM ranked_products
            ORDER BY ProductRevenue DESC
            LIMIT 10;
        """,
        
        "4. Repeat Purchase Rate (RPR)": """
            WITH customer_orders AS (
                SELECT 
                    CustomerID,
                    COUNT(DISTINCT InvoiceNo) as OrderCount
                FROM sales_transactions
                WHERE CustomerID IS NOT NULL AND Quantity > 0
                GROUP BY CustomerID
            )
            SELECT 
                COUNT(*) as TotalCustomers,
                SUM(CASE WHEN OrderCount > 1 THEN 1 ELSE 0 END) as RepeatCustomers,
                ROUND((SUM(CASE WHEN OrderCount > 1 THEN 1 ELSE 0 END) * 100.0) / COUNT(*), 2) as RepeatPurchaseRatePct
            FROM customer_orders;
        """,
        
        "5. RFM Segment Performance Aggregation": """
            SELECT 
                RFM_Segment,
                COUNT(DISTINCT CustomerID) as CustomerCount,
                ROUND(AVG(Recency), 1) as AvgRecencyDays,
                ROUND(AVG(Frequency), 1) as AvgOrderFrequency,
                ROUND(AVG(AOV), 2) as AvgOrderValue,
                ROUND(SUM(Monetary), 2) as TotalSegmentRevenue,
                ROUND((SUM(Monetary) * 100.0) / SUM(SUM(Monetary)) OVER (), 2) as SegmentRevenuePct,
                ROUND(AVG(ChurnProbability) * 100.0, 2) as AvgChurnRiskPct,
                ROUND(AVG(PredictiveCLV), 2) as AvgExpectedCLV
            FROM customer_metrics
            GROUP BY RFM_Segment
            ORDER BY TotalSegmentRevenue DESC;
        """,
        
        "6. High-Value Churn Risk Alert (VIP Win-back List)": """
            SELECT 
                CustomerID,
                RFM_Segment,
                Recency as DaysSinceLastPurchase,
                Frequency as TotalOrdersPurchased,
                ROUND(Monetary, 2) as TotalNetSpend,
                ROUND(ChurnProbability * 100.0, 2) as ChurnRiskPct,
                ROUND(PredictiveCLV, 2) as PredictedCLV
            FROM customer_metrics
            WHERE 
                RFM_Segment IN ('Champions', 'Loyal Customers', "Can't Lose Them")
                AND ChurnProbability > 0.50
                AND Recency > 45
            ORDER BY Monetary DESC
            LIMIT 10;
        """
    }
    
    with open(output_report_path, 'w') as f:
        f.write("=======================================================\n")
        f.write("SQL BUSINESS INSIGHTS REPORT (VERIFIED IN SQLITE)\n")
        f.write("=======================================================\n\n")
        
        for name, query in queries.items():
            print(f"Executing Query: {name}...")
            f.write(f"--- {name} ---\n")
            
            try:
                res_df = pd.read_sql_query(query, conn)
                # Format to string representation
                f.write(res_df.to_string(index=False))
                f.write("\n\n")
            except Exception as e:
                f.write(f"Error executing query: {str(e)}\n\n")
                print(f"Error executing {name}: {e}")
                
    print(f"SQL Verification report generated at {output_report_path}!")
    conn.close()

if __name__ == "__main__":
    run_sqlite_verification(
        "data/cleaned_transactions.csv", 
        "data/customer_metrics.csv", 
        "data/sql_insights_report.txt"
    )
