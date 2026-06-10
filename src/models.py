import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler

def get_rfm_segment(row):
    """
    Maps R, F, M scores (1-5) to a marketing segment.
    """
    r, f, m = row['R_Score'], row['F_Score'], row['M_Score']
    
    # Champions: bought recently, buy frequently, spend the most
    if r >= 4 and f >= 4 and m >= 4:
        return 'Champions'
    
    # Loyal Customers: spend regularly, responsive to promotions
    elif (f >= 3 and m >= 3) and r >= 3:
        return 'Loyal Customers'
        
    # Potential Loyalists: recent spenders with decent frequency
    elif r >= 3 and f >= 2 and m >= 2:
        return 'Potential Loyalists'
        
    # New Customers: bought recently, but not frequently
    elif r >= 4 and f == 1:
        return 'New Customers'
        
    # Promising: recent buyers, low spend/frequency
    elif r == 3 and f == 1:
        return 'Promising'
        
    # Need Attention: above average recency and frequency, but slipping
    elif (r in [2, 3]) and (f in [2, 3]) and (m in [2, 3]):
        return 'Need Attention'
        
    # About to Sleep: below average recency, low frequency
    elif r == 2 and f == 1:
        return 'About to Sleep'
        
    # Can't Lose Them: huge spenders historically, but haven't returned in a long time
    elif r == 1 and f >= 3 and m >= 3:
        return "Can't Lose Them"

    # At Risk: spent big and often, but it was long ago
    elif r <= 2 and f >= 2 and m >= 2:
        return 'At Risk'
        
    # Hibernating: last purchase was long ago, low spend, low frequency
    else:
        return 'Hibernating'


def engineer_customer_features(df, start_date, end_date):
    """
    Engineers behavioral features for a cohort of customers active in a given window.
    """
    # Filter transactions to the window
    window_df = df[(df['InvoiceDate'] >= start_date) & (df['InvoiceDate'] <= end_date)]
    
    # If no transactions in this window, return empty dataframe
    if len(window_df) == 0:
        return pd.DataFrame()
        
    # Anchor date for recency calculation (day after window ends)
    anchor_date = end_date + timedelta(days=1)
    
    # Standard transaction aggregates
    # Separate purchases and cancellations to compute features
    purchases = window_df[~window_df['IsCancellation']]
    
    # Recency: days since last purchase
    recency = purchases.groupby('CustomerID')['InvoiceDate'].max().apply(lambda x: (anchor_date - x).days)
    
    # Frequency: count of unique purchase invoices
    frequency = purchases.groupby('CustomerID')['InvoiceNo'].nunique()
    
    # Monetary: net spending (purchases + cancellations)
    monetary = window_df.groupby('CustomerID')['TotalSpend'].sum()
    
    # Average Order Value (AOV)
    aov = monetary / frequency.replace(0, 1)
    
    # Tenure: days between first purchase and anchor date
    tenure = purchases.groupby('CustomerID')['InvoiceDate'].min().apply(lambda x: (anchor_date - x).days)
    
    # Basket size: average quantity per invoice
    basket_qty = purchases.groupby('CustomerID')['Quantity'].mean()
    
    # Calculate Gaps (days between consecutive orders)
    gaps_mean = []
    gaps_std = []
    cust_ids = []
    
    for cust_id, group in purchases.groupby('CustomerID'):
        cust_ids.append(cust_id)
        if len(group) <= 1:
            gaps_mean.append(0)
            gaps_std.append(0)
        else:
            dates = sorted(group['InvoiceDate'].dt.date.unique())
            if len(dates) <= 1:
                gaps_mean.append(0)
                gaps_std.append(0)
            else:
                diffs = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
                gaps_mean.append(np.mean(diffs))
                gaps_std.append(np.std(diffs))
                
    gaps_df = pd.DataFrame({
        'CustomerID': cust_ids,
        'AvgOrderGap': gaps_mean,
        'StdOrderGap': gaps_std
    }).set_index('CustomerID')
    
    # Spend Momentum: spend in last 60 days of window vs. overall monthly average
    recent_cutoff = end_date - timedelta(days=60)
    recent_spend = window_df[window_df['InvoiceDate'] >= recent_cutoff].groupby('CustomerID')['TotalSpend'].sum()
    
    # Combine everything
    features = pd.DataFrame(index=monetary.index)
    features['Recency'] = recency
    features['Frequency'] = frequency
    features['Monetary'] = monetary
    features['AOV'] = aov
    features['Tenure'] = tenure
    features['BasketQty'] = basket_qty
    features = features.join(gaps_df, how='left').fillna(0)
    
    # Add spend momentum
    features['RecentSpend'] = features.index.map(recent_spend).fillna(0)
    # Relative spend (ratio of recent 60-day spend to total spend)
    features['SpendMomentum'] = features['RecentSpend'] / (features['Monetary'] + 0.01)
    
    return features


