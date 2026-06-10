-- =========================================================================
-- Business Insights Analytical Queries
-- Standard ANSI SQL (Adapted for PostgreSQL, Snowflake, and BigQuery)
-- =========================================================================

-- 1. Monthly Revenue and Growth Rate (MoM)
-- Purpose: Track revenue performance over time and measure monthly expansion rate.
WITH monthly_revenue AS (
    SELECT 
        -- For SQLite use: strftime('%Y-%m', InvoiceDate) as YearMonth
        -- For BigQuery use: FORMAT_TIMESTAMP('%Y-%m', InvoiceDate) as YearMonth
        DATE_TRUNC('month', InvoiceDate) AS YearMonth,
        ROUND(SUM(Quantity * UnitPrice), 2) AS Revenue,
        COUNT(DISTINCT InvoiceNo) AS OrderCount,
        COUNT(DISTINCT CustomerID) AS ActiveCustomers
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
        LAG(Revenue) OVER (ORDER BY YearMonth) AS PreviousMonthRevenue
    FROM monthly_revenue
)
SELECT 
    YearMonth,
    Revenue,
    OrderCount,
    ActiveCustomers,
    ROUND(PreviousMonthRevenue, 2) AS PreviousMonthRevenue,
    ROUND(
        ((Revenue - PreviousMonthRevenue) / PreviousMonthRevenue) * 100.0, 
        2
    ) AS MoMGrowthPct
FROM revenue_lag
ORDER BY YearMonth;


-- 2. Customer Cohort Retention Analysis (MoM)
-- Purpose: Monitor how customer cohorts retain over subsequent months after registration.
WITH customer_cohort AS (
    -- Identify the first purchase month for each customer
    SELECT 
        CustomerID,
        DATE_TRUNC('month', MIN(InvoiceDate)) AS CohortMonth
    FROM sales_transactions
    WHERE CustomerID IS NOT NULL AND Quantity > 0
    GROUP BY CustomerID
),
customer_activity AS (
    -- Map each customer purchase to their transaction month
    SELECT DISTINCT
        t.CustomerID,
        c.CohortMonth,
        DATE_TRUNC('month', t.InvoiceDate) AS ActivityMonth
    FROM sales_transactions t
    JOIN customer_cohort c ON t.CustomerID = c.CustomerID
    WHERE t.Quantity > 0
),
cohort_size AS (
    -- Count total customers in each cohort
    SELECT 
        CohortMonth,
        COUNT(DISTINCT CustomerID) AS CohortSize
    FROM customer_cohort
    GROUP BY CohortMonth
),
cohort_periods AS (
    -- Calculate month difference between cohort start and activity date
    -- Note: EXTRACT(YEAR/MONTH) works on Postgres/Snowflake.
    -- For SQLite use: (strftime('%Y', ActivityMonth) - strftime('%Y', CohortMonth)) * 12 + ...
    SELECT 
        CustomerID,
        CohortMonth,
        ActivityMonth,
        (EXTRACT(YEAR FROM ActivityMonth) - EXTRACT(YEAR FROM CohortMonth)) * 12 + 
        (EXTRACT(MONTH FROM ActivityMonth) - EXTRACT(MONTH FROM CohortMonth)) AS PeriodIndex
    FROM customer_activity
)
SELECT 
    p.CohortMonth,
    s.CohortSize,
    p.PeriodIndex AS MonthOffset,
    COUNT(DISTINCT p.CustomerID) AS ActiveCustomers,
    ROUND(
        (COUNT(DISTINCT p.CustomerID) * 100.0) / s.CohortSize, 
        2
    ) AS RetentionPct
FROM cohort_periods p
JOIN cohort_size s ON p.CohortMonth = s.CohortMonth
GROUP BY p.CohortMonth, s.CohortSize, p.PeriodIndex
ORDER BY p.CohortMonth, p.PeriodIndex;


