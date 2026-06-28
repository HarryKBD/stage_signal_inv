import sqlite3
import pandas as pd
import numpy as np
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from scanner import get_cached_candidates, get_cached_stage1, get_cached_stage4, get_stage_trends_data, calculate_stages, DB_PATH
import os

app = FastAPI(title="Kojiro Moving Average Grand Cycle Analyzer")
# Trigger uvicorn reload history

# Create templates and static directories if they don't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_portfolio_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            market TEXT NOT NULL,
            buy_date TEXT NOT NULL,
            buy_price REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_portfolio_db()

def calculate_full_indicators(df):
    if df.empty:
        return df
    # Clean column names (mainly mapping index to Date for US stocks)
    if 'Date' not in df.columns:
        if 'index' in df.columns:
            df.rename(columns={'index': 'Date'}, inplace=True)
            
    df = df.sort_values('Date')
    df.set_index('Date', inplace=True)
    df = calculate_stages(df)
    df.reset_index(inplace=True)
    return df

def get_stock_history_data(market: str, code: str, limit: int = None):
    conn = get_db_connection()
    if market == 'kor':
        query = "SELECT Date, Open, High, Low, Close, Volume, Name FROM stock_prices WHERE Code = ? ORDER BY Date"
        if limit:
            # For candidate summary charts, fetch recent data only
            query = f"SELECT * FROM ({query} DESC LIMIT {limit}) ORDER BY Date"
        df = pd.read_sql_query(query, conn, params=(code,))
    else:
        query = "SELECT \"index\" as Date, Open, High, Low, Close, Volume, Name FROM us_stock_prices WHERE Code = ? ORDER BY \"index\""
        if limit:
            query = f"SELECT * FROM ({query} DESC LIMIT {limit}) ORDER BY Date"
        df = pd.read_sql_query(query, conn, params=(code,))
    conn.close()
    
    if df.empty:
        return None
        
    df = calculate_full_indicators(df)
    return df

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    kor_trends = get_stage_trends_data('kor')
    us_trends = get_stage_trends_data('us')
    
    kor_latest = kor_trends[-1] if kor_trends else None
    us_latest = us_trends[-1] if us_trends else None
    
    kor_recent_30 = kor_trends[-30:] if kor_trends else []
    us_recent_30 = us_trends[-30:] if us_trends else []
    
    return templates.TemplateResponse(request=request, name="index.html", context={
        "request": request,
        "kor_latest": kor_latest,
        "us_latest": us_latest,
        "kor_recent_30": kor_recent_30,
        "us_recent_30": us_recent_30
    })

@app.get("/buy_candidates", response_class=HTMLResponse)
async def buy_candidates(
    request: Request, 
    market: str = Query('kor', regex='^(kor|us)$'),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1)
):
    # Fetch cached early buy candidates
    candidates = get_cached_candidates(market)
    
    # Simple pagination
    total_count = len(candidates)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_candidates = candidates[start_idx:end_idx]
    
    # For each paginated candidate, fetch recent 100 days of price history
    # and attach it to the candidate record so the UI can draw summary charts.
    candidates_with_data = []
    for c in paginated_candidates:
        hist_df = get_stock_history_data(market, c['Code'], limit=100)
        if hist_df is not None and not hist_df.empty:
            # Format history for JSON rendering
            history = []
            for _, row in hist_df.iterrows():
                dt_str = row['Date'].strftime('%Y-%m-%d') if isinstance(row['Date'], pd.Timestamp) else str(row['Date'])[:10]
                history.append({
                    'time': dt_str,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                    'ma5': float(row['MA5']) if not pd.isna(row['MA5']) else None,
                    'ma20': float(row['MA20']) if not pd.isna(row['MA20']) else None,
                    'ma40': float(row['MA40']) if not pd.isna(row['MA40']) else None,
                    'macd_s': float(row['MACD_S']) if not pd.isna(row['MACD_S']) else None,
                    'macd_m': float(row['MACD_M']) if not pd.isna(row['MACD_M']) else None,
                    'macd_l': float(row['MACD_L']) if not pd.isna(row['MACD_L']) else None,
                    'stage': int(row['Stage']) if not pd.isna(row['Stage']) else 0
                })
            
            c_copy = dict(c)
            c_copy['history'] = history
            candidates_with_data.append(c_copy)
            
    # Calculate pagination metadata
    total_pages = (total_count + limit - 1) // limit
    
    return templates.TemplateResponse(request=request, name="candidates.html", context={
        "request": request,
        "market": market,
        "candidates": candidates_with_data,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "total_count": total_count,
        "has_prev": page > 1,
        "has_next": page < total_pages
    })

@app.get("/buy_detail", response_class=HTMLResponse)
async def buy_detail(
    request: Request,
    code: str = Query(...),
    market: str = Query('kor', regex='^(kor|us)$')
):
    # Just render the page shell. Page will fetch all data from /api/chart_data using AJAX.
    # We fetch basic stock name to show in the header immediately.
    conn = get_db_connection()
    name = "Unknown"
    if market == 'kor':
        row = conn.execute("SELECT Name FROM tickers WHERE Code = ? UNION SELECT Name FROM stock_prices WHERE Code = ? LIMIT 1", (code, code)).fetchone()
    else:
        row = conn.execute("SELECT Name FROM us_tickers WHERE Symbol = ? UNION SELECT Name FROM us_stock_prices WHERE Code = ? LIMIT 1", (code, code)).fetchone()
    conn.close()
    
    if row:
        name = row['Name']
        
    return templates.TemplateResponse(request=request, name="detail.html", context={
        "request": request,
        "code": code,
        "market": market,
        "name": name
    })

