import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "/Users/keybd/work/mov_invest/stock_data.db"

def inspect_data():
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Fetch ETF prices
    query_etf = """
        SELECT substr(Date, 1, 10) as Date, Close as ETF_Close
        FROM stock_prices
        WHERE Code = '229200' AND Date >= '2020-01-01'
        ORDER BY Date ASC
    """
    df_etf = pd.read_sql_query(query_etf, conn)
    df_etf['Date'] = pd.to_datetime(df_etf['Date'])
    
    # 2. Fetch KOSDAQ 150 signal counts
    query_signals = """
        SELECT h.Date, h.SignalType, COUNT(*) as Count
        FROM historical_signals h
        JOIN tickers t ON h.Code = t.Code
        WHERE t.IsKOSDAQ150 = 1
        GROUP BY h.Date, h.SignalType
        ORDER BY h.Date ASC
    """
    df_sig = pd.read_sql_query(query_signals, conn)
    df_sig['Date'] = pd.to_datetime(df_sig['Date'])
    
    # Pivot signals to have columns for each SignalType
    df_sig_pivot = df_sig.pivot(index='Date', columns='SignalType', values='Count').fillna(0).reset_index()
    
    # Merge ETF and signals
    df_merged = pd.merge(df_etf, df_sig_pivot, on='Date', how='left').fillna(0)
    df_merged = df_merged.sort_values('Date').reset_index(drop=True)
    
    conn.close()
    
    print("Columns:", df_merged.columns)
    print("Data head (first 5 rows):")
    print(df_merged.head())
    print("\nData tail (last 5 rows):")
    print(df_merged.tail())
    print("\nSummary statistics:")
    print(df_merged.describe())
    
    # Save merged data to scratch csv for convenience
    df_merged.to_csv("scratch_merged_kosdaq150.csv", index=False)
    print("\nSaved merged data to scratch_merged_kosdaq150.csv")

if __name__ == "__main__":
    inspect_data()
