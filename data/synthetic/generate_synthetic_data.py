import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

def generate_synthetic_data(num_customers=1000, num_transactions=20000, start_date="2024-01-01", output_path="data/synthetic/synthetic_data.csv"):
    """
    Generates synthetic transaction data matching the Online Retail II dataset schema.
    
    Args:
        num_customers (int): Number of unique customers.
        num_transactions (int): Approximate number of transactions to generate.
        start_date (str): Starting date for transactions (YYYY-MM-DD).
        output_path (str): Where to save the generated CSV.
    """
    np.random.seed(42)
    random.seed(42)
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    
    # Generate customers
    customer_ids = [10000 + i for i in range(num_customers)]
    
    # Some customers buy more frequently (Beta distribution)
    customer_frequencies = np.random.beta(a=2, b=5, size=num_customers)
    customer_frequencies = customer_frequencies / customer_frequencies.sum()
    
    # Generate transactions
    dates = [start_dt + timedelta(days=random.randint(0, 365), hours=random.randint(8, 20), minutes=random.randint(0, 59)) for _ in range(num_transactions)]
    dates.sort()
    
    # Select customers based on their assigned probabilities
    selected_customers = np.random.choice(customer_ids, size=num_transactions, p=customer_frequencies, replace=True)
    
    # Generate products
    stock_codes = [f"{random.randint(10000, 99999)}" for _ in range(100)]
    descriptions = [f"Product_{code}" for code in stock_codes]
    product_map = dict(zip(stock_codes, descriptions))
    price_map = {code: round(random.uniform(5.0, 100.0), 2) for code in stock_codes}
    
    data = []
    invoice_counter = 500000
    
    for i in range(num_transactions):
        # 30% chance to share the same invoice as the previous transaction
        if i > 0 and random.random() < 0.3:
            invoice_no = data[-1]['InvoiceNo']
            customer = data[-1]['CustomerID']
            date = data[-1]['InvoiceDate']
        else:
            invoice_no = str(invoice_counter)
            invoice_counter += 1
            customer = selected_customers[i]
            date = dates[i]
            
        stock = random.choice(stock_codes)
        
        # 5% chance of return (cancelled invoice, starts with C)
        is_cancelled = random.random() < 0.05
        if is_cancelled:
            invoice_no = "C" + invoice_no.replace("C", "")
            quantity = -random.randint(1, 5)
        else:
            quantity = random.randint(1, 10)
            
        data.append({
            "InvoiceNo": invoice_no,
            "StockCode": stock,
            "Description": product_map[stock],
            "Quantity": quantity,
            "InvoiceDate": date,
            "UnitPrice": price_map[stock],
            "CustomerID": float(customer),
            "Country": "United Kingdom"
        })
        
    df = pd.DataFrame(data)
    df["InvoiceDate"] = df["InvoiceDate"].dt.strftime("%Y-%m-%d %H:%M:%S")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} records for {df['CustomerID'].nunique()} unique customers.")
    print(f"Data saved to {output_path}")

if __name__ == "__main__":
    generate_synthetic_data()
