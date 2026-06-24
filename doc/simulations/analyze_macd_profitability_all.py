import sqlite3
import pandas as pd
import numpy as np
import os

DB_PATH = "/Users/keybd/work/mov_invest/stock_data.db"
OUTPUT_PATH = "/Users/keybd/.gemini/antigravity/brain/6b66a3bf-a886-42ce-ad0e-a6da780184a6/analysis_results.md"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_indicators(df):
    df = df.sort_values('Date').copy()
    # SMAs
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA40'] = df['Close'].rolling(window=40).mean()
    
    # EMAs for MACD
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
    
    # MACD rising: S, M, L all rising compared to previous day
    df['MACD_S_rising'] = df['MACD_S'] > df['MACD_S'].shift(1)
    df['MACD_M_rising'] = df['MACD_M'] > df['MACD_M'].shift(1)
    df['MACD_L_rising'] = df['MACD_L'] > df['MACD_L'].shift(1)
    df['MACD_Signal'] = (df['Stage'].isin([5, 6])) & df['MACD_S_rising'] & df['MACD_M_rising'] & df['MACD_L_rising']
    
    # Find "First" signal day of a consecutive run
    df['Prev_Signal'] = df['MACD_Signal'].shift(1).fillna(False)
    df['New_Signal'] = df['MACD_Signal'] & (~df['Prev_Signal'])
    
    return df

def analyze_profitability(df):
    df_reset = df.reset_index(drop=True)
    signal_indices = df_reset[df_reset['New_Signal'] == True].index
    
    trades = []
    
    for idx in signal_indices:
        buy_price = float(df_reset.loc[idx, 'Close'])
        buy_date = df_reset.loc[idx, 'Date']
        
        future_df = df_reset.iloc[idx + 1:]
        
        has_hit_stage1 = False
        outcome = None
        sell_price = None
        sell_date = None
        
        for f_idx, row in future_df.iterrows():
            stage = int(row['Stage'])
            
            if not has_hit_stage1:
                if stage == 1:
                    has_hit_stage1 = True
                elif stage == 4:
                    outcome = 'loss'
                    sell_price = float(row['Close'])
                    sell_date = row['Date']
                    break
            else:
                if stage == 3:
                    outcome = 'win'
                    sell_price = float(row['Close'])
                    sell_date = row['Date']
                    break
                    
        if outcome is not None:
            return_pct = ((sell_price - buy_price) / buy_price) * 100
            trades.append({
                'buy_date': buy_date,
                'buy_price': buy_price,
                'sell_date': sell_date,
                'sell_price': sell_price,
                'outcome': outcome,
                'return_pct': return_pct
            })
            
    return trades

def filter_valid_us_tickers(conn, limit, offset):
    valid_tickers = []
    current_offset = offset
    
    candidates = conn.execute(
        f"SELECT Symbol, Name FROM us_tickers LIMIT 250 OFFSET {current_offset}"
    ).fetchall()
    
    for c in candidates:
        symbol = c['Symbol']
        name = c['Name']
        
        lower_name = name.lower()
        if any(word in lower_name for word in ['pref', 'preferred', 'dep shs', 'mandatory', 'debshs', 'conv prf', 'note', 'index', 'etn', 'fund', 'shs repstg']):
            continue
            
        if '.' in symbol or '-' in symbol:
            continue
            
        exists = conn.execute("SELECT 1 FROM us_stock_prices WHERE Code = ? LIMIT 1", (symbol,)).fetchone()
        if not exists:
            continue
            
        valid_tickers.append({'Code': symbol, 'Name': name})
        if len(valid_tickers) == limit:
            break
            
    return valid_tickers

