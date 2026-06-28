import sys
import os
import sqlite3
import argparse
import pandas as pd
import numpy as np

# 프로젝트 어디로 이동해도 따라가도록, 이 스크립트 위치 기준으로 DB 경로 산출
_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_HERE, "stock_data.db")

def get_market_data(market_flag, etf_code):
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Fetch ETF prices
    query_etf = f"""
        SELECT substr(Date, 1, 10) as DateStr, Close as ETF_Close
        FROM stock_prices
        WHERE Code = '{etf_code}' AND Date >= '2023-01-01'
        ORDER BY Date ASC
    """
    df_etf = pd.read_sql_query(query_etf, conn)
    
    # 2. Fetch daily signals count
    query_signals = f"""
        SELECT h.Date, h.SignalType, COUNT(*) as Count
        FROM historical_signals h
        JOIN tickers t ON h.Code = t.Code
        WHERE t.{market_flag} = 1
        GROUP BY h.Date, h.SignalType
        ORDER BY h.Date ASC
    """
    df_sig = pd.read_sql_query(query_signals, conn)
    df_sig['Date'] = pd.to_datetime(df_sig['Date'])
    df_sig['DateStr'] = df_sig['Date'].dt.strftime('%Y-%m-%d')
    
    df_sig_pivot = df_sig.pivot(index='DateStr', columns='SignalType', values='Count').fillna(0).reset_index()
    
    # Merge ETF and signals
    df_merged = pd.merge(df_etf, df_sig_pivot, on='DateStr', how='left').fillna(0)
    df_merged = df_merged.sort_values('DateStr').reset_index(drop=True)
    
    conn.close()
    
    # Calculate Net Breadth & SMA-10
    df_merged['net_breadth'] = df_merged.get('stage1', 0) - df_merged.get('stage4', 0)
    df_merged['net_sma10'] = df_merged['net_breadth'].rolling(10).mean()
    
    return df_merged

def calculate_k200_signals(df):
    pos_s2 = 0
    last_sig_s2 = "CASH"
    sig_date_s2 = "N/A"
    sig_price_s2 = 0.0
    
    pos_s3 = 0
    last_sig_s3 = "CASH"
    sig_date_s3 = "N/A"
    sig_price_s3 = 0.0
    
    history_s2 = []
    history_s3 = []
    
    for i in range(len(df)):
        close = float(df.loc[i, 'ETF_Close'])
        date_str = df.loc[i, 'DateStr']
        eb = df.loc[i, 'early_buy'] if 'early_buy' in df.columns else 0
        s1 = df.loc[i, 'stage1'] if 'stage1' in df.columns else 0
        s4 = df.loc[i, 'stage4'] if 'stage4' in df.columns else 0
        
        # Strategy 2: Capitulation Reversal (EB >= 30, S1 <= 50)
        if pos_s2 == 0:
            if eb >= 30 and s1 <= 50:
                pos_s2 = 1
                last_sig_s2 = "BUY"
                sig_date_s2 = date_str
                sig_price_s2 = close
        else:
            if s4 >= 80 or s1 < 45:
                pos_s2 = 0
                last_sig_s2 = "CASH"
                sig_date_s2 = date_str
                sig_price_s2 = close
                
        # Strategy 3: Net Breadth SMA10 Crossover
        net = df.loc[i, 'net_breadth']
        sma = df.loc[i, 'net_sma10']
        if not pd.isna(sma):
            prev_net = df.loc[i-1, 'net_breadth'] if i > 0 else 0
            prev_sma = df.loc[i-1, 'net_sma10'] if i > 0 else 0
            
            if pos_s3 == 0:
                if net > sma and prev_net <= prev_sma:
                    pos_s3 = 1
                    last_sig_s3 = "BUY"
                    sig_date_s3 = date_str
                    sig_price_s3 = close
            else:
                if net < sma and prev_net >= prev_sma:
                    pos_s3 = 0
                    last_sig_s3 = "CASH"
                    sig_date_s3 = date_str
                    sig_price_s3 = close
                    
        history_s2.append({'pos': pos_s2, 'sig': last_sig_s2, 'date': sig_date_s2, 'price': sig_price_s2})
        history_s3.append({'pos': pos_s3, 'sig': last_sig_s3, 'date': sig_date_s3, 'price': sig_price_s3})
        
    return history_s2, history_s3