-- 3. Product Pareto Analysis (80/20 Rule)
-- Purpose: Identify the top 20% of products generating 80% of total revenue.
WITH product_revenue AS (
    SELECT 
        StockCode,
        Description,
        SUM(Quantity * UnitPrice) AS ProductRevenue
    FROM sales_transactions
    WHERE Quantity > 0
    GROUP BY StockCode, Description
),
ranked_products AS (
    SELECT 
        StockCode,
        Description,
        ProductRevenue,
        SUM(ProductRevenue) OVER (ORDER BY ProductRevenue DESC) AS CumulativeRevenue,
        SUM(ProductRevenue) OVER () AS TotalRevenue,
        ROW_NUMBER() OVER (ORDER BY ProductRevenue DESC) AS ProductRank,
        COUNT(*) OVER () AS TotalProductCount
    FROM product_revenue
)
SELECT 
    StockCode,
    Description,
    ROUND(ProductRevenue, 2) AS Revenue,
    ROUND((ProductRevenue * 100.0) / TotalRevenue, 2) AS RevenueContributionPct,
    ROUND((CumulativeRevenue * 100.0) / TotalRevenue, 2) AS CumulativeRevenuePct,
    ROUND((ProductRank * 100.0) / TotalProductCount, 2) AS CumulativeProductPct,
    CASE 
        WHEN CumulativeRevenue <= TotalRevenue * 0.80 THEN 'Top 80% Driver (VIP Product)'
        ELSE 'Long Tail Product'
    END AS ParetoStatus
FROM ranked_products
ORDER BY ProductRevenue DESC;


-- 4. Repeat Purchase Rate (RPR)
-- Purpose: Measure customer loyalty by calculating the proportion of repeat buyers.
WITH customer_orders AS (
    SELECT 
        CustomerID,
        COUNT(DISTINCT InvoiceNo) AS OrderCount
    FROM sales_transactions
    WHERE CustomerID IS NOT NULL AND Quantity > 0
    GROUP BY CustomerID
)
SELECT 
    COUNT(*) AS TotalCustomers,
    SUM(CASE WHEN OrderCount > 1 THEN 1 ELSE 0 END) AS RepeatCustomers,
    ROUND(
        (SUM(CASE WHEN OrderCount > 1 THEN 1 ELSE 0 END) * 100.0) / COUNT(*), 
        2
    ) AS RepeatPurchaseRatePct
FROM customer_orders;


-- 5. RFM Segment Aggregation
-- Purpose: Aggregate monetary contribution and engagement patterns across client segments.
-- Assumes a customer_metrics metadata table exists in the data warehouse.
SELECT 
    RFM_Segment,
    COUNT(DISTINCT CustomerID) AS CustomerCount,
    ROUND(AVG(Recency), 1) AS AvgRecencyDays,
    ROUND(AVG(Frequency), 1) AS AvgOrderFrequency,
    ROUND(AVG(AOV), 2) AS AvgOrderValue,
    ROUND(SUM(Monetary), 2) AS TotalSegmentRevenue,
    ROUND(
        (SUM(Monetary) * 100.0) / SUM(SUM(Monetary)) OVER (), 
        2
    ) AS SegmentRevenueContributionPct,
    ROUND(AVG(ChurnProbability) * 100.0, 2) AS AvgChurnRiskPct,
    ROUND(AVG(PredictiveCLV), 2) AS AvgExpectedCLV
FROM customer_metrics
GROUP BY RFM_Segment
ORDER BY TotalSegmentRevenue DESC;


-- 6. High-Value Churn Risk Alert (VIP Win-back List)
-- Purpose: List VIP/Loyal customers at risk of churning, sorted by highest historical value.
-- Alerts marketing to run personalized retention campaigns on our most valuable customers.
SELECT 
    CustomerID,
    RFM_Segment,
    Recency AS DaysSinceLastPurchase,
    Frequency AS TotalOrdersPurchased,
    ROUND(Monetary, 2) AS TotalNetSpend,
    ROUND(ChurnProbability * 100.0, 2) AS ChurnProbabilityPct,
    ROUND(PredictiveCLV, 2) AS PredictedCLV
FROM customer_metrics
WHERE 
    RFM_Segment IN ('Champions', 'Loyal Customers', "Can't Lose Them")
    AND ChurnProbability > 0.50
    AND Recency > 45
ORDER BY Monetary DESC
LIMIT 15;
