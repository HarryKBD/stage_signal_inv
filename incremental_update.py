import FinanceDataReader as fdr
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import argparse
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 글로벌 네트워크 소켓 타임아웃 설정 (FinanceDataReader의 무한 대기 방지)
socket.setdefaulttimeout(15.0)

def fetch_with_timeout(code, start_date, end_date, timeout=8.0):
    """
    FinanceDataReader.DataReader를 별도 데몬 스레드에서 실행하고 timeout 시간 내에 완료되지 않으면 포기함.
    특정 종목 조회 시 발생하는 라이브러리 내부 무한 루프 또는 데드락으로 인한 전체 행(hang) 현상을 완벽히 방어.
    """
    result = [None]
    exception = [None]
    
    def worker():
        try:
            result[0] = fdr.DataReader(code, start_date, end_date)
        except Exception as e:
            exception[0] = e
            
    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()
    t.join(timeout)
    
    if t.is_alive():
        print(f"\n[WARNING] DataReader for {code} timed out after {timeout}s. Skipping.", flush=True)
        return None
        
    if exception[0] is not None:
        raise exception[0]
        
    return result[0]

def fetch_stock_data(code, name, market, start_date, end_date, market_type):
    try:
        # 타임아웃 8초 제한 적용하여 데이터 로드
        df = fetch_with_timeout(code, start_date, end_date, timeout=8.0)
        if df is not None and not df.empty:
            df['Code'] = code
            df['Name'] = name
            df['Market'] = market
            df = df.reset_index()
            
            if market_type == 'US':
                df = df.rename(columns={'Date': 'index'})
            return df
        return None
    except Exception:
        return None