def build_predictive_models(df):
    """
    Trains Churn Classification and Future Value Regression models using a split-window design.
    - Calibration window: first 18 months
    - Observation window: last 6 months (180 days)
    """
    print("Building predictive models (Calibration vs Observation)...")
    
    # Date limits
    min_date = df['InvoiceDate'].min()
    max_date = df['InvoiceDate'].max()
    obs_duration = 180 # 6 months
    
    calibration_end = max_date - timedelta(days=obs_duration)
    
    print(f"Calibration period: {min_date.date()} to {calibration_end.date()}")
    print(f"Observation period: {calibration_end.date()} to {max_date.date()}")
    
    # 1. Extract features in Calibration period
    cal_features = engineer_customer_features(df, min_date, calibration_end)
    if len(cal_features) == 0:
        raise ValueError("No customer features generated in calibration period.")
        
    # Get active customers in calibration
    cal_customers = cal_features.index.tolist()
    
    # 2. Extract labels in Observation period
    obs_df = df[(df['InvoiceDate'] > calibration_end) & (df['InvoiceDate'] <= max_date)]
    obs_active_customers = set(obs_df[~obs_df['IsCancellation']]['CustomerID'].unique())
    obs_spend = obs_df.groupby('CustomerID')['TotalSpend'].sum()
    
    # Churn Label: 1 if customer did NOT make a purchase in observation, 0 otherwise
    # Churn is only defined for customers who existed in the calibration period
    labels = pd.DataFrame(index=cal_customers)
    labels['Churned'] = labels.index.map(lambda cid: 0 if cid in obs_active_customers else 1)
    labels['FutureSpend'] = labels.index.map(obs_spend).fillna(0)
    
    # Align features and labels
    X = cal_features.copy()
    y_churn = labels['Churned']
    y_spend = labels['FutureSpend']
    
    # Split into train/validation sets (80% train, 20% validation)
    X_train, X_val, y_c_train, y_c_val, y_s_train, y_s_val = train_test_split(
        X, y_churn, y_spend, test_size=0.2, random_state=42
    )
    
    print(f"Training models on {len(X_train)} samples, validating on {len(X_val)} samples...")
    
    # Standardize features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # Train Churn Classifier (Random Forest)
    churn_model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    churn_model.fit(X_train_scaled, y_c_train)
    
    churn_val_auc = churn_model.score(X_val_scaled, y_c_val)
    print(f"Churn Classifier Validation Accuracy: {churn_val_auc:.4f}")
    
    # Train Value Regressor (Random Forest)
    spend_model = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
    spend_model.fit(X_train_scaled, y_s_train)
    
    spend_val_score = spend_model.score(X_val_scaled, y_s_val) # R2 score
    print(f"Spend Regressor Validation R2 Score: {spend_val_score:.4f}")
    
    # 3. Fit on full calibration data to maximize training size
    scaler_full = StandardScaler()
    X_scaled = scaler_full.fit_transform(X)
    
    churn_model_full = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    churn_model_full.fit(X_scaled, y_churn)
    
    spend_model_full = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
    spend_model_full.fit(X_scaled, y_spend)
    
    return churn_model_full, spend_model_full, scaler_full