@app.get("/api/chart_data")
async def api_chart_data(
    code: str = Query(...),
    market: str = Query('kor', regex='^(kor|us)$')
):
    df = get_stock_history_data(market, code)
    if df is None or df.empty:
        return JSONResponse(status_code=404, content={"message": "No data found for stock code"})
        
    # Prepare payload
    name = df.iloc[0]['Name']
    
    chart_data = []
    for _, row in df.iterrows():
        dt_str = row['Date'].strftime('%Y-%m-%d') if isinstance(row['Date'], pd.Timestamp) else str(row['Date'])[:10]
        chart_data.append({
            'time': dt_str,
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'volume': int(row['Volume']),
            'ma5': float(row['MA5']) if not pd.isna(row['MA5']) else None,
            'ma20': float(row['MA20']) if not pd.isna(row['MA20']) else None,
            'ma40': float(row['MA40']) if not pd.isna(row['MA40']) else None,
            'macd_s': float(row['MACD_S']) if not pd.isna(row['MACD_S']) else None,
            'macd_m': float(row['MACD_M']) if not pd.isna(row['MACD_M']) else None,
            'macd_l': float(row['MACD_L']) if not pd.isna(row['MACD_L']) else None,
            'stage': int(row['Stage']) if not pd.isna(row['Stage']) else 0
        })
        
    return {
        "code": code,
        "name": name,
        "market": market,
        "data": chart_data
    }

@app.get("/stage1", response_class=HTMLResponse)
async def stage1(
    request: Request, 
    market: str = Query('kor', pattern='^(kor|us)$'),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1)
):
    # Fetch cached stage 1 candidates
    candidates = get_cached_stage1(market)
    
    # Simple pagination
    total_count = len(candidates)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_candidates = candidates[start_idx:end_idx]
    
    # Fetch recent 100 days of price history for chart rendering
    candidates_with_data = []
    for c in paginated_candidates:
        hist_df = get_stock_history_data(market, c['Code'], limit=100)
        if hist_df is not None and not hist_df.empty:
            history = []
            for _, row in hist_df.iterrows():
                dt_str = row['Date'].strftime('%Y-%m-%d') if isinstance(row['Date'], pd.Timestamp) else str(row['Date'])[:10]
                history.append({
                    'time': dt_str,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                    'ma5': float(row['MA5']) if not pd.isna(row['MA5']) else None,
                    'ma20': float(row['MA20']) if not pd.isna(row['MA20']) else None,
                    'ma40': float(row['MA40']) if not pd.isna(row['MA40']) else None,
                    'macd_s': float(row['MACD_S']) if not pd.isna(row['MACD_S']) else None,
                    'macd_m': float(row['MACD_M']) if not pd.isna(row['MACD_M']) else None,
                    'macd_l': float(row['MACD_L']) if not pd.isna(row['MACD_L']) else None,
                    'stage': int(row['Stage']) if not pd.isna(row['Stage']) else 0
                })
            
            c_copy = dict(c)
            c_copy['history'] = history
            candidates_with_data.append(c_copy)
            
    total_pages = (total_count + limit - 1) // limit
    
    return templates.TemplateResponse(request=request, name="stage1.html", context={
        "request": request,
        "market": market,
        "candidates": candidates_with_data,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "total_count": total_count,
        "has_prev": page > 1,
        "has_next": page < total_pages
    })

@app.get("/stage4", response_class=HTMLResponse)
async def stage4(
    request: Request, 
    market: str = Query('kor', pattern='^(kor|us)$'),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1)
):
    # Fetch cached stage 4 candidates
    candidates = get_cached_stage4(market)
    
    # Simple pagination
    total_count = len(candidates)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_candidates = candidates[start_idx:end_idx]
    
    # Fetch recent 100 days of price history for chart rendering
    candidates_with_data = []
    for c in paginated_candidates:
        hist_df = get_stock_history_data(market, c['Code'], limit=100)
        if hist_df is not None and not hist_df.empty:
            history = []
            for _, row in hist_df.iterrows():
                dt_str = row['Date'].strftime('%Y-%m-%d') if isinstance(row['Date'], pd.Timestamp) else str(row['Date'])[:10]
                history.append({
                    'time': dt_str,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                    'ma5': float(row['MA5']) if not pd.isna(row['MA5']) else None,
                    'ma20': float(row['MA20']) if not pd.isna(row['MA20']) else None,
                    'ma40': float(row['MA40']) if not pd.isna(row['MA40']) else None,
                    'macd_s': float(row['MACD_S']) if not pd.isna(row['MACD_S']) else None,
                    'macd_m': float(row['MACD_M']) if not pd.isna(row['MACD_M']) else None,
                    'macd_l': float(row['MACD_L']) if not pd.isna(row['MACD_L']) else None,
                    'stage': int(row['Stage']) if not pd.isna(row['Stage']) else 0
                })
            
            c_copy = dict(c)
            c_copy['history'] = history
            candidates_with_data.append(c_copy)
            
    total_pages = (total_count + limit - 1) // limit
    
    return templates.TemplateResponse(request=request, name="stage4.html", context={
        "request": request,
        "market": market,
        "candidates": candidates_with_data,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "total_count": total_count,
        "has_prev": page > 1,
        "has_next": page < total_pages
    })

