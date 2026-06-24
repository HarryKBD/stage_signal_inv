import sqlite3
import pandas as pd
import FinanceDataReader as fdr
import json
import os

DB_PATH = 'stock_data.db'
JSON_PATH = 'index_constituents.json'

def main():
    print("Starting database initialization...")
    
    # 1. Connect to Database (Creates if not exists)
    conn = sqlite3.connect(DB_PATH)
    
    # 2. Fetch Korean stock listings
    print("Fetching Korean stock listings from FinanceDataReader...")
    df_kor = fdr.StockListing('KOR')
    print(f"Fetched {len(df_kor)} Korean stock tickers.")
    
    # Add index flags to KOR DataFrame
    df_kor['IsKOSPI200'] = 0
    df_kor['IsKOSDAQ150'] = 0
    
    # Map index constituents from JSON
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            constituents = json.load(f)
        
        kospi200_codes = set(constituents.get('kospi200', []))
        kosdaq150_codes = set(constituents.get('kosdaq150', []))
        
        # Apply flags
        df_kor.loc[df_kor['Code'].isin(kospi200_codes), 'IsKOSPI200'] = 1
        df_kor.loc[df_kor['Code'].isin(kosdaq150_codes), 'IsKOSDAQ150'] = 1
        
        print(f"Applied index flags: {len(kospi200_codes)} KOSPI 200, {len(kosdaq150_codes)} KOSDAQ 150.")
    else:
        print("[WARNING] index_constituents.json not found! Index flags won't be set.")
        
    # Write tickers to db
    df_kor.to_sql('tickers', conn, if_exists='replace', index=False)
    print("Saved 'tickers' table to database.")
    
    # 3. Fetch US stock listings (NASDAQ, NYSE, AMEX)
    print("Fetching US stock listings from FinanceDataReader...")
    us_dfs = []
    for market in ['NASDAQ', 'NYSE', 'AMEX']:
        try:
            print(f"Fetching {market}...")
            df = fdr.StockListing(market)
            df['Market'] = market
            # Keep only the target columns
            df = df[['Symbol', 'Name', 'IndustryCode', 'Industry', 'Market']]
            us_dfs.append(df)
        except Exception as e:
            print(f"Error fetching {market}: {e}")
            
    if us_dfs:
        df_us = pd.concat(us_dfs, ignore_index=True)
        # Write us_tickers to db
        df_us.to_sql('us_tickers', conn, if_exists='replace', index=False)
        print(f"Saved 'us_tickers' table with {len(df_us)} symbols to database.")
    else:
        print("[ERROR] No US tickers fetched.")
        
    # Close connection
    conn.close()
    print("Database initialization finished successfully!")

if __name__ == '__main__':
    main()