def run_modeling_pipeline(cleaned_path, output_path):
    """
    Main pipeline to execute customer analytics:
    - Load clean transaction log
    - Build models using split windows
    - Calculate full-period features for predictions
    - Perform RFM scoring
    - Apply predictive models (future churn, future spend)
    - Output final customer profile metrics
    """
    df = pd.read_csv(cleaned_path)
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    
    # 1. Build and train models
    churn_model, spend_model, scaler = build_predictive_models(df)
    
    # 2. Extract features over the ENTIRE dataset for production inference
    min_date = df['InvoiceDate'].min()
    max_date = df['InvoiceDate'].max()
    
    print(f"Generating full-period features up to {max_date.date()} for production deployment...")
    full_features = engineer_customer_features(df, min_date, max_date)
    
    # Scale full-period features
    full_features_scaled = scaler.transform(full_features)
    
    # Predict future churn probability (next 6 months)
    churn_probs = churn_model.predict_proba(full_features_scaled)[:, 1]
    
    # Predict future 6-month spend
    predicted_6m_spend = spend_model.predict(full_features_scaled)
    # Ensure no negative predictions
    predicted_6m_spend = np.clip(predicted_6m_spend, 0, None)
    
    # Add predictions to full features dataframe
    customer_metrics = full_features.copy()
    customer_metrics['ChurnProbability'] = churn_probs
    customer_metrics['Predicted6MonthSpend'] = predicted_6m_spend
    
    # 3. Calculate RFM Scoring (using full period metrics)
    print("Computing RFM Segments...")
    # Recency: higher is worse, so invert scoring (1 = old, 5 = recent)
    customer_metrics['R_Score'] = pd.qcut(customer_metrics['Recency'].rank(method='first'), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    
    # Frequency: higher is better (1 = few, 5 = many)
    customer_metrics['F_Score'] = pd.qcut(customer_metrics['Frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    
    # Monetary: higher is better (1 = low, 5 = high)
    # If monetary is negative or zero, force rank to lowest
    m_values = customer_metrics['Monetary'].clip(lower=0.01)
    customer_metrics['M_Score'] = pd.qcut(m_values.rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    
    # Map to Segments
    customer_metrics['RFM_Segment'] = customer_metrics.apply(get_rfm_segment, axis=1)
    customer_metrics['RFM_Score'] = customer_metrics['R_Score'].astype(str) + customer_metrics['F_Score'].astype(str) + customer_metrics['M_Score'].astype(str)
    
    # 4. Calculate Customer Lifetime Value (CLV)
    # Historical CLV = net spend to date (Monetary column)
    # Predictive CLV = Historical Spend + Predicted Next 12 Month Spend (extrapolated from 6 months prediction)
    customer_metrics['HistoricalCLV'] = customer_metrics['Monetary']
    customer_metrics['PredictiveCLV'] = customer_metrics['HistoricalCLV'] + (customer_metrics['Predicted6MonthSpend'] * 2)
    
    # Ensure predictive CLV is at least equal to historical
    customer_metrics['PredictiveCLV'] = customer_metrics[['HistoricalCLV', 'PredictiveCLV']].max(axis=1)
    
    # Reset index to include CustomerID
    customer_metrics = customer_metrics.reset_index()
    
    # Order columns logically
    cols_to_keep = [
        'CustomerID', 'Recency', 'Frequency', 'Monetary', 'AOV', 'Tenure', 
        'R_Score', 'F_Score', 'M_Score', 'RFM_Score', 'RFM_Segment',
        'ChurnProbability', 'Predicted6MonthSpend', 'HistoricalCLV', 'PredictiveCLV'
    ]
    customer_metrics = customer_metrics[cols_to_keep]
    
    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    customer_metrics.to_csv(output_path, index=False)
    print(f"Customer analytical metrics successfully saved to {output_path}!")
    
    # Output segment distribution
    print("\nCustomer Segment Distribution:")
    print(customer_metrics['RFM_Segment'].value_counts())
    
    return customer_metrics

if __name__ == "__main__":
    run_modeling_pipeline("data/cleaned_transactions.csv", "data/customer_metrics.csv")
