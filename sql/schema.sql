-- Schema definition for E-commerce Transaction Database
-- Compatible with PostgreSQL, Snowflake, BigQuery, and SQLite

-- Drop table if exists
DROP TABLE IF EXISTS sales_transactions;

-- Create Sales Transactions table
CREATE TABLE sales_transactions (
    InvoiceNo VARCHAR(20) NOT NULL,
    StockCode VARCHAR(20) NOT NULL,
    Description VARCHAR(255),
    Quantity INTEGER NOT NULL,
    UnitPrice DECIMAL(10, 2) NOT NULL,
    InvoiceDate TIMESTAMP NOT NULL,
    CustomerID INTEGER,
    Country VARCHAR(100),
    TotalSpend DECIMAL(12, 2) GENERATED ALWAYS AS (Quantity * UnitPrice) STORED,
    IsCancellation BOOLEAN GENERATED ALWAYS AS (CASE WHEN Quantity < 0 THEN TRUE ELSE FALSE END) STORED
);

-- Indexing for analytical query optimization
CREATE INDEX idx_transactions_customer ON sales_transactions(CustomerID);
CREATE INDEX idx_transactions_date ON sales_transactions(InvoiceDate);
CREATE INDEX idx_transactions_country ON sales_transactions(Country);
CREATE INDEX idx_transactions_invoice ON sales_transactions(InvoiceNo);
