import sqlite3
import pandas as pd
import numpy as np
from visualize_kojiro import calculate_stages, plot_kojiro

def find_early_buy_signals():
    conn = sqlite3.connect('stock_data.db')
    
    print("Scanning for EARLY Buy Signals (Stage 6 recovery or Stage 1 entry)...")
    kr_codes = pd.read_sql_query("SELECT DISTINCT Code, Name FROM stock_prices", conn)
    early_buy_candidates = []
    
    for _, row in kr_codes.iterrows():
        code = row['Code']
        name = row['Name']
        
        df = pd.read_sql_query("SELECT Date, Open, High, Low, Close, Volume, Name FROM stock_prices WHERE Code = ? ORDER BY Date", conn, params=(code,))
        
        if len(df) < 60: # Need more data for SMA and MACD stability
            continue
            
        df = calculate_stages(df)
        
        if len(df) < 3:
            continue
            
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 1. Official Stage 1 Entry
        is_stage1_entry = (curr['Stage'] == 1 and prev['Stage'] != 1)
        
        # 2. Early Stage 6 Recovery (MACD bottoming and rising)
        # Check if MACD values are starting to rise while in Stage 6 or Stage 5
        is_macd_rising = (curr['MACD_S'] > prev['MACD_S']) and \
                         (curr['MACD_M'] > prev['MACD_M']) and \
                         (curr['MACD_L'] > prev['MACD_L'])
        
        is_early_signal = (curr['Stage'] in [5, 6]) and is_macd_rising
        
        if is_stage1_entry or is_early_signal:
            reason = "Stage 1 Entry" if is_stage1_entry else "Early MACD Recovery"
            early_buy_candidates.append({'Code': code, 'Name': name, 'Reason': reason})
    
    conn.close()
    return early_buy_candidates

if __name__ == "__main__":
    candidates = find_early_buy_signals()
    
    print("\n" + "="*60)
    print(f"SMA & MACD BUY SIGNALS: {len(candidates)} found")
    print("="*60)
    
    if not candidates:
        print("No early signals found for the latest date.")
    else:
        # Show top candidates and generate plots
        # Limiting to 20 for brevity
        for i, s in enumerate(candidates[:20]):
            print(f"[{i+1}/{len(candidates)}] {s['Name']} ({s['Code']}) - {s['Reason']}")
            try:
                plot_kojiro(s['Code'])
            except Exception as e:
                print(f"Failed to plot {s['Code']}: {e}")
        
        if len(candidates) > 20:
            print(f"... and {len(candidates)-20} more.")

        print("\n" + "="*60)
        print("Visualization charts with MACD have been generated.")
        print("Check the files: plot_macd_XXXXXX.png")
        print("="*60)