def incremental_update(market_type='US', max_workers=20):
    db_path = 'stock_data.db'
    
    # SQLite 락 방지를 위한 타임아웃 설정이 추가된 연결
    conn = sqlite3.connect(db_path, timeout=30.0)
    
    if market_type == 'KR':
        tickers_table = 'tickers'
        prices_table = 'stock_prices'
        date_col = 'Date'
        code_col = 'Code'
    else:
        tickers_table = 'us_tickers'
        prices_table = 'us_stock_prices'
        date_col = '"index"'
        code_col = 'Code'
    
    print(f"\nStarting incremental update for {market_type} stocks...")
    
    try:
        tickers_df = pd.read_sql(f"SELECT * FROM {tickers_table}", conn)
    except Exception as e:
        print(f"Error reading tickers table: {e}")
        conn.close()
        return

    print(f"Fetching current max dates from {prices_table}...")
    try:
        max_dates_query = f"SELECT {code_col}, MAX({date_col}) as last_date FROM {prices_table} GROUP BY {code_col}"
        max_dates = pd.read_sql(max_dates_query, conn)
        max_date_dict = dict(zip(max_dates[code_col], max_dates['last_date']))
    except Exception as e:
        print(f"Prices table might not exist or is empty: {e}")
        max_date_dict = {}
    
    conn.close()

    # Target end_date should be today, but on weekends we treat Friday as the target.
    now = datetime.now()
    if now.weekday() == 5:  # Saturday
        end_date_dt = now - timedelta(days=1)
    elif now.weekday() == 6:  # Sunday
        end_date_dt = now - timedelta(days=2)
    else:
        end_date_dt = now
    end_date = end_date_dt.strftime('%Y-%m-%d')
    
    # Fast Bulk Update Optimization for KR Market
    if market_type == 'KR':
        anchor_code = '005930'  # Samsung Electronics
        last_date_str = max_date_dict.get(anchor_code)
        if last_date_str:
            last_date = datetime.strptime(last_date_str[:10], '%Y-%m-%d')
            # Get missing business days (Mon-Fri)
            date_range = pd.date_range(start=last_date + timedelta(days=1), end=datetime.now(), freq='B')
            dates_to_update = [d.strftime('%Y-%m-%d') for d in date_range if d.strftime('%Y-%m-%d') <= end_date]
            
            if 1 <= len(dates_to_update) <= 10:
                print(f"Detecting small gap ({len(dates_to_update)} business days). Attempting fast bulk date-wise update...")
                try:
                    from pykrx import stock as pykrx_stock
                    bulk_conn = sqlite3.connect(db_path, timeout=30.0)
                    
                    for date_str in dates_to_update:
                        date_pykrx = date_str.replace('-', '')
                        print(f"Fetching all stock prices for date {date_str} in bulk...")
                        
                        # Fetch all tickers for this date
                        df_bulk = pykrx_stock.get_market_ohlcv_by_ticker(date_pykrx, market="ALL")
                        if df_bulk.empty:
                            print(f"No trading data returned for {date_str} (possible holiday). Skipping.")
                            continue
                            
                        # Format dataframe
                        df_bulk = df_bulk.reset_index()
                        df_bulk = df_bulk.rename(columns={
                            '티커': 'Code',
                            '시가': 'Open',
                            '고가': 'High',
                            '저가': 'Low',
                            '종가': 'Close',
                            '거래량': 'Volume'
                        })
                        
                        # Keep only necessary columns and join with tickers metadata
                        df_bulk = df_bulk[['Code', 'Open', 'High', 'Low', 'Close', 'Volume']]
                        
                        # Merge with tickers_df to get Name and Market
                        df_merged = pd.merge(df_bulk, tickers_df[['Code', 'Name', 'Market']], on='Code', how='inner')
                        df_merged['Date'] = f"{date_str} 00:00:00"
                        
                        # Rearrange columns to match database schema exactly
                        db_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Code', 'Name', 'Market']
                        df_merged = df_merged[db_columns]
                        
                        # Write to database
                        df_merged.to_sql(prices_table, bulk_conn, if_exists='append', index=False)
                        print(f"Successfully saved {len(df_merged)} stock prices for {date_str} in bulk.")
                        
                    bulk_conn.commit()
                    bulk_conn.close()
                    print("Fast bulk update completed successfully!")
                    return
                except Exception as e:
                    print(f"Fast bulk update failed: {e}. Falling back to individual thread-pool update...")
                    if 'bulk_conn' in locals():
                        try:
                            bulk_conn.close()
                        except:
                            pass
                            
    tasks = []
    for row in tickers_df.itertuples():
        code = getattr(row, 'Code', getattr(row, 'Symbol', None))
        if not code: continue
        name = getattr(row, 'Name', 'Unknown')
        market = getattr(row, 'Market', 'Unknown')
        
        last_date_str = max_date_dict.get(code)
        if last_date_str:
            last_date = datetime.strptime(last_date_str[:10], '%Y-%m-%d')
            start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            start_date = '2000-01-01'
            
        if start_date <= end_date:
            tasks.append((code, name, market, start_date, end_date))

    print(f"Tickers needing update: {len(tasks)}")
    
    if not tasks:
        print(f"All {market_type} stocks are up to date.")
        return

    updated_count = 0
    error_count = 0
    batch_dfs = []
    batch_size = 100  # 100개 종목 단위로 묶어서 벌크 저장하여 SQLite 쓰기 락 경쟁 및 I/O 횟수 대폭 감소
    
    print(f"Updating using {max_workers} thread workers...", flush=True)
    
    def save_batch(dfs):
        if not dfs: return
        merged_df = pd.concat(dfs, ignore_index=True)
        # SQLite 쓰기 시에도 30초 락 대기 타임아웃 부여
        batch_conn = sqlite3.connect(db_path, timeout=30.0)
        try:
            merged_df.to_sql(prices_table, batch_conn, if_exists='append', index=False)
            batch_conn.commit()
        except Exception as e:
            print(f"\nError writing batch to database: {e}", flush=True)
        finally:
            batch_conn.close()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_code = {
            executor.submit(fetch_stock_data, t[0], t[1], t[2], t[3], t[4], market_type): t[0] 
            for t in tasks
        }
        
        for i, future in enumerate(as_completed(future_to_code)):
            df_result = future.result()
            if df_result is not None:
                batch_dfs.append(df_result)
                updated_count += 1
            else:
                error_count += 1
                
            # 주기적 벌크 쓰기 실행
            if len(batch_dfs) >= batch_size:
                save_batch(batch_dfs)
                batch_dfs = []
                
            if (i + 1) % 50 == 0 or (i + 1) == len(tasks):
                print(f"Progress: {i + 1}/{len(tasks)} (Fetched: {updated_count}, NoData/Skip: {error_count})", flush=True)
                
        # 남은 잔여 데이터 최종 벌크 저장
        if batch_dfs:
            save_batch(batch_dfs)
            
    print(f"{market_type} Update complete. Total Fetched & Saved: {updated_count}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Kojiro Moving Average Grand Cycle - Incremental Update Script")
    parser.add_argument('--market', type=str, choices=['KR', 'US', 'BOTH'], default='BOTH',
                        help="Market to update: KR (Korea), US (USA), or BOTH (default)")
    parser.add_argument('--workers', type=int, default=20,
                        help="Number of concurrent thread workers (default: 20)")
    parser.add_argument('--skip-scan', action='store_true',
                        help="Skip automatic scanner update after price fetch")
    args = parser.parse_args()
    
    # 1. Update prices
    if args.market in ('US', 'BOTH'):
        incremental_update('US', max_workers=args.workers)
    if args.market in ('KR', 'BOTH'):
        incremental_update('KR', max_workers=args.workers)
        
    # 2. Automatically run scanner unless explicitly skipped
    if not args.skip_scan:
        print("\n[AUTO] Starting scanner update to refresh buy candidates and trends...")
        try:
            import scanner
            if args.market in ('KR', 'BOTH'):
                print("[AUTO] Running scanner for KOR market...")
                scanner.scan_market('kor')
            if args.market in ('US', 'BOTH'):
                print("[AUTO] Running scanner for US market...")
                scanner.scan_market('us')
            print("[AUTO] Scanner update completed successfully.")
        except Exception as e:
            print(f"[AUTO] [ERROR] Failed to run scanner: {e}")

