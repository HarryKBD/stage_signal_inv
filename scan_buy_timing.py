import sqlite3
import pandas as pd
import numpy as np
from visualize_kojiro import calculate_stages, plot_kojiro

def find_new_stage1_entries():
    conn = sqlite3.connect('stock_data.db')
    
    print("Scanning for Korean stocks that JUST entered Stage 1...")
    kr_codes = pd.read_sql_query("SELECT DISTINCT Code, Name FROM stock_prices", conn)
    buy_candidates = []
    
    for _, row in kr_codes.iterrows():
        code = row['Code']
        name = row['Name']
        
        # Get enough data to calculate EMA and check transition
        df = pd.read_sql_query("SELECT Date, Open, High, Low, Close, Volume, Name FROM stock_prices WHERE Code = ? ORDER BY Date", conn, params=(code,))
        
        if len(df) < 42: # Need enough for EMAs + transition check
            continue
            
        df = calculate_stages(df)
        
        # Check transition: Previous was NOT 1, Current IS 1
        if len(df) >= 2:
            prev_stage = df.iloc[-2]['Stage']
            curr_stage = df.iloc[-1]['Stage']
            
            if curr_stage == 1 and prev_stage != 1:
                buy_candidates.append({'Code': code, 'Name': name})
    
    conn.close()
    return buy_candidates

if __name__ == "__main__":
    candidates = find_new_stage1_entries()
    
    print("\n" + "="*50)
    print(f"NEW BUY SIGNALS (Just Entered Stage 1): {len(candidates)} found")
    print("="*50)
    
    if not candidates:
        print("No new entries found for the latest date.")
    else:
        # Sort or limit if necessary, but here we process them
        for i, s in enumerate(candidates):
            print(f"[{i+1}/{len(candidates)}] Processing {s['Name']} ({s['Code']})...")
            try:
                plot_kojiro(s['Code'])
            except Exception as e:
                print(f"Failed to plot {s['Code']}: {e}")
        
        print("\n" + "="*50)
        print("All visualization charts have been generated.")
        print("Check the files: plot_XXXXXX.png")
        print("="*50)
