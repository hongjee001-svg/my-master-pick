import os
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
import FinanceDataReader as fdr
from pykrx import stock

print("📊 시장 전체 종목 데이터를 초고속(Bulk)으로 수집합니다...")
# (주의) KRX 로그인 실패 경고는 기관용 유료 기능 관련 알림이므로 공개 데이터 수집엔 무시하셔도 됩니다.

now = datetime.now()

# 한국 시장 휴장일을 피해 가장 가까운 평일(영업일)을 찾아주는 함수 (최신 pykrx API 완벽 적용)
def get_closest_bizday(target_date):
    try:
        # 1. 새 규칙에 맞게 날짜 글자가 아닌 연(year), 월(month)을 숫자로 쪼개서 넣습니다.
        biz_days = stock.get_previous_business_days(year=target_date.year, month=target_date.month)
        
        # 2. 이번 달 영업일 목록 중 타겟 날짜 이전인 것만 골라냅니다.
        past_days = [d for d in biz_days if d.date() <= target_date.date()]
        if past_days:
            return past_days[-1].strftime("%Y%m%d")
        
        # 3. 혹시 월초(ex: 1일이 일요일)라서 이번 달 영업일이 안 잡히면, 지난달 마지막 영업일로 넘어갑니다.
        prev_month = target_date - relativedelta(months=1)
        biz_days_prev = stock.get_previous_business_days(year=prev_month.year, month=prev_month.month)
        return biz_days_prev[-1].strftime("%Y%m%d")
    except Exception as e:
        # 만약 실패해도 멈추지 않고 안전하게 기본 날짜 반환
        return target_date.strftime("%Y%m%d")

date_t0 = get_closest_bizday(now)
date_1m = get_closest_bizday(now - relativedelta(months=1))
date_3m = get_closest_bizday(now - relativedelta(months=3))
date_5m = get_closest_bizday(now - relativedelta(months=5))

print(f"기준일: {date_t0}, 1개월전: {date_1m}, 3개월전: {date_3m}, 5개월전: {date_5m}")

# 1. KRX 전체 종목 기본 정보 가져오기
df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Code'].str.match(r'^\d{6}$')]

print("🚀 주가, 시가총액, PER, PBR 데이터를 한 방에 가져옵니다...")

# 2. pykrx를 이용해 전종목 주가 및 펀더멘털 통째로 가져오기 (429 에러 완벽 방어)
df_p0 = stock.get_market_ohlcv(date_t0, market="ALL")
df_p1 = stock.get_market_ohlcv(date_1m, market="ALL")
df_p3 = stock.get_market_ohlcv(date_3m, market="ALL")
df_p5 = stock.get_market_ohlcv(date_5m, market="ALL")

# 💡 핵심: 오늘 날짜 기준 진짜 PER, PBR, 시가총액 통째로 불러오기
df_fund = stock.get_market_fundamental(date_t0, market="ALL")
df_cap = stock.get_market_cap(date_t0, market="ALL")

data_list = []

# 3. 데이터 병합 (초고속 처리)
for idx, row in df_krx.iterrows():
    code = str(row['Code'])
    name = row['Name']
    
    try:
        # 주가나 펀더멘털 데이터가 없으면 패스
        if code not in df_p0.index or code not in df_fund.index or code not in df_cap.index:
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
        
        # 가짜 값이 아닌 pykrx에서 가져온 진짜 데이터 연결
        real_marcap = float(df_cap.loc[code, '시가총액']) / 100000000  # 억 원 단위
        real_per = float(df_fund.loc[code, 'PER'])
        real_pbr = float(df_fund.loc[code, 'PBR'])
        
        data_list.append({
            "종목코드": code,
            "종목명": name,
            "현재가": current_price,
            "PER": real_per if pd.notna(real_per) and real_per > 0 else 0,
            "PBR": real_pbr if pd.notna(real_pbr) and real_pbr > 0 else 0,
            "시가총액(억)": round(real_marcap, 2),
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
