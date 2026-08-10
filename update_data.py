import pandas as pd
from pykrx import stock
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

def get_recent_bday(target_date):
    """특정 날짜 기준 가장 최근 주식시장 영업일을 찾습니다."""
    start = target_date - relativedelta(days=10)
    bdays = stock.get_business_days_dates(start.strftime("%Y%m%d"), target_date.strftime("%Y%m%d"))
    return bdays[-1] if len(bdays) > 0 else target_date

def get_price_data(date, market):
    """특정 영업일의 종가 데이터를 가져옵니다."""
    try:
        df = stock.get_market_ohlcv_by_ticker(date, market=market)
        return df[['종가']]
    except Exception:
        return pd.DataFrame()

print("🚀 7대 거장 스크리너 데이터 수집을 시작합니다...")

# 1. 기준 날짜 계산 (오늘, 1개월 전, 3개월 전, 5개월 전)
today = datetime.today()
date_t0 = get_recent_bday(today)
date_1m = get_recent_bday(today - relativedelta(months=1))
date_3m = get_recent_bday(today - relativedelta(months=3))
date_5m = get_recent_bday(today - relativedelta(months=5))

print(f"기준일: {date_t0.strftime('%Y-%m-%d')} (업데이트 진행 중...)")

# 2. 현재 기준 펀더멘털(PER, PBR, ROE, DIV) 및 시가총액 수집
df_fund_kospi = stock.get_market_fundamental_by_ticker(date_t0, market="KOSPI")
df_fund_kosdaq = stock.get_market_fundamental_by_ticker(date_t0, market="KOSDAQ")
df_fund = pd.concat([df_fund_kospi, df_fund_kosdaq])

df_cap_kospi = stock.get_market_cap_by_ticker(date_t0, market="KOSPI")
df_cap_kosdaq = stock.get_market_cap_by_ticker(date_t0, market="KOSDAQ")
df_cap = pd.concat([df_cap_kospi, df_cap_kosdaq])

# 3. 과거 종가 수집 (모멘텀 계산용)
markets = ["KOSPI", "KOSDAQ"]
price_t0, price_1m, price_3m, price_5m = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

for mkt in markets:
    price_t0 = pd.concat([price_t0, get_price_data(date_t0, mkt)])
    price_1m = pd.concat([price_1m, get_price_data(date_1m, mkt)])
    price_3m = pd.concat([price_3m, get_price_data(date_3m, mkt)])
    price_5m = pd.concat([price_5m, get_price_data(date_5m, mkt)])
    time.sleep(1) # 서버 과부하 방지

# 4. 데이터 병합 및 가공
df_master = df_fund.copy()
df_master['종목코드'] = df_master.index
df_master['종목명'] = [stock.get_market_ticker_name(t) for t in df_master.index]
df_master['시가총액(억)'] = df_cap['시가총액'] / 100000000

# 수익률 계산 (NaN 방지를 위해 기본값 0 처리)
df_master['현재가'] = price_t0['종가']
df_master['1개월전'] = price_1m['종가']
df_master['3개월전'] = price_3m['종가']
df_master['5개월전'] = price_5m['종가']

df_master['1개월_수익률(%)'] = ((df_master['현재가'] - df_master['1개월전']) / df_master['1개월전'] * 100).round(2)
df_master['3개월_수익률(%)'] = ((df_master['현재가'] - df_master['3개월전']) / df_master['3개월전'] * 100).round(2)
df_master['5개월_수익률(%)'] = ((df_master['현재가'] - df_master['5개월전']) / df_master['5개월전'] * 100).round(2)

# 불필요한 과거 가격 컬럼 삭제 및 인덱스 정리
df_master = df_master.drop(columns=['1개월전', '3개월전', '5개월전'])
df_master = df_master.reset_index(drop=True)

# 5. CSV 파일로 저장
df_master.to_csv("stock_data.csv", index=False, encoding="utf-8-sig")
print("✅ 데이터 수집 완료! 'stock_data.csv' 파일이 성공적으로 생성되었습니다.")