def calculate_kq150_signals(df):
    pos_s2 = 0
    last_sig_s2 = "CASH"
    sig_date_s2 = "N/A"
    sig_price_s2 = 0.0
    
    pos_s3 = 0
    last_sig_s3 = "CASH"
    sig_date_s3 = "N/A"
    sig_price_s3 = 0.0
    
    history_s2 = []
    history_s3 = []
    
    for i in range(len(df)):
        close = float(df.loc[i, 'ETF_Close'])
        date_str = df.loc[i, 'DateStr']
        eb = df.loc[i, 'early_buy'] if 'early_buy' in df.columns else 0
        s1 = df.loc[i, 'stage1'] if 'stage1' in df.columns else 0
        s4 = df.loc[i, 'stage4'] if 'stage4' in df.columns else 0
        
        # Strategy 2: Capitulation Reversal (EB >= 15, S1 <= 35)
        if pos_s2 == 0:
            if eb >= 15 and s1 <= 35:
                pos_s2 = 1
                last_sig_s2 = "BUY"
                sig_date_s2 = date_str
                sig_price_s2 = close
        else:
            if s1 >= 70 or s4 >= 75:
                pos_s2 = 0
                last_sig_s2 = "CASH"
                sig_date_s2 = date_str
                sig_price_s2 = close
                
        # Strategy 3: Net Breadth SMA10 Crossover
        net = df.loc[i, 'net_breadth']
        sma = df.loc[i, 'net_sma10']
        if not pd.isna(sma):
            prev_net = df.loc[i-1, 'net_breadth'] if i > 0 else 0
            prev_sma = df.loc[i-1, 'net_sma10'] if i > 0 else 0
            
            if pos_s3 == 0:
                if net > sma and prev_net <= prev_sma:
                    pos_s3 = 1
                    last_sig_s3 = "BUY"
                    sig_date_s3 = date_str
                    sig_price_s3 = close
            else:
                if net < sma and prev_net >= prev_sma:
                    pos_s3 = 0
                    last_sig_s3 = "CASH"
                    sig_date_s3 = date_str
                    sig_price_s3 = close
                    
        history_s2.append({'pos': pos_s2, 'sig': last_sig_s2, 'date': sig_date_s2, 'price': sig_price_s2})
        history_s3.append({'pos': pos_s3, 'sig': last_sig_s3, 'date': sig_date_s3, 'price': sig_price_s3})
        
    return history_s2, history_s3

def get_visual_length(s):
    import re
    # Strip ANSI color codes before measuring length
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean_s = ansi_escape.sub('', s)
    length = 0
    for char in clean_s:
        if ord(char) > 127:
            length += 2
        else:
            length += 1
    return length

def print_border_line(content, target_width=58):
    vis_len = get_visual_length(content)
    padding = target_width - vis_len
    if padding < 0:
        padding = 0
    print(f"│ {content}" + " " * padding + " │")

