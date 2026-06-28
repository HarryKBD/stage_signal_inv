import sqlite3
import pandas as pd
import numpy as np
import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

DB_PATH = 'stock_data.db'

def calculate_stages(df):
    # Standard Moving Averages (SMA)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA40'] = df['Close'].rolling(window=40).mean()
    
    # Grand Cycle MACD
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

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Cache table for Early Buy signals (Page 2)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS early_buy_signals (
        Market TEXT,
        Code TEXT,
        Name TEXT,
        Stage INTEGER,
        SignalDate TEXT,
        DurationDays INTEGER,
        Close REAL,
        UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (Market, Code)
    );
    """)
    # Cache table for Stage 1 signals (Page 4)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stage1_signals (
        Market TEXT,
        Code TEXT,
        Name TEXT,
        Stage INTEGER,
        EntryDate TEXT,
        DurationDays INTEGER,
        Close REAL,
        UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (Market, Code)
    );
    """)
    # Cache table for Stage 4 signals (Page 5)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stage4_signals (
        Market TEXT,
        Code TEXT,
        Name TEXT,
        Stage INTEGER,
        EntryDate TEXT,
        DurationDays INTEGER,
        Close REAL,
        UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (Market, Code)
    );
    """)
    # New table for Stage trends statistics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stage_trends (
        Market TEXT,
        Date TEXT,
        Stage1_Count INTEGER,
        Stage2_Count INTEGER,
        Stage3_Count INTEGER,
        Stage4_Count INTEGER,
        Stage5_Count INTEGER,
        Stage6_Count INTEGER,
        Total_Count INTEGER,
        PRIMARY KEY (Market, Date)
    );
    """)
    # New table for Historical Signals (for In/Out changelogs and 6-month trends)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historical_signals (
        Date TEXT,
        Market TEXT,
        Code TEXT,
        Name TEXT,
        SignalType TEXT,
        Stage INTEGER,
        Close REAL,
        PRIMARY KEY (Date, Market, Code, SignalType)
    );
    """)
    conn.commit()
    conn.close()

def process_single_stock_combined(code, name, df_stock):
    if len(df_stock) < 45:  # Minimum required days to calculate 40 SMA
        return None
        
    df_calc = calculate_stages(df_stock.copy())
    
    if len(df_calc) < 3:
        return None
        
    curr = df_calc.iloc[-1]
    prev = df_calc.iloc[-2]
    
    curr_stage = int(curr['Stage'])
    
    result = {
        'early_buy': None, 
        'stage1': None, 
        'stage4': None,
        'curr_stage': curr_stage,
        'code': code,
        'name': name,
        'close': float(curr['Close'])
    }
    
    # 1. Early Buy Check (Stage 5/6 + MACD rising)
    is_stage_5_or_6 = curr_stage in [5, 6]
    is_macd_rising = (curr['MACD_S'] > prev['MACD_S']) and \
                     (curr['MACD_M'] > prev['MACD_M']) and \
                     (curr['MACD_L'] > prev['MACD_L'])
                     
    if is_stage_5_or_6 and is_macd_rising:
        duration_days = 0
        signal_date = None
        for i in range(len(df_calc) - 1, 0, -1):
            c_row = df_calc.iloc[i]
            p_row = df_calc.iloc[i-1]
            row_stage = int(c_row['Stage'])
            row_macd_rising = (c_row['MACD_S'] > p_row['MACD_S']) and \
                              (c_row['MACD_M'] > p_row['MACD_M']) and \
                              (c_row['MACD_L'] > p_row['MACD_L'])
            
            if (row_stage in [5, 6]) and row_macd_rising:
                duration_days += 1
                dt_val = c_row.name
                signal_date = dt_val.strftime('%Y-%m-%d') if isinstance(dt_val, pd.Timestamp) else str(dt_val)[:10]
            else:
                break
        if duration_days > 0:
            result['early_buy'] = {
                'Code': code,
                'Name': name,
                'Stage': curr_stage,
                'SignalDate': signal_date,
                'DurationDays': duration_days,
                'Close': float(curr['Close'])
            }
            
    # 2. Stage 1 Check (Stable Upward)
    if curr_stage == 1:
        duration_days = 0
        entry_date = None
        for i in range(len(df_calc) - 1, -1, -1):
            c_row = df_calc.iloc[i]
            if int(c_row['Stage']) == 1:
                duration_days += 1
                dt_val = c_row.name
                entry_date = dt_val.strftime('%Y-%m-%d') if isinstance(dt_val, pd.Timestamp) else str(dt_val)[:10]
            else:
                break
        if duration_days > 0:
            result['stage1'] = {
                'Code': code,
                'Name': name,
                'Stage': curr_stage,
                'EntryDate': entry_date,
                'DurationDays': duration_days,
                'Close': float(curr['Close'])
            }
            
    # 3. Stage 4 Check (Stable Downward)
    if curr_stage == 4:
        duration_days = 0
        entry_date = None
        for i in range(len(df_calc) - 1, -1, -1):
            c_row = df_calc.iloc[i]
            if int(c_row['Stage']) == 4:
                duration_days += 1
                dt_val = c_row.name
                entry_date = dt_val.strftime('%Y-%m-%d') if isinstance(dt_val, pd.Timestamp) else str(dt_val)[:10]
            else:
                break
        if duration_days > 0:
            result['stage4'] = {
                'Code': code,
                'Name': name,
                'Stage': curr_stage,
                'EntryDate': entry_date,
                'DurationDays': duration_days,
                'Close': float(curr['Close'])
            }
            
    return result

def analyze_single_stock(code, name, group, market, min_date_dt):
    group = group.sort_values('Date')
    if len(group) < 45:
        return []
        
    # Standard Moving Averages (SMA)
    group['MA5'] = group['Close'].rolling(window=5).mean()
    group['MA20'] = group['Close'].rolling(window=20).mean()
    group['MA40'] = group['Close'].rolling(window=40).mean()
    
    # Grand Cycle MACD
    ema5 = group['Close'].ewm(span=5, adjust=False).mean()
    ema20 = group['Close'].ewm(span=20, adjust=False).mean()
    ema40 = group['Close'].ewm(span=40, adjust=False).mean()
    
    group['MACD_S'] = ema5 - ema20
    group['MACD_M'] = ema5 - ema40
    group['MACD_L'] = ema20 - ema40
    
    # MACD Rising
    group['MACD_S_prev'] = group['MACD_S'].shift(1)
    group['MACD_M_prev'] = group['MACD_M'].shift(1)
    group['MACD_L_prev'] = group['MACD_L'].shift(1)
    
    group['is_macd_rising'] = (group['MACD_S'] > group['MACD_S_prev']) & \
                              (group['MACD_M'] > group['MACD_M_prev']) & \
                              (group['MACD_L'] > group['MACD_L_prev'])
    
    # Stage logic
    conditions = [
        (group['MA5'] > group['MA20']) & (group['MA20'] > group['MA40']),  # 1
        (group['MA20'] > group['MA5']) & (group['MA5'] > group['MA40']),   # 2
        (group['MA20'] > group['MA40']) & (group['MA40'] > group['MA5']),  # 3
        (group['MA40'] > group['MA20']) & (group['MA20'] > group['MA5']),  # 4
        (group['MA40'] > group['MA5']) & (group['MA5'] > group['MA20']),   # 5
        (group['MA5'] > group['MA40']) & (group['MA40'] > group['MA20'])   # 6
    ]
    choices = [1, 2, 3, 4, 5, 6]
    group['Stage'] = np.select(conditions, choices, default=0)
    
    # Filter for dates >= min_date
    valid = group[group['Date'] >= min_date_dt]
    
    records = []
    for _, row in valid.iterrows():
        date_str = row['Date'].strftime('%Y-%m-%d')
        stage = int(row['Stage'])
        close = float(row['Close'])
        
        # Stage signal
        if stage in [1, 2, 3, 4, 5, 6]:
            records.append({
                'Date': date_str, 'Market': market, 'Code': code, 'Name': name,
                'SignalType': f'stage{stage}', 'Stage': stage, 'Close': close
            })
        # Early buy
        if stage in [5, 6] and row['is_macd_rising']:
            records.append({
                'Date': date_str, 'Market': market, 'Code': code, 'Name': name,
                'SignalType': 'early_buy', 'Stage': stage, 'Close': close
            })
    return records

def process_stock_history_stages(code, df_stock):
    if len(df_stock) < 45:
        return None
    df_calc = calculate_stages(df_stock.copy())
    df_out = df_calc[['Stage']].copy()
    df_out['Code'] = code
    return df_out

def scan_market(market):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    
    print(f"[{market.upper()}] Starting combined scan process...")
    
    if market == 'kor':
        dates_df = pd.read_sql_query("SELECT DISTINCT Date FROM stock_prices ORDER BY Date DESC LIMIT 120", conn)
        if dates_df.empty:
            conn.close()
            return [], [], []
        min_date = dates_df.iloc[-1]['Date']
        
        query = "SELECT Date, Open, High, Low, Close, Volume, Code, Name FROM stock_prices WHERE Date >= ? ORDER BY Date"
        df = pd.read_sql_query(query, conn, params=(min_date,), parse_dates=['Date'])
    else:
        # US Market
        dates_df = pd.read_sql_query("SELECT DISTINCT \"index\" as Date FROM us_stock_prices ORDER BY \"index\" DESC LIMIT 120", conn)
        if dates_df.empty:
            conn.close()
            return [], [], []
        min_date = dates_df.iloc[-1]['Date']
        
        query = "SELECT \"index\" as Date, Open, High, Low, Close, Volume, Code, Name FROM us_stock_prices WHERE \"index\" >= ? ORDER BY \"index\""
        df = pd.read_sql_query(query, conn, params=(min_date,), parse_dates=['Date'])
    
    conn.close()
    
    if df.empty:
        print(f"[{market.upper()}] No stock data fetched.")
        return [], [], []
        
    print(f"[{market.upper()}] Grouping data by stock code...")
    grouped = df.groupby('Code')
    
    tasks = []
    for code, group in grouped:
        group_sorted = group.sort_values('Date')
        name = group_sorted.iloc[0]['Name']
        group_sorted.set_index('Date', inplace=True)
        tasks.append((code, name, group_sorted))
        
    print(f"[{market.upper()}] Scanning {len(tasks)} symbols using ProcessPoolExecutor...")
    
    early_buy_results = []
    stage1_results = []
    stage4_results = []
    
    # Store latest stages of all stocks for today's trend caching
    today_stages = []
    latest_date_str = ""
    if market == 'kor':
        latest_date_str = df['Date'].max().strftime('%Y-%m-%d')
    else:
        latest_date_str = df['Date'].max().strftime('%Y-%m-%d')
        
    workers = min(os.cpu_count() or 4, 8)
    all_stages = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_single_stock_combined, t[0], t[1], t[2]): t for t in tasks}
        for future in as_completed(futures):
            try:
                res = future.result()
                if res:
                    if res['early_buy']:
                        res['early_buy']['Market'] = market
                        early_buy_results.append(res['early_buy'])
                    if res['stage1']:
                        res['stage1']['Market'] = market
                        stage1_results.append(res['stage1'])
                    if res['stage4']:
                        res['stage4']['Market'] = market
                        stage4_results.append(res['stage4'])
                    
                    if res['curr_stage'] in [1, 2, 3, 4, 5, 6]:
                        today_stages.append(res['curr_stage'])
                        all_stages.append({
                            'Code': res['code'],
                            'Name': res['name'],
                            'Stage': res['curr_stage'],
                            'Close': res['close']
                        })
            except Exception as e:
                code_err = futures[future][0]
                print(f"Error processing {code_err}: {e}")
                
    print(f"[{market.upper()}] Found {len(early_buy_results)} early buy, {len(stage1_results)} stage 1, {len(stage4_results)} stage 4 candidates.")
    
    # Save results to DB cache tables
    save_to_cache(market, early_buy_results, stage1_results, stage4_results, all_stages, latest_date_str)
    
    # Record today's stage statistics
    if today_stages:
        save_single_trend(market, latest_date_str, today_stages)
        
    return early_buy_results, stage1_results, stage4_results

def save_to_cache(market, early_buy, stage1, stage4, all_stages, scan_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Update early buy signals cache
    cursor.execute("DELETE FROM early_buy_signals WHERE Market = ?", (market,))
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for r in early_buy:
        cursor.execute("""
        INSERT INTO early_buy_signals (Market, Code, Name, Stage, SignalDate, DurationDays, Close, UpdatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (market, r['Code'], r['Name'], r['Stage'], r['SignalDate'], r['DurationDays'], r['Close'], now))
        
    # Update stage 1 signals cache
    cursor.execute("DELETE FROM stage1_signals WHERE Market = ?", (market,))
    for r in stage1:
        cursor.execute("""
        INSERT INTO stage1_signals (Market, Code, Name, Stage, EntryDate, DurationDays, Close, UpdatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (market, r['Code'], r['Name'], r['Stage'], r['EntryDate'], r['DurationDays'], r['Close'], now))
        
    # Update stage 4 signals cache
    cursor.execute("DELETE FROM stage4_signals WHERE Market = ?", (market,))
    for r in stage4:
        cursor.execute("""
        INSERT INTO stage4_signals (Market, Code, Name, Stage, EntryDate, DurationDays, Close, UpdatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (market, r['Code'], r['Name'], r['Stage'], r['EntryDate'], r['DurationDays'], r['Close'], now))
        
    # Update historical signals (delete first to prevent duplicates for the same day)
    cursor.execute("DELETE FROM historical_signals WHERE Market = ? AND Date = ?", (market, scan_date))
    for r in early_buy:
        cursor.execute("""
        INSERT OR REPLACE INTO historical_signals (Date, Market, Code, Name, SignalType, Stage, Close)
        VALUES (?, ?, ?, ?, 'early_buy', ?, ?)
        """, (scan_date, market, r['Code'], r['Name'], r['Stage'], r['Close']))
        
    for r in all_stages:
        cursor.execute("""
        INSERT OR REPLACE INTO historical_signals (Date, Market, Code, Name, SignalType, Stage, Close)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (scan_date, market, r['Code'], r['Name'], f"stage{r['Stage']}", r['Stage'], r['Close']))
        
    conn.commit()
    conn.close()
    print(f"[{market.upper()}] Cache tables updated successfully.")

def save_single_trend(market, date_str, stages_list):
    # Counts occurrences of each stage
    counts = {i: stages_list.count(i) for i in range(1, 7)}
    total = sum(counts.values())
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT OR REPLACE INTO stage_trends (Market, Date, Stage1_Count, Stage2_Count, Stage3_Count, Stage4_Count, Stage5_Count, Stage6_Count, Total_Count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (market, date_str, counts[1], counts[2], counts[3], counts[4], counts[5], counts[6], total))
    
    conn.commit()
    conn.close()
    print(f"[{market.upper()}] Saved trend for {date_str}: Total={total}")

def backfill_stage_trends(market):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    
    print(f"[{market.upper()}] Starting historical backfill of Stage trends...")
    
    # We backfill 1500 days of history
    if market == 'kor':
        dates_df = pd.read_sql_query("SELECT DISTINCT Date FROM stock_prices ORDER BY Date DESC LIMIT 1500", conn)
        if dates_df.empty:
            conn.close()
            return
        min_date = dates_df.iloc[-1]['Date']
        
        query = "SELECT Date, Close, Code FROM stock_prices WHERE Date >= ? ORDER BY Date"
        df = pd.read_sql_query(query, conn, params=(min_date,), parse_dates=['Date'])
    else:
        dates_df = pd.read_sql_query("SELECT DISTINCT \"index\" as Date FROM us_stock_prices ORDER BY \"index\" DESC LIMIT 1500", conn)
        if dates_df.empty:
            conn.close()
            return
        min_date = dates_df.iloc[-1]['Date']
        
        query = "SELECT \"index\" as Date, Close, Code FROM us_stock_prices WHERE \"index\" >= ? ORDER BY \"index\""
        df = pd.read_sql_query(query, conn, params=(min_date,), parse_dates=['Date'])
        
    conn.close()
    
    if df.empty:
        print(f"[{market.upper()}] No historical data found.")
        return
        
    grouped = df.groupby('Code')
    tasks = []
    for code, group in grouped:
        group_sorted = group.sort_values('Date')
        group_sorted.set_index('Date', inplace=True)
        tasks.append((code, group_sorted))
        
    print(f"[{market.upper()}] Calculating historical stages for {len(tasks)} stocks...")
    
    stages_dfs = []
    workers = min(os.cpu_count() or 4, 8)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_stock_history_stages, t[0], t[1]): t for t in tasks}
        for future in as_completed(futures):
            try:
                res = future.result()
                if res is not None:
                    stages_dfs.append(res)
            except Exception as e:
                print(f"Error backfilling history: {e}")
                
    if not stages_dfs:
        print(f"[{market.upper()}] No stage history calculated.")
        return
        
    # Concatenate all series into one large DataFrame
    print(f"[{market.upper()}] Aggregating historical statistics...")
    df_combined = pd.concat(stages_dfs)
    df_combined.reset_index(inplace=True)
    
    # Format Date index to string 'YYYY-MM-DD'
    df_combined['DateStr'] = df_combined['Date'].dt.strftime('%Y-%m-%d')
    
    # Group by DateStr and Stage to compute size
    grouped_counts = df_combined.groupby(['DateStr', 'Stage']).size().unstack(fill_value=0)
    
    # Ensure all columns 1-6 exist
    for col in range(1, 7):
        if col not in grouped_counts.columns:
            grouped_counts[col] = 0
            
    grouped_counts['Total'] = grouped_counts[[1, 2, 3, 4, 5, 6]].sum(axis=1)
    
    # Write to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear old trends for this market
    cursor.execute("DELETE FROM stage_trends WHERE Market = ?", (market,))
    
    for date_str, row in grouped_counts.iterrows():
        cursor.execute("""
        INSERT INTO stage_trends (Market, Date, Stage1_Count, Stage2_Count, Stage3_Count, Stage4_Count, Stage5_Count, Stage6_Count, Total_Count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (market, date_str, int(row[1]), int(row[2]), int(row[3]), int(row[4]), int(row[5]), int(row[6]), int(row['Total'])))
        
    conn.commit()
    conn.close()
    print(f"[{market.upper()}] Historical backfill completed for {len(grouped_counts)} days.")

def backfill_historical_signals(market):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    
    print(f"[{market.upper()}] Starting historical signals backfill (recent 1500 trading days)...")
    
    if market == 'kor':
        dates_df = pd.read_sql_query("SELECT DISTINCT Date FROM stock_prices ORDER BY Date DESC LIMIT 1500", conn)
        prices_table = 'stock_prices'
    else:
        dates_df = pd.read_sql_query("SELECT DISTINCT \"index\" as Date FROM us_stock_prices ORDER BY \"index\" DESC LIMIT 1500", conn)
        prices_table = 'us_stock_prices'
        
    if dates_df.empty:
        conn.close()
        print(f"[{market.upper()}] No date history found.")
        return
        
    min_date = dates_df.iloc[-1]['Date']
    min_date_str = str(min_date)[:10]
    
    # Calculate starting point for moving averages: min_date - 90 days
    min_date_dt = pd.to_datetime(min_date)
    from datetime import timedelta
    start_calc_date = (min_date_dt - timedelta(days=90)).strftime('%Y-%m-%d')
    
    print(f"[{market.upper()}] Fetching stock prices since {start_calc_date}...")
    if market == 'kor':
        query = f"SELECT Date, Open, High, Low, Close, Volume, Code, Name FROM {prices_table} WHERE Date >= ? ORDER BY Code, Date"
    else:
        query = f"SELECT \"index\" as Date, Open, High, Low, Close, Volume, Code, Name FROM {prices_table} WHERE \"index\" >= ? ORDER BY Code, \"index\""
    
    df_all = pd.read_sql_query(query, conn, params=(start_calc_date,), parse_dates=['Date'])
    conn.close()
    
    if df_all.empty:
        print(f"[{market.upper()}] No price data fetched since {start_calc_date}.")
        return
        
    grouped = df_all.groupby('Code')
    tasks = []
    for code, group in grouped:
        name = group.iloc[0]['Name']
        tasks.append((code, name, group))
        
    print(f"[{market.upper()}] Calculating signals in parallel for {len(tasks)} symbols...")
    
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import os
    workers = min(os.cpu_count() or 4, 8)
    
    historical_records = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(analyze_single_stock, t[0], t[1], t[2], market, min_date_dt): t[0] for t in tasks}
        for future in as_completed(futures):
            try:
                res = future.result()
                if res:
                    historical_records.extend(res)
            except Exception as e:
                print(f"Error backfilling signals for {futures[future]}: {e}")
                
    if historical_records:
        df_hist = pd.DataFrame(historical_records)
        df_hist = df_hist.drop_duplicates(subset=['Date', 'Market', 'Code', 'SignalType'])
        print(f"[{market.upper()}] Writing {len(df_hist)} records to historical_signals...")
        
        conn_write = sqlite3.connect(DB_PATH)
        cursor = conn_write.cursor()
        cursor.execute("DELETE FROM historical_signals WHERE Market = ? AND Date >= ?", (market, min_date_str))
        conn_write.commit()
        
        # Write to sql
        df_hist.to_sql('historical_signals', conn_write, if_exists='append', index=False)
        conn_write.close()
        print(f"[{market.upper()}] Signal history backfill done.")
    else:
        print(f"[{market.upper()}] No historical signals computed.")

def get_cached_candidates(market):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    if market == 'kor':
        query = """
            SELECT e.Code, e.Name, e.Stage, e.SignalDate, e.DurationDays, e.Close, e.UpdatedAt,
                   t.IsKOSPI200, t.IsKOSDAQ150, 0 as IsSP500, 0 as IsNASDAQ100, 0 as IsDOW30
            FROM early_buy_signals e
            LEFT JOIN tickers t ON e.Code = t.Code
            WHERE e.Market = ? 
            ORDER BY e.DurationDays DESC
        """
    else:
        query = """
            SELECT e.Code, e.Name, e.Stage, e.SignalDate, e.DurationDays, e.Close, e.UpdatedAt,
                   0 as IsKOSPI200, 0 as IsKOSDAQ150, t.IsSP500, t.IsNASDAQ100, t.IsDOW30
            FROM early_buy_signals e
            LEFT JOIN us_tickers t ON e.Code = t.Symbol
            WHERE e.Market = ? 
            ORDER BY e.DurationDays DESC
        """
    df = pd.read_sql_query(query, conn, params=(market,))
    conn.close()
    return df.to_dict(orient='records')

def get_cached_stage1(market):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    if market == 'kor':
        query = """
            SELECT s.Code, s.Name, s.Stage, s.EntryDate, s.DurationDays, s.Close, s.UpdatedAt,
                   t.IsKOSPI200, t.IsKOSDAQ150, 0 as IsSP500, 0 as IsNASDAQ100, 0 as IsDOW30
            FROM stage1_signals s
            LEFT JOIN tickers t ON s.Code = t.Code
            WHERE s.Market = ? 
            ORDER BY s.DurationDays ASC
        """
    else:
        query = """
            SELECT s.Code, s.Name, s.Stage, s.EntryDate, s.DurationDays, s.Close, s.UpdatedAt,
                   0 as IsKOSPI200, 0 as IsKOSDAQ150, t.IsSP500, t.IsNASDAQ100, t.IsDOW30
            FROM stage1_signals s
            LEFT JOIN us_tickers t ON s.Code = t.Symbol
            WHERE s.Market = ? 
            ORDER BY s.DurationDays ASC
        """
    df = pd.read_sql_query(query, conn, params=(market,))
    conn.close()
    return df.to_dict(orient='records')

def get_cached_stage4(market):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    if market == 'kor':
        query = """
            SELECT s.Code, s.Name, s.Stage, s.EntryDate, s.DurationDays, s.Close, s.UpdatedAt,
                   t.IsKOSPI200, t.IsKOSDAQ150, 0 as IsSP500, 0 as IsNASDAQ100, 0 as IsDOW30
            FROM stage4_signals s
            LEFT JOIN tickers t ON s.Code = t.Code
            WHERE s.Market = ? 
            ORDER BY s.DurationDays ASC
        """
    else:
        query = """
            SELECT s.Code, s.Name, s.Stage, s.EntryDate, s.DurationDays, s.Close, s.UpdatedAt,
                   0 as IsKOSPI200, 0 as IsKOSDAQ150, t.IsSP500, t.IsNASDAQ100, t.IsDOW30
            FROM stage4_signals s
            LEFT JOIN us_tickers t ON s.Code = t.Symbol
            WHERE s.Market = ? 
            ORDER BY s.DurationDays ASC
        """
    df = pd.read_sql_query(query, conn, params=(market,))
    conn.close()
    return df.to_dict(orient='records')

def get_stage_trends_data(market):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    # Get all sorted by Date
    query = "SELECT Date, Stage1_Count, Stage2_Count, Stage3_Count, Stage4_Count, Stage5_Count, Stage6_Count, Total_Count FROM stage_trends WHERE Market = ? ORDER BY Date ASC"
    df = pd.read_sql_query(query, conn, params=(market,))
    conn.close()
    return df.to_dict(orient='records')

if __name__ == '__main__':
    # Test scan and run backfill
    backfill_stage_trends('kor')
    backfill_stage_trends('us')
    backfill_historical_signals('kor')
    backfill_historical_signals('us')
    scan_market('kor')
    scan_market('us')
