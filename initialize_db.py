import sqlite3
import pandas as pd
import FinanceDataReader as fdr
import json
import os

DB_PATH = 'stock_data.db'
JSON_PATH = 'index_constituents.json'

def ensure_constituents(df_kor):
    import requests
    import re
    import time
    
    krx_id = os.environ.get('KRX_ID')
    krx_pw = os.environ.get('KRX_PW')
    
    kospi200 = []
    kosdaq150 = []
    
    if krx_id and krx_pw:
        try:
            print("KRX Credentials found in environment. Fetching constituents using pykrx...")
            from pykrx import stock
            kospi200 = stock.get_index_portfolio_deposit_file('1028')
            kosdaq150 = stock.get_index_portfolio_deposit_file('2203')
            print(f"Successfully fetched {len(kospi200)} KOSPI 200 and {len(kosdaq150)} KOSDAQ 150 codes via pykrx.")
        except Exception as e:
            print(f"Error fetching via pykrx: {e}. Falling back to scraping...")
            kospi200 = []
            kosdaq150 = []
            
    if not kospi200 or not kosdaq150:
        print("Fetching constituents via web scraping fallback...")
        if not kospi200:
            try:
                from bs4 import BeautifulSoup
                for page in range(1, 21):
                    url = f"https://finance.naver.com/sise/entryJongmok.naver?&page={page}"
                    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                    soup = BeautifulSoup(r.text, 'html.parser')
                    for item in soup.find_all('td', class_='ctg'):
                        code = item.a['href'].split('code=')[1]
                        kospi200.append(code)
                    time.sleep(0.05)
                kospi200 = list(set(kospi200))
                print(f"Scraped {len(kospi200)} KOSPI 200 codes from Naver.")
            except Exception as e:
                print(f"Error scraping KOSPI 200: {e}")
                
        if not kosdaq150:
            try:
                from bs4 import BeautifulSoup
                url = 'https://navercomp.wisereport.co.kr/v2/ETF/index.aspx?cmp_cd=229200'
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                m = re.search(r'var CU_data = (\{.*?\});', r.text)
                if m:
                    grid_data = json.loads(m.group(1))['grid_data']
                    names = [item['STK_NM_KOR'] for item in grid_data if item['STK_NM_KOR'] != '원화현금']
                    
                    clean_df = df_kor.copy()
                    clean_df['CleanName'] = clean_df['Name'].str.replace(' ', '')
                    name_map = dict(zip(clean_df['Name'], clean_df['Code']))
                    clean_map = dict(zip(clean_df['CleanName'], clean_df['Code']))
                    
                    for name in names:
                        if name in name_map:
                            kosdaq150.append(name_map[name])
                        elif name.replace(' ', '') in clean_map:
                            kosdaq150.append(clean_map[name.replace(' ', '')])
                        else:
                            print(f"[WARNING] Could not map constituent '{name}' to code.")
                    kosdaq150 = list(set(kosdaq150))
                    print(f"Mapped {len(kosdaq150)} KOSDAQ 150 codes from Wisereport.")
            except Exception as e:
                print(f"Error scraping KOSDAQ 150: {e}")
                
    if kospi200 or kosdaq150:
        existing = {}
        if os.path.exists(JSON_PATH):
            try:
                with open(JSON_PATH, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except:
                pass
        
        final_kospi = kospi200 if kospi200 else existing.get('kospi200', [])
        final_kosdaq = kosdaq150 if kosdaq150 else existing.get('kosdaq150', [])
        
        constituents = {
            'kospi200': final_kospi,
            'kosdaq150': final_kosdaq
        }
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(constituents, f, ensure_ascii=False, indent=4)
        print(f"Saved constituents update to {JSON_PATH}")

def main():
    print("Starting database initialization...")
    
    # 1. Connect to Database (Creates if not exists)
    conn = sqlite3.connect(DB_PATH)
    
    # 2. Fetch Korean stock listings
    print("Fetching Korean stock listings from FinanceDataReader...")
    df_kor = fdr.StockListing('KRX')
    print(f"Fetched {len(df_kor)} Korean stock tickers.")
    
    # Fetch live constituents (via credentials or fallback)
    ensure_constituents(df_kor)
    
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
        
    # Add ETFs to df_kor
    etf_rows = pd.DataFrame([
        {'Code': '252650', 'Name': 'KODEX 200동일가중', 'Market': 'KRX', 'IsKOSPI200': 0, 'IsKOSDAQ150': 0},
        {'Code': '229200', 'Name': 'KODEX 코스닥150', 'Market': 'KRX', 'IsKOSPI200': 0, 'IsKOSDAQ150': 0},
        {'Code': '226490', 'Name': 'KODEX 코스피', 'Market': 'KRX', 'IsKOSPI200': 0, 'IsKOSDAQ150': 0}
    ])
    df_kor = pd.concat([df_kor, etf_rows], ignore_index=True)

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
        # Add ETFs to df_us
        us_etfs = pd.DataFrame([
            {'Symbol': 'SPY', 'Name': 'SPDR S&P 500 ETF Trust', 'Market': 'NYSE'},
            {'Symbol': 'QQQ', 'Name': 'Invesco QQQ Trust', 'Market': 'NASDAQ'},
            {'Symbol': 'DIA', 'Name': 'SPDR Dow Jones Industrial Average ETF Trust', 'Market': 'NYSE'}
        ])
        df_us = pd.concat([df_us, us_etfs], ignore_index=True)
        
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