def print_status_report(df, h_s2, h_s3, target_date, title):
    # Find matching row index
    matches = df[df['DateStr'] == target_date]
    if matches.empty:
        # Get the latest row index
        idx = len(df) - 1
        actual_date = df.loc[idx, 'DateStr']
        print(f"⚠️ Warning: {target_date} is not a valid trading date. Using closest trading date: {actual_date}")
    else:
        idx = matches.index[0]
        actual_date = target_date

    row = df.loc[idx]
    s2_state = h_s2[idx]
    s3_state = h_s3[idx]
    
    # Calculate differences compared to 1 day ago and 5-day average
    prev_1d_row = df.loc[idx - 1] if idx - 1 >= 0 else None
    
    # Calculate 5-day average ending at target date (inclusive)
    if idx - 4 >= 0:
        sub_df_5d = df.loc[idx - 4 : idx]
        eb_avg_5d = sub_df_5d['early_buy'].mean()
        s1_avg_5d = sub_df_5d['stage1'].mean()
        s4_avg_5d = sub_df_5d['stage4'].mean()
    else:
        eb_avg_5d = s1_avg_5d = s4_avg_5d = None
    
    def get_diff_str(curr_val, prev_row, col_name):
        if prev_row is None:
            return "N/A"
        diff = int(curr_val) - int(prev_row.get(col_name, 0))
        if diff > 0:
            return f"+{diff}"
        elif diff < 0:
            return f"{diff}"
        else:
            return "+0"
            
    def get_avg_diff_str(curr_val, avg_val):
        if avg_val is None:
            return "N/A"
        diff = float(curr_val) - float(avg_val)
        if diff > 0:
            return f"+{diff:.1f}"
        elif diff < 0:
            return f"{diff:.1f}"
        else:
            return "+0.0"
            
    eb_val = int(row.get('early_buy', 0))
    s1_val = int(row.get('stage1', 0))
    s4_val = int(row.get('stage4', 0))
    
    eb_diff_1d = get_diff_str(eb_val, prev_1d_row, 'early_buy')
    eb_diff_5d_avg = get_avg_diff_str(eb_val, eb_avg_5d)
    
    s1_diff_1d = get_diff_str(s1_val, prev_1d_row, 'stage1')
    s1_diff_5d_avg = get_avg_diff_str(s1_val, s1_avg_5d)
    
    s4_diff_1d = get_diff_str(s4_val, prev_1d_row, 'stage4')
    s4_diff_5d_avg = get_avg_diff_str(s4_val, s4_avg_5d)
    
    net_val = int(row['net_breadth'])
    sma_val = float(row['net_sma10'])
    sma_str = f"{sma_val:.1f}" if not pd.isna(sma_val) else "N/A"
    
    # Text formatting colors
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Set status badges
    s2_badge = f"{GREEN}● BUY/HOLD{RESET}" if s2_state['pos'] == 1 else f"{YELLOW}● CASH/WAIT{RESET}"
    s3_badge = f"{GREEN}● BUY/HOLD{RESET}" if s3_state['pos'] == 1 else f"{YELLOW}● CASH/WAIT{RESET}"
    
    print("┌────────────────────────────────────────────────────────────┐")
    print_border_line(f"{BOLD}{CYAN}{title}{RESET}")
    print_border_line(f"기준 영업일: {BOLD}{actual_date}{RESET}")
    print("├────────────────────────────────────────────────────────────┤")
    print_border_line(" [세부 지표 현황]")
    print_border_line(f" - ETF 종가   : {int(row['ETF_Close']):,d}원")
    print_border_line(f" - Early Buy  : {eb_val:<3d} (전일: {eb_diff_1d:>3s}, 5일평균 대비: {eb_diff_5d_avg:>5s})")
    print_border_line(f" - Stage 1    : {s1_val:<3d} (전일: {s1_diff_1d:>3s}, 5일평균 대비: {s1_diff_5d_avg:>5s})")
    print_border_line(f" - Stage 4    : {s4_val:<3d} (전일: {s4_diff_1d:>3s}, 5일평균 대비: {s4_diff_5d_avg:>5s})")
    print_border_line(f" - 넷 브레드  : {net_val:<4d} (Stage 1 - Stage 4)")
    print_border_line(f" - Net SMA 10 : {sma_str}")
    print("├────────────────────────────────────────────────────────────┤")
    print_border_line(" [전략 1: 투매 역발상 (Capitulation Reversal)]")
    print_border_line(f" - 현재 포지션: {s2_badge}")
    print_border_line(f" - 최근 신호  : {s2_state['sig']} ({s2_state['date']}) @ {int(s2_state['price']):,d}원")
    print_border_line("")
    print_border_line(" [전략 2: 넷 브레드 SMA-10 크로스 (Crossover)]")
    print_border_line(f" - 현재 포지션: {s3_badge}")
    print_border_line(f" - 최근 신호  : {s3_state['sig']} ({s3_state['date']}) @ {int(s3_state['price']):,d}원")
    print("└────────────────────────────────────────────────────────────┘")
    print()

def main():
    parser = argparse.ArgumentParser(description="KOR Market Indicator & Strategy Signal Status Report")
    parser.add_argument("date", nargs="?", help="Target date format: YYYY-MM-DD (e.g. 2026-06-18)")
    args = parser.parse_args()
    
    # 1. Fetch data
    df_k200 = get_market_data("IsKOSPI200", "252650")
    df_kq150 = get_market_data("IsKOSDAQ150", "229200")
    
    # Determine target date
    if args.date:
        target_date = args.date
    else:
        # Default to latest date in DB
        target_date = df_k200.iloc[-1]['DateStr']
        
    # 2. Calculate Signals
    h_s2_k, h_s3_k = calculate_k200_signals(df_k200)
    h_s2_q, h_s3_q = calculate_kq150_signals(df_kq150)
    
    print(f"\n==============================================================")
    print(f"             MARKET SIGNALS & indicator REPORT")
    print(f"==============================================================\n")
    
    print_status_report(df_k200, h_s2_k, h_s3_k, target_date, "코스피 200 동일가중 (KODEX 200동일가중: 252650)")
    print_status_report(df_kq150, h_s2_q, h_s3_q, target_date, "코스닥 150 (KODEX 코스닥150: 229200)")

if __name__ == "__main__":
    main()
