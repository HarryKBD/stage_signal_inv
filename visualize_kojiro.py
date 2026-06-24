import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
import sys
import os
import platform

# Font configuration for Hangul support
if platform.system() == 'Darwin':  # macOS
    plt.rcParams['font.family'] = 'AppleGothic'
elif platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False # Fix for minus sign

def get_data(ticker):
    conn = sqlite3.connect('stock_data.db')
    query_kr = "SELECT Date, Open, High, Low, Close, Volume, Name FROM stock_prices WHERE Code = ? ORDER BY Date"
    df = pd.read_sql_query(query_kr, conn, params=(ticker,), parse_dates=['Date'])
    
    if df.empty:
        query_us = 'SELECT "index" as Date, Open, High, Low, Close, Volume, Name FROM us_stock_prices WHERE Code = ? ORDER BY "index"'
        df = pd.read_sql_query(query_us, conn, params=(ticker,), parse_dates=['Date'])
    
    conn.close()
    if not df.empty:
        df.set_index('Date', inplace=True)
    return df

def calculate_stages(df):
    # Standard Moving Averages (SMA)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA40'] = df['Close'].rolling(window=40).mean()
    
    # Grand Cycle MACD
    # MACD Short: 5 EMA - 20 EMA
    # MACD Mid: 5 EMA - 40 EMA
    # MACD Long: 20 EMA - 40 EMA
    ema5 = df['Close'].ewm(span=5, adjust=False).mean()
    ema20 = df['Close'].ewm(span=20, adjust=False).mean()
    ema40 = df['Close'].ewm(span=40, adjust=False).mean()
    
    df['MACD_S'] = ema5 - ema20
    df['MACD_M'] = ema5 - ema40
    df['MACD_L'] = ema20 - ema40
    
    conditions = [
        (df['MA5'] > df['MA20']) & (df['MA20'] > df['MA40']),  # 1
        (df['MA20'] > df['MA5']) & (df['MA5'] > df['MA40']),   # 2
        (df['MA20'] > df['MA40']) & (df['MA40'] > df['MA5']),  # 3
        (df['MA40'] > df['MA20']) & (df['MA20'] > df['MA5']),  # 4
        (df['MA40'] > df['MA5']) & (df['MA5'] > df['MA20']),   # 5
        (df['MA5'] > df['MA40']) & (df['MA40'] > df['MA20'])   # 6
    ]
    choices = [1, 2, 3, 4, 5, 6]
    df['Stage'] = np.select(conditions, choices, default=0)
    return df

def plot_kojiro(ticker):
    df = get_data(ticker)
    if df.empty:
        print(f"No data found for {ticker}")
        return

    name = df.iloc[0]['Name']
    df = calculate_stages(df)
    
    # Use last 100 days for the plot
    plot_df = df.tail(100).copy()
    current_stage = int(plot_df.iloc[-1]['Stage'] if not pd.isna(plot_df.iloc[-1]['Stage']) else 0)
    
    # Define stage names
    stage_names = {
        1: "Stage 1: Stable Upward",
        2: "Stage 2: Upward Slowdown",
        3: "Stage 3: Early Downward",
        4: "Stage 4: Stable Downward",
        5: "Stage 5: Downward Slowdown",
        6: "Stage 6: Early Upward"
    }
    
    print(f"\n[Status: {name} ({ticker})]")
    print(f"Current Price: {plot_df.iloc[-1]['Close']:,.0f}")
    print(f"Current Stage: {current_stage} ({stage_names.get(current_stage, 'Unknown')})")
    
    # Visualization using mplfinance
    # Main Chart Addplots (SMAs)
    apds = [
        mpf.make_addplot(plot_df['MA5'], color='red', width=1.0, label='SMA5'),
        mpf.make_addplot(plot_df['MA20'], color='orange', width=1.0, label='SMA20'),
        mpf.make_addplot(plot_df['MA40'], color='blue', width=1.0, label='SMA40'),
        # Subplot 2: MACD (S, M, L)
        mpf.make_addplot(plot_df['MACD_S'], panel=1, color='red', width=0.8, label='MACD-S'),
        mpf.make_addplot(plot_df['MACD_M'], panel=1, color='orange', width=0.8, label='MACD-M'),
        mpf.make_addplot(plot_df['MACD_L'], panel=1, color='blue', width=0.8, label='MACD-L'),
    ]
    
    file_name = f"plot_macd_{ticker}.png"
    
    # Customize the plot
    title_font = 'AppleGothic' if platform.system() == 'Darwin' else 'Malgun Gothic'
    s = mpf.make_mpf_style(base_mpf_style='charles', rc={'font.family': title_font})
    
    fig, axes = mpf.plot(
        plot_df,
        type='candle',
        addplot=apds,
        title=f"\n{name} ({ticker}) - SMA & GC MACD\nCurrent: {stage_names.get(current_stage)}",
        style=s,
        volume=False, # Volume off to focus on MACD
        figsize=(12, 10),
        panel_ratios=(6, 4),
        returnfig=True,
        savefig=file_name
    )
    
    print(f"Graph with MACD has been saved as: {os.path.abspath(file_name)}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else '005930'
    plot_kojiro(target)