@app.get("/stage_trends", response_class=HTMLResponse)
async def stage_trends(
    request: Request,
    market: str = Query('kor', pattern='^(kor|us)$')
):
    return templates.TemplateResponse(request=request, name="stage_trends.html", context={
        "request": request,
        "market": market
    })

@app.get("/api/stage_trends")
async def api_stage_trends(
    market: str = Query('kor', pattern='^(kor|us)$')
):
    trends = get_stage_trends_data(market)
    return {
        "market": market,
        "data": trends
    }

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse(request=request, name="search.html", context={"request": request})

@app.get("/api/search")
async def api_search(q: str = Query("", min_length=1)):
    if not q:
        return []
    
    conn = get_db_connection()
    kor_rows = conn.execute(
        "SELECT Code, Name, Market FROM tickers WHERE Code LIKE ? OR Name LIKE ? LIMIT 10",
        (f"%{q}%", f"%{q}%")
    ).fetchall()
    
    us_rows = conn.execute(
        "SELECT Symbol AS Code, Name, Market FROM us_tickers WHERE Symbol LIKE ? OR Name LIKE ? LIMIT 10",
        (f"%{q}%", f"%{q}%")
    ).fetchall()
    conn.close()
    
    results = []
    for r in kor_rows:
        results.append({
            "code": r["Code"],
            "name": r["Name"],
            "market": "kor"
        })
    for r in us_rows:
        results.append({
            "code": r["Code"],
            "name": r["Name"],
            "market": "us"
        })
    return results

@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio_page(request: Request):
    conn = get_db_connection()
    rows = conn.execute("SELECT id, code, market, buy_date, buy_price FROM portfolio ORDER BY id DESC").fetchall()
    conn.close()
    
    portfolio_items = []
    for r in rows:
        item_id = r["id"]
        code = r["code"]
        market = r["market"]
        buy_date = r["buy_date"]
        buy_price = r["buy_price"]
        
        # Fetch stock name first from tickers metadata
        conn = get_db_connection()
        name = "Unknown"
        is_kospi200 = 0
        is_kosdaq150 = 0
        if market == 'kor':
            meta = conn.execute("SELECT Name, IsKOSPI200, IsKOSDAQ150 FROM tickers WHERE Code = ? LIMIT 1", (code,)).fetchone()
            if meta:
                name = meta["Name"]
                is_kospi200 = meta["IsKOSPI200"]
                is_kosdaq150 = meta["IsKOSDAQ150"]
            else:
                meta_fallback = conn.execute("SELECT Name FROM stock_prices WHERE Code = ? LIMIT 1", (code,)).fetchone()
                if meta_fallback:
                    name = meta_fallback["Name"]
        else:
            meta = conn.execute("SELECT Name FROM us_tickers WHERE Symbol = ? UNION SELECT Name FROM us_stock_prices WHERE Code = ? LIMIT 1", (code, code)).fetchone()
            if meta:
                name = meta["Name"]
        conn.close()
        
        # Fetch historical prices to calculate Stages at buy date vs today
        df = get_stock_history_data(market, code)
        if df is not None and not df.empty:
            # Normalize index name if needed
            if 'Date' not in df.columns and 'index' in df.columns:
                df.rename(columns={'index': 'Date'}, inplace=True)
                
            # Convert date to string for comparison
            df['Date_str'] = df['Date'].astype(str).str[:10]
            
            # 1. Locate the record on or closest before the buy date
            buy_records = df[df['Date_str'] <= buy_date]
            if not buy_records.empty:
                buy_record = buy_records.iloc[-1]
            else:
                buy_record = df.iloc[0] # Fallback to first available record
                
            buy_stage = int(buy_record['Stage']) if not pd.isna(buy_record['Stage']) else 0
            
            # 2. Locate the latest record
            latest_record = df.iloc[-1]
            current_stage = int(latest_record['Stage']) if not pd.isna(latest_record['Stage']) else 0
            current_price = float(latest_record['Close'])
            
            if name == "Unknown" and 'Name' in latest_record:
                name = latest_record['Name']
                
            # 3. Calculate Return
            return_rate = ((current_price - buy_price) / buy_price) * 100
            
            # 4. Determine status
            status = "보유"
            status_class = "status-hold"
            if buy_stage in (5, 6) and current_stage == 1:
                status = "GOOD"
                status_class = "status-good"
            elif buy_stage in (5, 6) and current_stage == 4:
                status = "손절 필요"
                status_class = "status-sell"
                
            portfolio_items.append({
                "id": item_id,
                "code": code,
                "name": name,
                "market": market,
                "buy_date": buy_date,
                "buy_price": buy_price,
                "current_price": current_price,
                "return_rate": return_rate,
                "buy_stage": buy_stage,
                "current_stage": current_stage,
                "status": status,
                "status_class": status_class,
                "is_kospi200": is_kospi200,
                "is_kosdaq150": is_kosdaq150
            })
        else:
            # Fallback if no history is found
            portfolio_items.append({
                "id": item_id,
                "code": code,
                "name": name,
                "market": market,
                "buy_date": buy_date,
                "buy_price": buy_price,
                "current_price": 0,
                "return_rate": 0,
                "buy_stage": 0,
                "current_stage": 0,
                "status": "데이터 없음",
                "status_class": "status-hold",
                "is_kospi200": is_kospi200,
                "is_kosdaq150": is_kosdaq150
            })
            
    return templates.TemplateResponse(request=request, name="portfolio.html", context={
        "request": request,
        "portfolio_items": portfolio_items
    })

