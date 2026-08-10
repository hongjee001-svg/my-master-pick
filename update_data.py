import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import time

def get_recent_bday(target_date):
    """특정 날짜 기준 가장 최근 주식시장 영업일을 찾습니다. (라이브러리 버그 우회 방식)"""
    start = (target_date - relativedelta(days=10)).strftime("%Y%m%d")
    end = target_date.strftime("%Y%m%d")
    
    try:
        # 삼성전자(005930) 주가로 실제 장이 열린 마지막 날짜 추출
        df = stock.get_market_ohlcv_by_ticker(start, end, "005930")
        if not df.empty:
            return df.index[-1]
    except Exception:
        pass
    
    return target_date

def get_price_data(date, market):
    """특정 영업일의 종가 데이터를 가져옵니다."""
    date_str = date.strftime("%Y%m%d")
    try:
        df = stock.get_market_ohlcv_by_ticker(date_str, market=market)
        return df[['종가']]
    except Exception:
        return pd.DataFrame()

print("🚀 7대 거장 스크리너 데이터 수집을 시작합니다...")

# 1. 한국 시간(KST) 설정 및 안전 장치 도입
kst = timezone(timedelta(hours=9))
now = datetime.now(kst)

# 오전이나 장중(오후 4시 이전)에 실행될 경우, 아직 데이터가 없으므로 무조건 전날(과거) 기준으로 설정
if now.hour < 16:
    base_date = now - timedelta(days=1)
    print("💡 아직 장 마감 전이므로 가장 최근 영업일 기준으로 데이터를 수집합니다.")
else:
    base_date = now

# pykrx 라이브러리와의 호환성을 위해 시간대 정보(tz) 제거
base_date = base_date.replace(tzinfo=None)

# 2. 기준 날짜 계산
date_t0 = get_recent_bday(base_date)
date_1m = get_recent_bday(base_date - relativedelta(months=1))
date_3m = get_recent_bday(base_date - relativedelta(months=3))
date_5m = get_recent_bday(base_date - relativedelta(months=5))

print(f"기준일: {date_t0.strftime('%Y-%m-%d')}")

# 3. 현재 기준 펀더멘털(PER, PBR, ROE, DIV) 및 시가총액 수집
date_t0_str = date_t0.strftime("%Y%m%d")
df_fund_kospi = stock.get_market_fundamental_by_ticker(date_t0_str, market="KOSPI")
df_fund_kosdaq = stock.get_market_fundamental_by_ticker(date_t0_str, market="KOSDAQ")
df_fund = pd.concat([df_fund_kospi, df_fund_kosdaq])

df_cap_kospi = stock.get_market_cap_by_ticker(date_t0_str, market="KOSPI")
df_cap_kosdaq = stock.get_market_cap_by_ticker(date_t0_str, market="KOSDAQ")
df_cap = pd.concat([df_cap_kospi, df_cap_kosdaq])

# 4. 과거 종가 수집 (모멘텀 계산용)
markets = ["KOSPI", "KOSDAQ"]
price_t0, price_1m, price_3m, price_5m = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

for mkt in markets:
    price_t0 = pd.concat([price_t0, get_price_data(date_t0, mkt)])
    price_1m = pd.concat([price_1m, get_price_data(date_1m, mkt)])
    price_3m = pd.concat([price_3m, get_price_data(date_3m, mkt)])
    price_5m = pd.concat([price_5m, get_price_data(date_5m, mkt)])
    time.sleep(1) 

# 5. 데이터 병합 및 가공
df_master = df_fund.copy()
df_master['종목코드'] = df_master.index
df_master['종목명'] = [stock.get_market_ticker_name(t) for t in df_master.index]
df_master['시가총액(억)'] = df_cap['시가총액'] / 100000000

df_master['현재가'] = price_t0['종가']
df_master['1개월전'] = price_1m['종가']
df_master['3개월전'] = price_3m['종가']
df_master['5개월전'] = price_5m['종가']

df_master['1개월_수익률(%)'] = ((df_master['현재가'] - df_master['1개월전']) / df_master['1개월전'] * 100).round(2)
df_master['3개월_수익률(%)'] = ((df_master['현재가'] - df_master['3개월전']) / df_master['3개월전'] * 100).round(2)
df_master['5개월_수익률(%)'] = ((df_master['현재가'] - df_master['5개월전']) / df_master['5개월전'] * 100).round(2)

df_master = df_master.drop(columns=['1개월전', '3개월전', '5개월전'])
df_master = df_master.reset_index(drop=True)

df_master.to_csv("stock_data.csv", index=False, encoding="utf-8-sig")
print("✅ 데이터 수집 완료! 'stock_data.csv' 파일이 생성되었습니다.")
