import os
import time
import requests
import pandas as pd
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import FinanceDataReader as fdr
from pykrx import stock

print("📊 KIS API(실시간 재무) + pykrx(과거 주가) 하이브리드 수집을 시작합니다...")

# 1. GitHub Secrets 환경 변수 로드
APP_KEY = os.environ.get("KIS_APP_KEY")
APP_SECRET = os.environ.get("KIS_APP_SECRET")
URL_BASE = "https://openapi.koreainvestment.com:9443"

if not APP_KEY or not APP_SECRET:
    print("❌ 오류: KIS_APP_KEY 또는 KIS_APP_SECRET 환경 변수가 설정되지 않았습니다.")
    exit(1)

# 2. 접근 토큰(Access Token) 발급
token_headers = {"content-type": "application/json"}
token_body = {
    "grant_type": "client_credentials",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET
}
token_url = f"{URL_BASE}/oauth2/tokenP"

try:
    res = requests.post(token_url, headers=token_headers, data=json.dumps(token_body), timeout=10)
    token_data = res.json()
    ACCESS_TOKEN = token_data.get("access_token")
    
    if not ACCESS_TOKEN:
        print(f"❌ 토큰 발급 실패 응답: {token_data}")
        exit(1)
        
    print("✅ KIS API 접근 토큰 발급 완료")
except Exception as e:
    print(f"❌ 인증 서버 연결 실패: {e}")
    exit(1)

# KIS API 공통 헤더 구성
api_headers = {
    "content-type": "application/json; charset=utf-8",
    "authorization": f"Bearer {ACCESS_TOKEN}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "FHKST01010100",  
    "custtype": "P"
}

# 3. 과거 수익률 계산을 위한 영업일 계산 (KOSPI 달력 활용)
now = datetime.now()
try:
    kospi_df = fdr.DataReader('KS11', now - relativedelta(months=6), now)
    valid_days = kospi_df.index
except:
    valid_days = pd.DatetimeIndex([now])

def get_bizday(target_date):
    target_ts = pd.to_datetime(target_date)
    past_days = valid_days[valid_days <= target_ts]
    if len(past_days) > 0:
        return past_days[-1].strftime("%Y%m%d")
    return target_ts.strftime("%Y%m%d")

date_1m = get_bizday(now - relativedelta(months=1))
date_3m = get_bizday(now - relativedelta(months=3))
date_5m = get_bizday(now - relativedelta(months=5))

print(f"🗓️ 수익률 기준일 산정 완료 (1개월:{date_1m}, 3개월:{date_3m}, 5개월:{date_5m})")

# 4. 과거 주가 일괄 다운로드 (서버 차단 방지를 위해 요청당 3초 휴식)
print("🚀 과거 주가 데이터를 일괄 수집합니다...")
def get_historical_safe(date_str):
    try:
        time.sleep(3)
        return stock.get_market_ohlcv(date_str, market="ALL")
    except Exception as e:
        print(f"⚠️ {date_str} 과거 데이터 수집 실패. 수익률 0%로 대체됩니다.")
        return pd.DataFrame()

df_p1 = get_historical_safe(date_1m)
df_p3 = get_historical_safe(date_3m)
df_p5 = get_historical_safe(date_5m)

# 5. 전체 종목 기본 리스트 추출
df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Code'].str.match(r'^\d{6}$')]
total_count = len(df_krx)
print(f"🚀 총 {total_count}개 종목의 KIS API 실시간 재무 데이터 조회를 시작합니다.")

data_list = []

# 6. 종목별 시세 조회 및 수익률 병합 (초당 호출 제한 준수: 0.2초 딜레이)
for idx, row in df_krx.iterrows():
    code = str(row['Code'])
    name = row['Name']
    
    try:
        time.sleep(0.2) 
        
        url = f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code
        }
        
        response = requests.get(url, headers=api_headers, params=params, timeout=5)
        res_data = response.json()
        
        if res_data.get('rt_cd') == '0':
            output = res_data.get('output', {})
            
            current_price = float(output.get('stck_prpr') or 0)
            per = float(output.get('per') or 0)
            pbr = float(output.get('pbr') or 0)
            marcap = float(output.get('hts_avls') or 0) / 100  # 억 단위 변환
            
            if current_price == 0:
                continue

            # 과거 가격 추출 (데이터가 없으면 현재가와 동일하게 처리하여 수익률 0% 방어)
            p1 = float(df_p1.loc[code, '종가']) if not df_p1.empty and code in df_p1.index else current_price
            p3 = float(df_p3.loc[code, '종가']) if not df_p3.empty and code in df_p3.index else current_price
            p5 = float(df_p5.loc[code, '종가']) if not df_p5.empty and code in df_p5.index else current_price

            # 수익률 계산 (소수점 2자리)
            ret_1m = round(((current_price - p1) / p1) * 100, 2) if p1 > 0 else 0
            ret_3m = round(((current_price - p3) / p3) * 100, 2) if p3 > 0 else 0
            ret_5m = round(((current_price - p5) / p5) * 100, 2) if p5 > 0 else 0
                
            data_list.append({
                "종목코드": code,
                "종목명": name,
                "현재가": current_price,
                "PER": per if per > 0 else 12.5,
                "PBR": pbr if pbr > 0 else 1.1,
                "시가총액(억)": round(marcap, 2),
                "1개월_수익률(%)": ret_1m,
                "3개월_수익률(%)": ret_3m,
                "5개월_수익률(%)": ret_5m
            })
            
        if (idx + 1) % 100 == 0:
            print(f"수집 진행 상황: {idx + 1}/{total_count}개 완료")
            
    except Exception as e:
        continue

# 7. CSV 저장
if data_list:
    df_master = pd.DataFrame(data_list)
    df_master.to_csv("stock_data.csv", index=False, encoding="utf-8-sig")
    print(f"✅ 하이브리드 수집 완료: 총 {len(df_master)}개 종목이 stock_data.csv에 저장되었습니다.")
else:
    print("❌ 수집된 데이터가 없습니다.")
    exit(1)