@app.post("/api/portfolio/add")
async def api_portfolio_add(
    code: str = Query(...),
    market: str = Query(...),
    buy_date: str = Query(...),
    buy_price: float = Query(...)
):
    code = code.strip()
    market = market.strip().lower()
    buy_date = buy_date.strip()
    
    if market not in ('kor', 'us'):
        return JSONResponse(status_code=400, content={"message": "Invalid market. Choose 'kor' or 'us'."})
        
    # Validate stock code existence in metadata tables
    conn = get_db_connection()
    if market == 'kor':
        exists = conn.execute("SELECT 1 FROM tickers WHERE Code = ? UNION SELECT 1 FROM stock_prices WHERE Code = ? LIMIT 1", (code, code)).fetchone()
    else:
        exists = conn.execute("SELECT 1 FROM us_tickers WHERE Symbol = ? UNION SELECT 1 FROM us_stock_prices WHERE Code = ? LIMIT 1", (code, code)).fetchone()
    conn.close()
    
    if not exists:
        return JSONResponse(status_code=400, content={"message": f"Stock ticker code '{code}' not found in database."})
        
    # Insert record
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO portfolio (code, market, buy_date, buy_price) VALUES (?, ?, ?, ?)",
        (code, market, buy_date, buy_price)
    )
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "종목이 성공적으로 등록되었습니다."}