def run_analysis():
    conn = get_db_connection()
    
    # -------------------------------------------------------------
    # 1. KOR TICKERS SELECTION
    # -------------------------------------------------------------
    kor_large = conn.execute("SELECT Code, Name, Marcap FROM tickers ORDER BY Marcap DESC LIMIT 30").fetchall()
    kor_mid = conn.execute("SELECT Code, Name, Marcap FROM tickers ORDER BY Marcap DESC LIMIT 30 OFFSET 100").fetchall()
    kor_small = conn.execute("SELECT Code, Name, Marcap FROM tickers ORDER BY Marcap DESC LIMIT 30 OFFSET 600").fetchall()
    
    kor_groups = {
        '대형주': kor_large,
        '중형주': kor_mid,
        '소형주': kor_small
    }
    
    kor_results = {}
    
    for group_name, tickers in kor_groups.items():
        print(f"Analyzing KOR {group_name}...")
        group_results = []
        for t in tickers:
            code = t['Code']
            name = t['Name']
            
            price_rows = conn.execute(
                "SELECT Date, Close FROM stock_prices WHERE Code = ? ORDER BY Date", (code,)
            ).fetchall()
            
            if len(price_rows) < 50:
                continue
                
            df = pd.DataFrame(price_rows, columns=['Date', 'Close'])
            df['Close'] = df['Close'].astype(float)
            
            df = calculate_indicators(df)
            trades = analyze_profitability(df)
            
            total_trades = len(trades)
            win_trades = [tr for tr in trades if tr['outcome'] == 'win']
            loss_trades = [tr for tr in trades if tr['outcome'] == 'loss']
            
            win_count = len(win_trades)
            loss_count = len(loss_trades)
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
            
            # Simple Cumulative Return (Sum of returns)
            cum_simple = sum(tr['return_pct'] for tr in trades) if total_trades > 0 else 0.0
            
            # Compound Cumulative Return (Product of 1 + r/100)
            cum_compound = 1.0
            for tr in trades:
                # Limit the max loss factor to prevent total asset drop below zero in theory
                factor = max(0.01, 1.0 + (tr['return_pct'] / 100.0))
                cum_compound *= factor
            cum_compound_pct = (cum_compound - 1.0) * 100.0 if total_trades > 0 else 0.0
            
            avg_return = np.mean([tr['return_pct'] for tr in trades]) if total_trades > 0 else 0.0
            avg_win_return = np.mean([tr['return_pct'] for tr in win_trades]) if win_count > 0 else 0.0
            avg_loss_return = np.mean([tr['return_pct'] for tr in loss_trades]) if loss_count > 0 else 0.0
            
            group_results.append({
                'code': code,
                'name': name,
                'marcap': t['Marcap'],
                'total_days': len(df),
                'total_trades': total_trades,
                'win_count': win_count,
                'loss_count': loss_count,
                'win_rate': win_rate,
                'avg_return': avg_return,
                'avg_win_return': avg_win_return,
                'avg_loss_return': avg_loss_return,
                'cum_simple': cum_simple,
                'cum_compound': cum_compound_pct,
                'trades': trades
            })
        kor_results[group_name] = group_results

    # -------------------------------------------------------------
    # 2. USA TICKERS SELECTION & FILTERING
    # -------------------------------------------------------------
    print("Selecting valid US tickers...")
    us_large = filter_valid_us_tickers(conn, 30, 0)
    us_mid = filter_valid_us_tickers(conn, 30, 300)
    us_small = filter_valid_us_tickers(conn, 30, 1500)
    
    us_groups = {
        '대형주 (Mega-Cap)': us_large,
        '중형주 (Mid-Cap)': us_mid,
        '소형주 (Small-Cap)': us_small
    }
    
    us_results = {}
    
    for group_name, tickers in us_groups.items():
        print(f"Analyzing US {group_name}...")
        group_results = []
        for t in tickers:
            code = t['Code']
            name = t['Name']
            
            price_rows = conn.execute(
                "SELECT \"index\" as Date, Close FROM us_stock_prices WHERE Code = ? ORDER BY \"index\"", (code,)
            ).fetchall()
            
            if len(price_rows) < 50:
                continue
                
            df = pd.DataFrame(price_rows, columns=['Date', 'Close'])
            df['Close'] = df['Close'].astype(float)
            
            df = calculate_indicators(df)
            trades = analyze_profitability(df)
            
            total_trades = len(trades)
            win_trades = [tr for tr in trades if tr['outcome'] == 'win']
            loss_trades = [tr for tr in trades if tr['outcome'] == 'loss']
            
            win_count = len(win_trades)
            loss_count = len(loss_trades)
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
            
            cum_simple = sum(tr['return_pct'] for tr in trades) if total_trades > 0 else 0.0
            
            cum_compound = 1.0
            for tr in trades:
                factor = max(0.01, 1.0 + (tr['return_pct'] / 100.0))
                cum_compound *= factor
            cum_compound_pct = (cum_compound - 1.0) * 100.0 if total_trades > 0 else 0.0
            
            avg_return = np.mean([tr['return_pct'] for tr in trades]) if total_trades > 0 else 0.0
            avg_win_return = np.mean([tr['return_pct'] for tr in win_trades]) if win_count > 0 else 0.0
            avg_loss_return = np.mean([tr['return_pct'] for tr in loss_trades]) if loss_count > 0 else 0.0
            
            group_results.append({
                'code': code,
                'name': name,
                'marcap': 0,
                'total_days': len(df),
                'total_trades': total_trades,
                'win_count': win_count,
                'loss_count': loss_count,
                'win_rate': win_rate,
                'avg_return': avg_return,
                'avg_win_return': avg_win_return,
                'avg_loss_return': avg_loss_return,
                'cum_simple': cum_simple,
                'cum_compound': cum_compound_pct,
                'trades': trades
            })
        us_results[group_name] = group_results
        
    conn.close()
    
    # -------------------------------------------------------------
    # 3. WRITE MARKDOWN REPORT FOR BOTH MARKETS
    # -------------------------------------------------------------
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write("# MACD 시그널 수익률 백테스팅 보고서 (한국 & 미국 시장 통합)\n\n")
        f.write("본 보고서는 **Stage 5 또는 Stage 6(하락세 둔화/상승전환 초기)** 국면에서 **MACD 단기/중기/장기선이 모두 전일 대비 동시 우상향(Rising)**하는 매수 시그널이 발생했을 때, 투자 전략 시나리오에 따른 백테스팅 수익률을 **한국(KOR) 및 미국(USA) 시장**의 대형주, 중형주, 소형주 그룹별로 정밀 분석한 결과입니다. 이번 업데이트에서는 각 종목별 **누적 단리 및 복리 수익률**이 통합 반영되었습니다.\n\n")
        
        f.write("## 1. 백테스팅 매매 시나리오 정의\n")
        f.write("- **스캔 범위**: 각 종목별 전체 상장 데이터 (KOR 평균 2,700일, USA 평균 6,650일 전수 스캔)\n")
        f.write("- **매수 기준**: `Stage in [5, 6]` 이고 동시에 `MACD_S, M, L` 지표가 모두 전일 대비 우상향하는 최초 거래일의 **종가(Close)**로 매수합니다.\n")
        f.write("- **매도 기준 (청산)**:\n")
        f.write("  1. **실패 청산 (손절)**: 시그널 발생 후 Stage 1에 도달하기 전에 **Stage 4(역배열 하락 국면)**를 먼저 만나면, 해당 Stage 4 진입 당일 **종가(Close)**로 즉시 전량 매도(손절)합니다.\n")
        f.write("  2. **성공 청산 (익절)**: 시그널 발생 후 Stage 1에 먼저 도달했다면 매도를 보류하고, 그 이후 최초로 **Stage 3(하락전환 초기 국면)**으로 미끄러질 때 해당 Stage 3 진입 당일 **종가(Close)**로 전량 매도(익절)합니다.\n")
        f.write("  3. **진행 중 거래**: 아직 Stage 3이나 Stage 4 중 어느 곳에도 도달하지 않은 채 데이터가 종료되면 미결정 처리하여 수익률 통계에서 제외합니다.\n")
        f.write("- **누적 수익률 정의**:\n")
        f.write("  - **누적 단리 수익률**: 해당 종목에서 일어난 모든 청산 거래의 수익률을 단순히 합산한 값 ($\\sum r_i$)\n")
        f.write("  - **누적 복리 수익률**: 100% 자금으로 매 거래마다 청산 시 자금을 전액 재투자하여 복리로 곱해갔을 때 최종 누적 수익률 ($[\\prod (1 + r_i/100) - 1] \\times 100\\%$)\n\n")
        
        # ------------------- KOR SUMMARY -------------------
        f.write("## 2. [KOR] 한국 시장 백테스팅 요약\n\n")
        f.write("| 그룹명 | 분석 종목수 | 총 청산 거래수 | 승률 (Win Rate) | **평균 수익률 (전체)** | 익절 평균 | 손절 평균 | **평균 누적 단리** | **평균 누적 복리** |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        
        for group_name, res_list in kor_results.items():
            total_trades = sum(r['total_trades'] for r in res_list)
            total_win = sum(r['win_count'] for r in res_list)
            total_loss = sum(r['loss_count'] for r in res_list)
            win_rate = (total_win / total_trades * 100) if total_trades > 0 else 0.0
            
            all_returns = [tr['return_pct'] for r in res_list for tr in r['trades']]
            win_returns = [tr['return_pct'] for r in res_list for tr in r['trades'] if tr['outcome'] == 'win']
            loss_returns = [tr['return_pct'] for r in res_list for tr in r['trades'] if tr['outcome'] == 'loss']
            
            avg_ret = np.mean(all_returns) if all_returns else 0.0
            avg_win = np.mean(win_returns) if win_returns else 0.0
            avg_loss = np.mean(loss_returns) if loss_returns else 0.0
            
            avg_cum_simple = np.mean([r['cum_simple'] for r in res_list])
            avg_cum_compound = np.mean([r['cum_compound'] for r in res_list])
            
            f.write(f"| **{group_name}** | {len(res_list)}개 | {total_trades:,}회 | {win_rate:.2f}% | **{avg_ret:+.2f}%** | {avg_win:+.2f}% | {avg_loss:+.2f}% | **{avg_cum_simple:+.1f}%** | **{avg_cum_compound:+.1f}%** |\n")
            
        # ------------------- USA SUMMARY -------------------
        f.write("\n## 3. [USA] 미국 시장 백테스팅 요약\n\n")
        f.write("| 그룹명 | 분석 종목수 | 총 청산 거래수 | 승률 (Win Rate) | **평균 수익률 (전체)** | 익절 평균 | 손절 평균 | **평균 누적 단리** | **평균 누적 복리** |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        
        for group_name, res_list in us_results.items():
            total_trades = sum(r['total_trades'] for r in res_list)
            total_win = sum(r['win_count'] for r in res_list)
            total_loss = sum(r['loss_count'] for r in res_list)
            win_rate = (total_win / total_trades * 100) if total_trades > 0 else 0.0
            
            all_returns = [tr['return_pct'] for r in res_list for tr in r['trades']]
            win_returns = [tr['return_pct'] for r in res_list for tr in r['trades'] if tr['outcome'] == 'win']
            loss_returns = [tr['return_pct'] for r in res_list for tr in r['trades'] if tr['outcome'] == 'loss']
            
            avg_ret = np.mean(all_returns) if all_returns else 0.0
            avg_win = np.mean(win_returns) if win_returns else 0.0
            avg_loss = np.mean(loss_returns) if loss_returns else 0.0
            
            avg_cum_simple = np.mean([r['cum_simple'] for r in res_list])
            avg_cum_compound = np.mean([r['cum_compound'] for r in res_list])
            
            f.write(f"| **{group_name}** | {len(res_list)}개 | {total_trades:,}회 | {win_rate:.2f}% | **{avg_ret:+.2f}%** | {avg_win:+.2f}% | {avg_loss:+.2f}% | **{avg_cum_simple:+.1f}%** | **{avg_cum_compound:+.1f}%** |\n")
            
        f.write("\n> [!NOTE]\n")
        f.write("> **평균 누적 단리/복리**는 종목별로 약 10~26년간 모든 시그널 거래를 수행했을 때 종목당 얻게 되는 평균적인 최종 누적 성과를 의미합니다. 복리의 마법 혹은 손실 누적으로 인한 파산 위험을 직관적으로 확인할 수 있습니다.\n\n")

        # ------------------- KOR DETAILED -------------------
        f.write("## 4. [KOR] 한국 시장 종목별 세부 데이터\n\n")
        for group_name, res_list in kor_results.items():
            f.write(f"### 4) KOR {group_name} 종목별 세부 수익률\n\n")
            f.write("| 종목명 (코드) | 총 거래 | 승률 | 평균 수익률 | **누적 단리** | **누적 복리** | 익절 평균 | 손절 평균 | 스캔 일수 |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
            
            sorted_res = sorted(res_list, key=lambda x: x['cum_compound'], reverse=True)
            for r in sorted_res:
                win_rate_str = f"{r['win_rate']:.1f}%" if r['total_trades'] > 0 else "-"
                avg_ret_str = f"{r['avg_return']:+.2f}%" if r['total_trades'] > 0 else "-"
                cum_simple_str = f"**{r['cum_simple']:+.1f}%**" if r['total_trades'] > 0 else "-"
                cum_compound_str = f"**{r['cum_compound']:+.1f}%**" if r['total_trades'] > 0 else "-"
                avg_win_str = f"{r['avg_win_return']:+.2f}%" if r['win_count'] > 0 else "-"
                avg_loss_str = f"{r['avg_loss_return']:+.2f}%" if r['loss_count'] > 0 else "-"
                f.write(f"| {r['name']} ({r['code']}) | {r['total_trades']}회 | {win_rate_str} | {avg_ret_str} | {cum_simple_str} | {cum_compound_str} | {avg_win_str} | {avg_loss_str} | {r['total_days']:,}일 |\n")
            f.write("\n")
            
        # ------------------- USA DETAILED -------------------
        f.write("## 5. [USA] 미국 시장 종목별 세부 데이터\n\n")
        for group_name, res_list in us_results.items():
            f.write(f"### 5) USA {group_name} 종목별 세부 수익률\n\n")
            f.write("| 종목명 (Symbol) | 총 거래 | 승률 | 평균 수익률 | **누적 단리** | **누적 복리** | 익절 평균 | 손절 평균 | 스캔 일수 |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
            
            sorted_res = sorted(res_list, key=lambda x: x['cum_compound'], reverse=True)
            for r in sorted_res:
                win_rate_str = f"{r['win_rate']:.1f}%" if r['total_trades'] > 0 else "-"
                avg_ret_str = f"{r['avg_return']:+.2f}%" if r['total_trades'] > 0 else "-"
                cum_simple_str = f"**{r['cum_simple']:+.1f}%**" if r['total_trades'] > 0 else "-"
                cum_compound_str = f"**{r['cum_compound']:+.1f}%**" if r['total_trades'] > 0 else "-"
                avg_win_str = f"{r['avg_win_return']:+.2f}%" if r['win_count'] > 0 else "-"
                avg_loss_str = f"{r['avg_loss_return']:+.2f}%" if r['loss_count'] > 0 else "-"
                f.write(f"| {r['name']} ({r['code']}) | {r['total_trades']}회 | {win_rate_str} | {avg_ret_str} | {cum_simple_str} | {cum_compound_str} | {avg_win_str} | {avg_loss_str} | {r['total_days']:,}일 |\n")
            f.write("\n")
            
    print("Analysis finished successfully. Report updated with cumulative returns at:", OUTPUT_PATH)

if __name__ == "__main__":
    run_analysis()
