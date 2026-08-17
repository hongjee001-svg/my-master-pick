import os
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
import FinanceDataReader as fdr

print("📊 FinanceDataReader를 통해 시장 전체(코스피/코스닥) 종목 데이터를 불러옵니다...")

# 1. 날짜 설정 (오늘, 1/3/5개월 전)
now = datetime.now()
date_t0 = now.strftime("%Y-%m-%d")
date_1m = (now - relativedelta(months=1)).strftime("%Y-%m-%d")
date_3m = (now - relativedelta(months=3)).strftime("%Y-%m-%d")
date_5m = (now - relativedelta(months=5)).strftime("%Y-%m-%d")

# 2. KRX 전체 종목 가져오기 (제한 없이 모든 종목 스캔)
df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Code'].str.match(r'^\d{6}$')]
df_all = df_krx.copy() # 제한을 두지 않고 전체 데이터를 복사합니다.

data_list = []
print(f"🚀 총 {len(df_all)}개 전체 종목의 과거 주가 및 지표 계산 시작... (약 10~15분 소요 예상)")

# 3. 종목별 과거 주가 및 수익률 계산
for idx, row in df_all.iterrows():
    code = row['Code']
    name = row['Name']
    
    try:
        df_hist = fdr.DataReader(code, date_5m, date_t0)
        
        if df_hist.empty or len(df_hist) < 3:
            continue
            
        current_price = float(df_hist.iloc[-1]['Close'])
        
        def get_past_price(target_date_str):
            target = pd.to_datetime(target_date_str)
            past_df = df_hist[df_hist.index <= target]
            if not past_df.empty:
                return float(past_df.iloc[-1]['Close'])
            return current_price
            
        price_1m = get_past_price(date_1m)
        price_3m = get_past_price(date_3m)
        price_5m = get_past_price(date_5m)
        
        ret_1m = round(((current_price - price_1m) / price_1m) * 100, 2) if price_1m > 0 else 0
        ret_3m = round(((current_price - price_3m) / price_3m) * 100, 2) if price_3m > 0 else 0
        ret_5m = round(((current_price - price_5m) / price_5m) * 100, 2) if price_5m > 0 else 0
        
        market_cap = float(row.get('Marcap', 50000000000) / 100000000) if 'Marcap' in row and pd.notna(row['Marcap']) else 1000
        per = float(row.get('PER', 12.5)) if 'PER' in row and pd.notna(row['PER']) else 12.5
        pbr = float(row.get('PBR', 1.1)) if 'PBR' in row and pd.notna(row['PBR']) else 1.1
        
        data_list.append({
            "종목코드": code,
            "종목명": name,
            "현재가": current_price,
            "PER": per if per > 0 else 10.0,
            "PBR": pbr if pbr > 0 else 1.0,
            "시가총액(억)": market_cap,
            "1개월_수익률(%)": ret_1m, 
            "3개월_수익률(%)": ret_3m,
            "5개월_수익률(%)": ret_5m
        })
    except Exception as e:
        pass

# 4. CSV 저장
if len(data_list) > 0:
    df_master = pd.DataFrame(data_list)
    df_master.to_csv("stock_data.csv", index=False, encoding="utf-8-sig")
    print(f"✅ 전체 수집 완료! 총 {len(df_master)}개 종목의 데이터가 갱신되었습니다.")
else:
    print("❌ 수집된 데이터가 없습니다.")
