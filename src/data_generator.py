import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_synthetic_data(output_path, num_customers=3000, num_products=250, num_days=730):
    """
    Generates a realistic synthetic transaction dataset for e-commerce analytics.
    Simulates seasonality, distinct customer segments, cancellations, and missing values.
    """
    np.random.seed(42)
    random.seed(42)

    print(f"Generating synthetic e-commerce dataset with {num_customers} customers and {num_products} products...")

    # 1. Generate Product Catalog
    categories = ['Electronics', 'Home & Kitchen', 'Apparel', 'Beauty & Personal Care', 'Books', 'Sports & Outdoors']
    category_weights = [0.15, 0.25, 0.20, 0.15, 0.15, 0.10]
    
    products = []
    for i in range(num_products):
        category = np.random.choice(categories, p=category_weights)
        stock_code = f"{random.randint(10000, 99999)}{random.choice(['A', 'B', 'C', ''])}"
        description = f"{category} Item {i+1}"
        
        # Log-normal distribution for prices (mostly cheap items, few expensive ones)
        unit_price = round(float(np.random.lognormal(mean=2.5, sigma=1.0)), 2)
        unit_price = max(0.50, min(unit_price, 999.00)) # Clamp prices
        
        products.append({
            'StockCode': stock_code,
            'Description': description,
            'UnitPrice': unit_price,
            'Category': category
        })
    
    product_df = pd.DataFrame(products)

    # 2. Define Customer Archetypes
    # We define cohorts based on registration date and lifecycle properties
    start_date = datetime(2024, 6, 1)
    end_date = start_date + timedelta(days=num_days)
    
    customer_profiles = []
    countries = ['United Kingdom', 'Germany', 'France', 'Spain', 'Netherlands', 'Belgium', 'Switzerland', 'Portugal']
    country_weights = [0.75, 0.08, 0.05, 0.04, 0.03, 0.02, 0.02, 0.01]

    for cust_id in range(10001, 10001 + num_customers):
        # Assign Country
        country = np.random.choice(countries, p=country_weights)
        
        # Customer Type: VIP, Loyal, Casual, New, One-Time
        cust_type = np.random.choice(
            ['VIP', 'Loyal', 'Casual', 'New', 'OneTime'],
            p=[0.05, 0.20, 0.45, 0.15, 0.15]
        )
        
        # Determine registration/start time
        if cust_type == 'New':
            # Joined in the last 90 days
            join_delay = random.randint(num_days - 90, num_days - 10)
        else:
            # Joined anytime in the first 1.5 years
            join_delay = random.randint(0, int(num_days * 0.75))
            
        cust_start_date = start_date + timedelta(days=join_delay)
        
        # Churn behavior simulation: Casual and OneTime customers might stop buying
        churned = False
        churn_date = None
        if cust_type == 'OneTime':
            churned = True
            churn_date = cust_start_date + timedelta(days=1)
        elif cust_type == 'Casual' and random.random() < 0.45:
            # Churned casual customer
            churned = True
            active_duration = random.randint(30, 360)
            churn_date = cust_start_date + timedelta(days=active_duration)
            if churn_date > end_date:
                churn_date = end_date
                churned = False
                
        customer_profiles.append({
            'CustomerID': cust_id,
            'Country': country,
            'Type': cust_type,
            'StartDate': cust_start_date,
            'Churned': churned,
            'ChurnDate': churn_date
        })

    # 3. Generate Transactions
    transactions = []
    invoice_counter = 536365
    
    for cust in customer_profiles:
        cust_id = cust['CustomerID']
        cust_type = cust['Type']
        join_date = cust['StartDate']
        churned = cust['Churned']
        churn_date = cust['ChurnDate']
        
        current_date = join_date
        
        # Set average days between purchases based on customer type
        if cust_type == 'VIP':
            avg_interval = random.randint(5, 15)
            basket_size_mean = 12
        elif cust_type == 'Loyal':
            avg_interval = random.randint(15, 35)
            basket_size_mean = 7
        elif cust_type == 'Casual':
            avg_interval = random.randint(40, 90)
            basket_size_mean = 4
        elif cust_type == 'New':
            avg_interval = random.randint(15, 40)
            basket_size_mean = 5
        else: # OneTime
            avg_interval = 999999
            basket_size_mean = 3
            
        # First transaction
        invoices_to_create = []
        if current_date <= end_date:
            invoices_to_create.append(current_date)
            
        # Generate subsequent transaction dates
        if cust_type != 'OneTime':
            while True:
                # Add variation to interval
                interval = int(np.random.normal(avg_interval, avg_interval * 0.25))
                interval = max(3, interval)
                current_date = current_date + timedelta(days=interval)
                
                # Stop if past end date or past churn date
                if current_date > end_date:
                    break
                if churned and current_date > churn_date:
                    break
                    
                invoices_to_create.append(current_date)
                
        # Generate items for each invoice
        for inv_date in invoices_to_create:
            # Monthly seasonality modifier (e.g. higher volume in Nov/Dec, lower in Jan)
            month = inv_date.month
            seasonality_mod = 1.0
            if month in [11, 12]:  # Holiday spike
                seasonality_mod = 1.35
            elif month == 1:       # Post-holiday dip
                seasonality_mod = 0.75
                
            # Randomize basket size
            basket_size = max(1, int(np.random.poisson(basket_size_mean * seasonality_mod)))
            
            # Select random products
            selected_indices = np.random.choice(len(product_df), size=basket_size, replace=True)
            invoice_num = f"{invoice_counter}"
            invoice_counter += 1
            
            # Simulate cancellation (5% chance for VIP/Loyal/Casual, 0% for New/OneTime)
            is_cancelled = False
            if cust_type in ['VIP', 'Loyal', 'Casual'] and random.random() < 0.05:
                is_cancelled = True
                
            for idx in selected_indices:
                prod = product_df.iloc[idx]
                qty = max(1, int(np.random.geometric(p=0.4))) # Small quantities mostly
                
                # Add item to invoice
                transactions.append({
                    'InvoiceNo': invoice_num,
                    'StockCode': prod['StockCode'],
                    'Description': prod['Description'],
                    'Quantity': qty,
                    'UnitPrice': prod['UnitPrice'],
                    'InvoiceDate': inv_date.strftime('%Y-%m-%d %H:%M'),
                    'CustomerID': cust_id,
                    'Country': cust['Country']
                })
                
                # If cancelled, add a corresponding return transaction later
                if is_cancelled:
                    return_delay = random.randint(1, 10)
                    return_date = inv_date + timedelta(days=return_delay)
                    if return_date <= end_date:
                        transactions.append({
                            'InvoiceNo': f"C{invoice_num}",
                            'StockCode': prod['StockCode'],
                            'Description': f"Discount/Return: {prod['Description']}",
                            'Quantity': -qty, # Negative quantity represents return
                            'UnitPrice': prod['UnitPrice'],
                            'InvoiceDate': return_date.strftime('%Y-%m-%d %H:%M'),
                            'CustomerID': cust_id,
                            'Country': cust['Country']
                        })

    # 4. Generate guest checkout transactions (Missing CustomerID)
    # Around 10% of total transactions will have missing CustomerID
    guest_transactions_count = int(len(transactions) * 0.10)
    for _ in range(guest_transactions_count):
        guest_date = start_date + timedelta(days=random.randint(0, num_days - 1))
        # Seasonality
        month = guest_date.month
        seasonality_mod = 1.0
        if month in [11, 12]:
            seasonality_mod = 1.3
        elif month == 1:
            seasonality_mod = 0.8
            
        basket_size = max(1, int(np.random.poisson(3 * seasonality_mod)))
        invoice_num = f"{invoice_counter}"
        invoice_counter += 1
        
        selected_indices = np.random.choice(len(product_df), size=basket_size, replace=True)
        country = np.random.choice(countries, p=country_weights)
        
        for idx in selected_indices:
            prod = product_df.iloc[idx]
            qty = max(1, int(np.random.geometric(p=0.5)))
            
            transactions.append({
                'InvoiceNo': invoice_num,
                'StockCode': prod['StockCode'],
                'Description': prod['Description'],
                'Quantity': qty,
                'UnitPrice': prod['UnitPrice'],
                'InvoiceDate': guest_date.strftime('%Y-%m-%d %H:%M'),
                'CustomerID': np.nan, # Missing CustomerID
                'Country': country
            })

    # Create DataFrame and Save
    df = pd.DataFrame(transactions)
    # Shuffle transactions slightly to simulate concurrent activity
    df['InvoiceDateParsed'] = pd.to_datetime(df['InvoiceDate'])
    df = df.sort_values(by='InvoiceDateParsed').drop(columns=['InvoiceDateParsed'])
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Successfully generated {len(df)} transactions and saved to {output_path}!")

if __name__ == "__main__":
    generate_synthetic_data("data/raw_transactions.csv")
