import os
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
import FinanceDataReader as fdr
from pykrx import stock

print("📊 시장 전체 종목 데이터를 초고속(Bulk)으로 수집합니다...")

now = datetime.now()

# 한국 시장 휴장일을 피해 가장 가까운 평일(영업일)을 찾아주는 함수
def get_closest_bizday(target_date):
    biz_days = stock.get_business_days_of_month(target_date.year, target_date.month)
    if len(biz_days) == 0:
        return target_date.strftime("%Y%m%d")
    
    past_days = [d for d in biz_days if d <= target_date]
    if past_days:
        return past_days[-1].strftime("%Y%m%d")
    return biz_days[0].strftime("%Y%m%d")

date_t0 = get_closest_bizday(now)
date_1m = get_closest_bizday(now - relativedelta(months=1))
date_3m = get_closest_bizday(now - relativedelta(months=3))
date_5m = get_closest_bizday(now - relativedelta(months=5))

print(f"기준일: {date_t0}, 1개월전: {date_1m}, 3개월전: {date_3m}, 5개월전: {date_5m}")

# 1. KRX 전체 종목 기본 정보 가져오기
df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Code'].str.match(r'^\d{6}$')]

print("🚀 과거 주가 데이터를 한 번에 가져옵니다... (약 15초 소요)")

# 2. pykrx를 이용해 특정 날짜의 전종목 주가를 한 방에 통째로 가져오기
df_p0 = stock.get_market_ohlcv(date_t0, market="ALL")
df_p1 = stock.get_market_ohlcv(date_1m, market="ALL")
df_p3 = stock.get_market_ohlcv(date_3m, market="ALL")
df_p5 = stock.get_market_ohlcv(date_5m, market="ALL")

data_list = []

# 3. 데이터 병합 (초고속 처리)
for idx, row in df_krx.iterrows():
    code = str(row['Code'])
    name = row['Name']
    
    try:
        if code not in df_p0.index:
            continue
            
        current_price = float(df_p0.loc[code, '종가'])
        if current_price == 0:
            continue

        price_1m = float(df_p1.loc[code, '종가']) if code in df_p1.index and float(df_p1.loc[code, '종가']) > 0 else current_price
        price_3m = float(df_p3.loc[code, '종가']) if code in df_p3.index and float(df_p3.loc[code, '종가']) > 0 else current_price
        price_5m = float(df_p5.loc[code, '종가']) if code in df_p5.index and float(df_p5.loc[code, '종가']) > 0 else current_price
        
        ret_1m = round(((current_price - price_1m) / price_1m) * 100, 2)
        ret_3m = round(((current_price - price_3m) / price_3m) * 100, 2)
        ret_5m = round(((current_price - price_5m) / price_5m) * 100, 2)
        
        market_cap = float(row.get('Marcap', 50000000000) / 100000000) if pd.notna(row.get('Marcap')) else 1000
        per = float(row.get('PER', 12.5)) if pd.notna(row.get('PER')) else 12.5
        pbr = float(row.get('PBR', 1.1)) if pd.notna(row.get('PBR')) else 1.1
        
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
    print(f"✅ 초고속 수집 완료! 총 {len(df_master)}개 종목의 데이터가 갱신되었습니다.")
else:
    print("❌ 수집된 데이터가 없습니다.")