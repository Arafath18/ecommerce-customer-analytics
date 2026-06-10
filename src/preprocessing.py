import os
import pandas as pd
import numpy as np

def clean_data(input_path, output_path):
    """
    Cleans raw transaction data:
    1. Parses dates
    2. Removes transactions with missing CustomerID
    3. Handles returns/cancellations (InvoiceNo starts with 'C')
    4. Filters out invalid transactions (e.g. UnitPrice <= 0)
    5. Calculates TotalSpend = Quantity * UnitPrice
    6. Trims whitespace and extracts date parts
    """
    print(f"Loading raw transactions from {input_path}...")
    df = pd.read_csv(input_path)
    initial_rows = len(df)
    
    # 1. Parse InvoiceDate
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    
    # 2. Drop rows without CustomerID
    # For customer-centric analytics like RFM, CLV, and Churn, we must identify the customer.
    missing_cust_before = df['CustomerID'].isnull().sum()
    df = df.dropna(subset=['CustomerID'])
    df['CustomerID'] = df['CustomerID'].astype(int)
    
    # 3. Trim whitespace from text columns
    df['Description'] = df['Description'].fillna("").astype(str).str.strip()
    df['StockCode'] = df['StockCode'].astype(str).str.strip()
    df['InvoiceNo'] = df['InvoiceNo'].astype(str).str.strip()
    
    # 4. Handle invalid pricing
    # Keep standard transactions (Quantity > 0 and UnitPrice > 0) OR cancellations (Quantity < 0)
    # Filter out entries with negative/zero price which are usually adjustments, freebies, or system errors
    invalid_price = df[df['UnitPrice'] <= 0]
    df = df[df['UnitPrice'] > 0]
    
    # Identify returns/cancellations
    df['IsCancellation'] = df['InvoiceNo'].str.startswith('C', na=False)
    
    # Verify that cancellations have negative quantity and non-cancellations have positive quantity
    # Filter out any weird anomalies (like negative quantity without 'C' prefix, or positive quantity with 'C' prefix)
    df = df[((df['IsCancellation']) & (df['Quantity'] < 0)) | ((~df['IsCancellation']) & (df['Quantity'] > 0))]
    
    # 5. Calculate TotalSpend
    df['TotalSpend'] = df['Quantity'] * df['UnitPrice']
    
    # 6. Extract additional date fields for convenience in cohort/monthly analysis
    df['YearMonth'] = df['InvoiceDate'].dt.to_period('M')
    df['InvoiceDay'] = df['InvoiceDate'].dt.date
    
    # Summarize cleaning steps
    final_rows = len(df)
    print(f"Data Cleaning Summary:")
    print(f"  - Initial record count: {initial_rows}")
    print(f"  - Dropped due to missing CustomerID: {missing_cust_before} ({missing_cust_before/initial_rows*100:.2f}%)")
    print(f"  - Dropped due to <= 0 UnitPrice: {len(invalid_price)}")
    print(f"  - Cleaned record count: {final_rows} (Retained: {final_rows/initial_rows*100:.2f}%)")
    print(f"  - Total Standard transactions: {len(df[~df['IsCancellation']])}")
    print(f"  - Total Cancellation transactions: {len(df[df['IsCancellation']])}")
    
    # Ensure directory exists and save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Cleaned transactions saved to {output_path}!")
    return df

if __name__ == "__main__":
    clean_data("data/raw_transactions.csv", "data/cleaned_transactions.csv")