@app.post("/api/portfolio/delete")
async def api_portfolio_delete(id: int = Query(...)):
    conn = get_db_connection()
    conn.execute("DELETE FROM portfolio WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "삭제 완료"}

def compute_strategy_signals():
    conn = get_db_connection()
    
    # 1. KOSPI 200 ETF (252650)
    df_etf_k200 = pd.read_sql_query("""
        SELECT Date, Close as ETF_Close 
        FROM stock_prices 
        WHERE Code = '252650' AND Date >= '2020-01-01'
        ORDER BY Date ASC
    """, conn)
    df_etf_k200['DateStr'] = df_etf_k200['Date'].str[:10]
    
    # 2. KOSPI 200 signal counts
    df_sig_k200 = pd.read_sql_query("""
        SELECT substr(h.Date, 1, 10) as Date, h.SignalType, COUNT(*) as Count
        FROM historical_signals h
        JOIN tickers t ON h.Code = t.Code
        WHERE t.IsKOSPI200 = 1 AND h.Market = 'kor'
        GROUP BY h.Date, h.SignalType
    """, conn)
    df_sig_pivot_k200 = df_sig_k200.pivot(index='Date', columns='SignalType', values='Count').fillna(0).reset_index()
    df_sig_pivot_k200.rename(columns={'Date': 'DateStr'}, inplace=True)
    
    # Merge
    df_k200 = pd.merge(df_etf_k200, df_sig_pivot_k200, on='DateStr', how='left').fillna(0)
    df_k200 = df_k200.sort_values('DateStr').reset_index(drop=True)
    
    # 3. KOSDAQ 150 ETF (229200)
    df_etf_kq150 = pd.read_sql_query("""
        SELECT Date, Close as ETF_Close 
        FROM stock_prices 
        WHERE Code = '229200' AND Date >= '2020-01-01'
        ORDER BY Date ASC
    """, conn)
    df_etf_kq150['DateStr'] = df_etf_kq150['Date'].str[:10]
    
    # 4. KOSDAQ 150 signal counts
    df_sig_kq150 = pd.read_sql_query("""
        SELECT substr(h.Date, 1, 10) as Date, h.SignalType, COUNT(*) as Count
        FROM historical_signals h
        JOIN tickers t ON h.Code = t.Code
        WHERE t.IsKOSDAQ150 = 1 AND h.Market = 'kor'
        GROUP BY h.Date, h.SignalType
    """, conn)
    df_sig_pivot_kq150 = df_sig_kq150.pivot(index='Date', columns='SignalType', values='Count').fillna(0).reset_index()
    df_sig_pivot_kq150.rename(columns={'Date': 'DateStr'}, inplace=True)
    
    # Merge
    df_kq150 = pd.merge(df_etf_kq150, df_sig_pivot_kq150, on='DateStr', how='left').fillna(0)
    df_kq150 = df_kq150.sort_values('DateStr').reset_index(drop=True)
    
    conn.close()
    
    # Strategy 2: Capitulation Reversal (EB >= 30, S1 <= 50) for KOSPI 200
    pos_k2 = 0
    last_sig_k2 = "CASH"
    sig_date_k2 = "N/A"
    sig_price_k2 = 0.0
    
    # Strategy 3: Net Breadth SMA10 Crossover for KOSPI 200
    df_k200['net_breadth'] = df_k200.get('stage1', 0) - df_k200.get('stage4', 0)
    df_k200['net_sma10'] = df_k200['net_breadth'].rolling(10).mean()
    pos_k3 = 0
    last_sig_k3 = "CASH"
    sig_date_k3 = "N/A"
    sig_price_k3 = 0.0
    
    for i in range(len(df_k200)):
        close = float(df_k200.loc[i, 'ETF_Close'])
        date_str = df_k200.loc[i, 'DateStr']
        eb = df_k200.loc[i, 'early_buy'] if 'early_buy' in df_k200.columns else 0
        s1 = df_k200.loc[i, 'stage1'] if 'stage1' in df_k200.columns else 0
        s4 = df_k200.loc[i, 'stage4'] if 'stage4' in df_k200.columns else 0
        
        # Strat 2
        if pos_k2 == 0:
            if eb >= 30 and s1 <= 50:
                pos_k2 = 1
                last_sig_k2 = "BUY"
                sig_date_k2 = date_str
                sig_price_k2 = close
        else:
            if s4 >= 80 or s1 < 45:
                pos_k2 = 0
                last_sig_k2 = "CASH"
                sig_date_k2 = date_str
                sig_price_k2 = close
                
        # Strat 3
        net = df_k200.loc[i, 'net_breadth']
        sma = df_k200.loc[i, 'net_sma10']
        if not pd.isna(sma):
            prev_net = df_k200.loc[i-1, 'net_breadth'] if i > 0 else 0
            prev_sma = df_k200.loc[i-1, 'net_sma10'] if i > 0 else 0
            
            if pos_k3 == 0:
                if net > sma and prev_net <= prev_sma:
                    pos_k3 = 1
                    last_sig_k3 = "BUY"
                    sig_date_k3 = date_str
                    sig_price_k3 = close
            else:
                if net < sma and prev_net >= prev_sma:
                    pos_k3 = 0
                    last_sig_k3 = "CASH"
                    sig_date_k3 = date_str
                    sig_price_k3 = close

    # Strategy 2: Capitulation Reversal (EB >= 15, S1 <= 35) for KOSDAQ 150
    pos_q2 = 0
    last_sig_q2 = "CASH"
    sig_date_q2 = "N/A"
    sig_price_q2 = 0.0
    
    # Strategy 3: Net Breadth SMA10 Crossover for KOSDAQ 150
    df_kq150['net_breadth'] = df_kq150.get('stage1', 0) - df_kq150.get('stage4', 0)
    df_kq150['net_sma10'] = df_kq150['net_breadth'].rolling(10).mean()
    pos_q3 = 0
    last_sig_q3 = "CASH"
    sig_date_q3 = "N/A"
    sig_price_q3 = 0.0
    
    for i in range(len(df_kq150)):
        close = float(df_kq150.loc[i, 'ETF_Close'])
        date_str = df_kq150.loc[i, 'DateStr']
        eb = df_kq150.loc[i, 'early_buy'] if 'early_buy' in df_kq150.columns else 0
        s1 = df_kq150.loc[i, 'stage1'] if 'stage1' in df_kq150.columns else 0
        s4 = df_kq150.loc[i, 'stage4'] if 'stage4' in df_kq150.columns else 0
        
        # Strat 2
        if pos_q2 == 0:
            if eb >= 15 and s1 <= 35:
                pos_q2 = 1
                last_sig_q2 = "BUY"
                sig_date_q2 = date_str
                sig_price_q2 = close
        else:
            if s1 >= 70 or s4 >= 75:
                pos_q2 = 0
                last_sig_q2 = "CASH"
                sig_date_q2 = date_str
                sig_price_q2 = close
                
        # Strat 3
        net = df_kq150.loc[i, 'net_breadth']
        sma = df_kq150.loc[i, 'net_sma10']
        if not pd.isna(sma):
            prev_net = df_kq150.loc[i-1, 'net_breadth'] if i > 0 else 0
            prev_sma = df_kq150.loc[i-1, 'net_sma10'] if i > 0 else 0
            
            if pos_q3 == 0:
                if net > sma and prev_net <= prev_sma:
                    pos_q3 = 1
                    last_sig_q3 = "BUY"
                    sig_date_q3 = date_str
                    sig_price_q3 = close
            else:
                if net < sma and prev_net >= prev_sma:
                    pos_q3 = 0
                    last_sig_q3 = "CASH"
                    sig_date_q3 = date_str
                    sig_price_q3 = close

    # Format history lists
    history_k200 = []
    df_k200_recent = df_k200.iloc[-10:].copy().iloc[::-1]
    for _, row in df_k200_recent.iterrows():
        history_k200.append({
            'date': str(row['DateStr']),
            'close': float(row['ETF_Close']),
            'early_buy': int(row.get('early_buy', 0)),
            'stage1': int(row.get('stage1', 0)),
            'stage4': int(row.get('stage4', 0)),
            'net_breadth': int(row['net_breadth']),
            'net_sma10': round(float(row['net_sma10']), 1) if not pd.isna(row['net_sma10']) else 0.0
        })
        
    history_kq150 = []
    df_kq150_recent = df_kq150.iloc[-10:].copy().iloc[::-1]
    for _, row in df_kq150_recent.iterrows():
        history_kq150.append({
            'date': str(row['DateStr']),
            'close': float(row['ETF_Close']),
            'early_buy': int(row.get('early_buy', 0)),
            'stage1': int(row.get('stage1', 0)),
            'stage4': int(row.get('stage4', 0)),
            'net_breadth': int(row['net_breadth']),
            'net_sma10': round(float(row['net_sma10']), 1) if not pd.isna(row['net_sma10']) else 0.0
        })
        
    latest_k200 = df_k200.iloc[-1]
    latest_kq150 = df_kq150.iloc[-1]
    
    return {
        'kospi200': {
            'etf_close': float(latest_k200['ETF_Close']),
            'early_buy': int(latest_k200.get('early_buy', 0)),
            'stage1': int(latest_k200.get('stage1', 0)),
            'stage4': int(latest_k200.get('stage4', 0)),
            'net_breadth': int(latest_k200['net_breadth']),
            'strat2': {
                'position': pos_k2,
                'last_signal': last_sig_k2,
                'signal_date': sig_date_k2,
                'signal_price': sig_price_k2
            },
            'strat3': {
                'position': pos_k3,
                'last_signal': last_sig_k3,
                'signal_date': sig_date_k3,
                'signal_price': sig_price_k3
            },
            'history': history_k200
        },
        'kosdaq150': {
            'etf_close': float(latest_kq150['ETF_Close']),
            'early_buy': int(latest_kq150.get('early_buy', 0)),
            'stage1': int(latest_kq150.get('stage1', 0)),
            'stage4': int(latest_kq150.get('stage4', 0)),
            'net_breadth': int(latest_kq150['net_breadth']),
            'strat2': {
                'position': pos_q2,
                'last_signal': last_sig_q2,
                'signal_date': sig_date_q2,
                'signal_price': sig_price_q2
            },
            'strat3': {
                'position': pos_q3,
                'last_signal': last_sig_q3,
                'signal_date': sig_date_q3,
                'signal_price': sig_price_q3
            },
            'history': history_kq150
        }
    }

@app.get("/signals", response_class=HTMLResponse)
async def signals_page(request: Request):
    context = compute_strategy_signals()
    context["request"] = request
    return templates.TemplateResponse(request=request, name="signals.html", context=context)

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    conn = get_db_connection()
    # Fetch dates that have historical signals
    dates_kor = conn.execute("SELECT DISTINCT Date FROM historical_signals WHERE Market = 'kor' ORDER BY Date DESC").fetchall()
    dates_us = conn.execute("SELECT DISTINCT Date FROM historical_signals WHERE Market = 'us' ORDER BY Date DESC").fetchall()
    conn.close()
    
    kor_dates = [d["Date"] for d in dates_kor]
    us_dates = [d["Date"] for d in dates_us]
    
    latest_kor_date = kor_dates[0] if kor_dates else ""
    latest_us_date = us_dates[0] if us_dates else ""
    
    return templates.TemplateResponse(request=request, name="history.html", context={
        "request": request,
        "kor_dates": kor_dates,
        "us_dates": us_dates,
        "latest_kor_date": latest_kor_date,
        "latest_us_date": latest_us_date
    })

@app.get("/api/history")
async def api_history(
    date: str = Query(...),
    market: str = Query('kor', pattern='^(kor|us)$'),
    sub_market: str = Query('ALL', pattern='^(KOSPI|KOSDAQ|KOSPI200|KOSDAQ150|KOSPI200_EQUAL|SP500|NASDAQ100|DOW30|ALL)$')
):
    conn = get_db_connection()
    # 1. Fetch current date signals
    if market == 'kor':
        if sub_market in ('KOSPI', 'KOSDAQ'):
            market_cond = "t.Market = ?"
            cond_params = (date, sub_market)
        elif sub_market in ('KOSPI200', 'KOSPI200_EQUAL'):
            market_cond = "t.IsKOSPI200 = 1"
            cond_params = (date,)
        elif sub_market == 'KOSDAQ150':
            market_cond = "t.IsKOSDAQ150 = 1"
            cond_params = (date,)
        else: # ALL
            market_cond = "1=1"
            cond_params = (date,)
            
        query_curr = f"""
            SELECT h.Code, h.Name, h.SignalType, h.Stage, h.Close, t.IsKOSPI200, t.IsKOSDAQ150,
                   0 as IsSP500, 0 as IsNASDAQ100, 0 as IsDOW30
            FROM historical_signals h
            LEFT JOIN tickers t ON h.Code = t.Code
            WHERE h.Date = ? AND h.Market = 'kor' AND {market_cond}
        """
        curr_rows = conn.execute(query_curr, cond_params).fetchall()
    else:
        if sub_market == 'SP500':
            market_cond = "t.IsSP500 = 1"
        elif sub_market == 'NASDAQ100':
            market_cond = "t.IsNASDAQ100 = 1"
        elif sub_market == 'DOW30':
            market_cond = "t.IsDOW30 = 1"
        else: # ALL
            market_cond = "1=1"
            
        query_curr = f"""
            SELECT h.Code, h.Name, h.SignalType, h.Stage, h.Close, 0 as IsKOSPI200, 0 as IsKOSDAQ150,
                   t.IsSP500, t.IsNASDAQ100, t.IsDOW30
            FROM historical_signals h
            LEFT JOIN us_tickers t ON h.Code = t.Symbol
            WHERE h.Date = ? AND h.Market = 'us' AND {market_cond}
        """
        curr_rows = conn.execute(query_curr, (date,)).fetchall()
    
    # 2. Fetch previous trading date
    prev_date_row = conn.execute(
        "SELECT MAX(Date) as prev_date FROM historical_signals WHERE Date < ? AND Market = ?",
        (date, market)
    ).fetchone()
    
    prev_date = prev_date_row["prev_date"] if prev_date_row else None
    
    prev_rows = []
    if prev_date:
        if market == 'kor':
            if sub_market in ('KOSPI', 'KOSDAQ'):
                market_cond = "t.Market = ?"
                cond_params = (prev_date, sub_market)
            elif sub_market in ('KOSPI200', 'KOSPI200_EQUAL'):
                market_cond = "t.IsKOSPI200 = 1"
                cond_params = (prev_date,)
            elif sub_market == 'KOSDAQ150':
                market_cond = "t.IsKOSDAQ150 = 1"
                cond_params = (prev_date,)
            else: # ALL
                market_cond = "1=1"
                cond_params = (prev_date,)
                
            query_prev = f"""
                SELECT h.Code, h.Name, h.SignalType, h.Stage, h.Close, t.IsKOSPI200, t.IsKOSDAQ150,
                       0 as IsSP500, 0 as IsNASDAQ100, 0 as IsDOW30
                FROM historical_signals h
                LEFT JOIN tickers t ON h.Code = t.Code
                WHERE h.Date = ? AND h.Market = 'kor' AND {market_cond}
            """
            prev_rows = conn.execute(query_prev, cond_params).fetchall()
        else:
            if sub_market == 'SP500':
                market_cond = "t.IsSP500 = 1"
            elif sub_market == 'NASDAQ100':
                market_cond = "t.IsNASDAQ100 = 1"
            elif sub_market == 'DOW30':
                market_cond = "t.IsDOW30 = 1"
            else: # ALL
                market_cond = "1=1"
                
            query_prev = f"""
                SELECT h.Code, h.Name, h.SignalType, h.Stage, h.Close, 0 as IsKOSPI200, 0 as IsKOSDAQ150,
                       t.IsSP500, t.IsNASDAQ100, t.IsDOW30
                FROM historical_signals h
                LEFT JOIN us_tickers t ON h.Code = t.Symbol
                WHERE h.Date = ? AND h.Market = 'us' AND {market_cond}
            """
            prev_rows = conn.execute(query_prev, (prev_date,)).fetchall()
        
    conn.close()
    
    # Helper to segment rows into structured maps
    def segment_signals(rows):
        segs = {'early_buy': {}, 'stage1': {}, 'stage4': {}}
        for r in rows:
            t = r['SignalType']
            if t in segs:
                segs[t][r['Code']] = {
                    'code': r['Code'],
                    'name': r['Name'],
                    'stage': r['Stage'],
                    'close': r['Close'],
                    'is_kospi200': r['IsKOSPI200'] if r['IsKOSPI200'] is not None else 0,
                    'is_kosdaq150': r['IsKOSDAQ150'] if r['IsKOSDAQ150'] is not None else 0,
                    'is_sp500': r['IsSP500'] if ('IsSP500' in r.keys() and r['IsSP500'] is not None) else 0,
                    'is_nasdaq100': r['IsNASDAQ100'] if ('IsNASDAQ100' in r.keys() and r['IsNASDAQ100'] is not None) else 0,
                    'is_dow30': r['IsDOW30'] if ('IsDOW30' in r.keys() and r['IsDOW30'] is not None) else 0
                }
        return segs
        
    curr_segs = segment_signals(curr_rows)
    prev_segs = segment_signals(prev_rows)
    
    result = {
        'date': date,
        'prev_date': prev_date,
        'early_buy': {'in': [], 'out': [], 'hold': []},
        'stage1': {'in': [], 'out': [], 'hold': []},
        'stage4': {'in': [], 'out': [], 'hold': []}
    }
    
    for sig_type in ['early_buy', 'stage1', 'stage4']:
        curr_map = curr_segs[sig_type]
        prev_map = prev_segs[sig_type]
        
        curr_keys = set(curr_map.keys())
        prev_keys = set(prev_map.keys())
        
        in_keys = curr_keys - prev_keys
        out_keys = prev_keys - curr_keys
        hold_keys = curr_keys & prev_keys
        
        result[sig_type]['in'] = [curr_map[k] for k in in_keys]
        result[sig_type]['out'] = [prev_map[k] for k in out_keys]
        result[sig_type]['hold'] = [curr_map[k] for k in hold_keys]
        
    return result

@app.get("/api/history/trends")
async def api_history_trends(
    market: str = Query('kor', pattern='^(kor|us)$'),
    sub_market: str = Query('ALL', pattern='^(KOSPI|KOSDAQ|KOSPI200|KOSDAQ150|KOSPI200_EQUAL|SP500|NASDAQ100|DOW30|ALL)$')
):
    conn = get_db_connection()
    if market == 'kor' and sub_market in ('KOSPI', 'KOSDAQ', 'KOSPI200', 'KOSDAQ150', 'KOSPI200_EQUAL'):
        if sub_market in ('KOSPI', 'KOSDAQ'):
            market_cond = "t.Market = ?"
            cond_params = (sub_market,)
        elif sub_market in ('KOSPI200', 'KOSPI200_EQUAL'):
            market_cond = "t.IsKOSPI200 = 1"
            cond_params = ()
        else: # KOSDAQ150
            market_cond = "t.IsKOSDAQ150 = 1"
            cond_params = ()
            
        query = f"""
            SELECT h.Date, h.SignalType, COUNT(*) as count 
            FROM historical_signals h
            JOIN tickers t ON h.Code = t.Code
            WHERE h.Market = 'kor' AND {market_cond}
            GROUP BY h.Date, h.SignalType 
            ORDER BY h.Date ASC
        """
        rows = conn.execute(query, cond_params).fetchall()
    elif market == 'us' and sub_market in ('SP500', 'NASDAQ100', 'DOW30'):
        if sub_market == 'SP500':
            market_cond = "t.IsSP500 = 1"
        elif sub_market == 'NASDAQ100':
            market_cond = "t.IsNASDAQ100 = 1"
        else: # DOW30
            market_cond = "t.IsDOW30 = 1"
            
        query = f"""
            SELECT h.Date, h.SignalType, COUNT(*) as count 
            FROM historical_signals h
            JOIN us_tickers t ON h.Code = t.Symbol
            WHERE h.Market = 'us' AND {market_cond}
            GROUP BY h.Date, h.SignalType 
            ORDER BY h.Date ASC
        """
        rows = conn.execute(query).fetchall()
    else:
        query = """
            SELECT Date, SignalType, COUNT(*) as count 
            FROM historical_signals 
            WHERE Market = ? 
            GROUP BY Date, SignalType 
            ORDER BY Date ASC
        """
        rows = conn.execute(query, (market,)).fetchall()
    
    dates_set = sorted(list(set(r['Date'] for r in rows)))
    
    # Restrict to last 1500 dates for the trend
    dates_set = dates_set[-1500:]
    dates_filter = set(dates_set)
    
    counts = {d: {
        'early_buy': 0,
        'stage1': 0, 'stage2': 0, 'stage3': 0, 'stage4': 0, 'stage5': 0, 'stage6': 0,
        'total': 0
    } for d in dates_set}
    for r in rows:
        d = r['Date']
        if d not in dates_filter:
            continue
        t = r['SignalType']
        if t in counts[d]:
            counts[d][t] = r['count']
            
    for d in dates_set:
        counts[d]['total'] = sum(counts[d][f'stage{i}'] for i in range(1, 7))
            
    data_by_type = {
        'early_buy': [],
        'stage1': [], 'stage2': [], 'stage3': [], 'stage4': [], 'stage5': [], 'stage6': [],
        'total': []
    }
    
    for d in dates_set:
        for key in data_by_type.keys():
            data_by_type[key].append({'x': d, 'y': counts[d][key]})
        
    series_list = [
        {'name': 'Early Buy', 'type': 'area', 'data': data_by_type['early_buy']},
        {'name': 'Stage 1 (Stable Upward)', 'type': 'area', 'data': data_by_type['stage1']},
        {'name': 'Stage 2 (Upward Slowdown)', 'type': 'area', 'data': data_by_type['stage2']},
        {'name': 'Stage 3 (Early Downward)', 'type': 'area', 'data': data_by_type['stage3']},
        {'name': 'Stage 4 (Stable Downward)', 'type': 'area', 'data': data_by_type['stage4']},
        {'name': 'Stage 5 (Downward Slowdown)', 'type': 'area', 'data': data_by_type['stage5']},
        {'name': 'Stage 6 (Early Upward)', 'type': 'area', 'data': data_by_type['stage6']},
        {'name': 'Total Tickers', 'type': 'line', 'data': data_by_type['total']}
    ]
    
    # Add ETF price series if sub_market is active
    if dates_set:
        is_etf_needed = False
        etf_code = None
        etf_name = None
        prices_table = 'stock_prices'
        
        if market == 'kor' and sub_market in ('KOSPI', 'KOSDAQ', 'KOSPI200', 'KOSDAQ150', 'KOSPI200_EQUAL'):
            is_etf_needed = True
            prices_table = 'stock_prices'
            if sub_market in ('KOSPI', 'KOSPI200'):
                etf_code = '226490'
                etf_name = 'KODEX 코스피 가격'
            elif sub_market == 'KOSPI200_EQUAL':
                etf_code = '252650'
                etf_name = 'KODEX 200동일가중 가격'
            else:
                etf_code = '229200'
                etf_name = 'KODEX 코스닥150 가격'
        elif market == 'us' and sub_market in ('SP500', 'NASDAQ100', 'DOW30'):
            is_etf_needed = True
            prices_table = 'us_stock_prices'
            if sub_market == 'SP500':
                etf_code = 'SPY'
                etf_name = 'SPY ETF 가격'
            elif sub_market == 'NASDAQ100':
                etf_code = 'QQQ'
                etf_name = 'QQQ ETF 가격'
            else:
                etf_code = 'DIA'
                etf_name = 'DIA ETF 가격'
                
        if is_etf_needed:
            min_date_str = dates_set[0]
            if prices_table == 'stock_prices':
                etf_rows = conn.execute("""
                    SELECT Date, Close 
                    FROM stock_prices 
                    WHERE Code = ? AND Date >= ? 
                    ORDER BY Date ASC
                """, (etf_code, min_date_str + " 00:00:00")).fetchall()
            else:
                # us_stock_prices table uses "index" for Date
                etf_rows = conn.execute("""
                    SELECT "index" as Date, Close 
                    FROM us_stock_prices 
                    WHERE Code = ? AND "index" >= ? 
                    ORDER BY "index" ASC
                """, (etf_code, min_date_str + " 00:00:00")).fetchall()
                
            # Map date strings to float closes
            etf_map = {}
            for r in etf_rows:
                d_str = r['Date'][:10]
                etf_map[d_str] = float(r['Close'])
                
            # Build aligned data series (forward-fill missing dates)
            etf_data = []
            last_val = None
            for d in dates_set:
                val = etf_map.get(d)
                if val is not None:
                    last_val = val
                elif last_val is None:
                    last_val = 0.0
                etf_data.append({'x': d, 'y': last_val})
                
            series_list.append({
                'name': etf_name,
                'type': 'line',
                'data': etf_data
            })
            
    conn.close()
    
    return {
        'market': market,
        'sub_market': sub_market,
        'series': series_list
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main.py:app", host="0.0.0.0", port=8000, reload=True)
