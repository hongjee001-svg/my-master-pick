import os
import requests
import json
import pandas as pd
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import FinanceDataReader as fdr

# 1. 깃허브 환경 변수에서 한투 API 키 불러오기
APP_KEY = os.environ.get("KIS_APP_KEY")
APP_SECRET = os.environ.get("KIS_APP_SECRET")
URL_BASE = "https://openapi.koreainvestment.com:9443"

print("🔑 한국투자증권 API 토큰 발급 요청 중...")
headers = {"content-type": "application/json"}
body = {
    "grant_type": "client_credentials",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET
}
res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers=headers, data=json.dumps(body))
ACCESS_TOKEN = res.json().get("access_token")

if not ACCESS_TOKEN:
    print("❌ 토큰 발급 실패! API 키나 시크릿 값을 다시 확인해주세요.")
    exit(1)
print("✅ 한투 API 토큰 발급 성공!")

# 2. 날짜 설정 (오늘, 1/3/5개월 전)
now = datetime.now()
date_t0 = now.strftime("%Y%m%d")
date_1m = (now - relativedelta(months=1)).strftime("%Y%m%d")
date_3m = (now - relativedelta(months=3)).strftime("%Y%m%d")
date_5m = (now - relativedelta(months=5)).strftime("%Y%m%d")

# 3. 시장 전체 종목 리스트 불러오기 (초기 테스트: 시총 상위 300개로 제한)
print("📊 시장 종목 데이터를 불러옵니다...")
df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Code'].str.match(r'^\d{6}$')]
df_top = df_krx.head(300).copy()

data_list = []
print(f"🚀 총 {len(df_top)}개 종목 재무 및 모멘텀 분석 시작...")

# 4. 종목별 한투 API 호출 반복
for idx, row in df_top.iterrows():
    code = row['Code']
    name = row['Name']
    
    headers_api = {
        "content-type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010100"
    }
    
    params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code}
    
    try:
        resp = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price", headers=headers_api, params=params)
        time.sleep(0.06) 
        
        if resp.status_code == 200 and resp.json()["rt_cd"] == "0":
            output = resp.json()["output"]
            
            per = float(output.get("per", 0)) if output.get("per") else 0
            pbr = float(output.get("pbr", 0)) if output.get("pbr") else 0
            
            # 모멘텀 수익률 (계산 로직 - 테스트용 더미 데이터 유지)
            # 추후 과거 주가 API 결합 시 이 부분만 업데이트 예정
            data_list.append({
                "종목코드": code,
                "종목명": name,
                "현재가": float(output["stck_prpr"]),
                "PER": per,
                "PBR": pbr,
                "시가총액(억)": float(output["hts_avls"]),
                "1개월_수익률(%)": 5.0, 
                "3개월_수익률(%)": 10.0,
                "5개월_수익률(%)": 15.0
            })
    except Exception as e:
        print(f"⚠️ {name}({code}) 오류: {e}")

# 5. CSV 저장
df_master = pd.DataFrame(data_list)
df_master.to_csv("stock_data.csv", index=False, encoding="utf-8-sig")
print(f"✅ 수집 성공! 'stock_data.csv'가 생성되었습니다.")
