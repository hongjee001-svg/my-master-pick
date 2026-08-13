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
print("✅ 한투 API 토큰 발급 성공! (차단 없는 VIP 통로 개방)")

# 2. 한투 API 통신 헤더 세팅
api_headers = {
    "content-type": "application/json",
    "authorization": f"Bearer {ACCESS_TOKEN}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "FHKST01010100" # 주식현재가 시세 (PER, PBR 등 재무지표 포함)
}

# 3. 분석 대상 종목 가져오기 (초기 테스트: 코스피/코스닥 시가총액 상위 300개)
print("📊 시장 종목 데이터를 불러옵니다...")
df_krx = fdr.StockListing('KRX')
df_top = df_krx.head(300).copy()

data_list = []
print("🚀 실시간 주가 및 재무 데이터 수집 시작 (초당 제한을 피하기 위해 안전하게 수집합니다)...")

# 4. 종목별 한투 API 호출 반복
for idx, row in df_top.iterrows():
    code = row['Code']
    name = row['Name']
    
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": code
    }
    
    try:
        resp = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price", headers=api_headers, params=params)
        time.sleep(0.06) # 한투 API 초당 20건 제한 방어 (안전 장치)
        
        if resp.status_code == 200 and resp.json()["rt_cd"] == "0":
            output = resp.json()["output"]
            
            # API 응답에서 수치형 데이터 추출 (없으면 0 처리)
            per = float(output.get("per", 0)) if output.get("per") else 0
            pbr = float(output.get("pbr", 0)) if output.get("pbr") else 0
            div = float(output.get("eps", 0)) if output.get("eps") else 0 # 임시로 EPS 할당, 추후 배당수익률로 고도화 가능
            
            data_list.append({
                "종목코드": code,
                "종목명": name,
                "현재가": float(output["stck_prpr"]),
                "PER": per,
                "PBR": pbr,
                "시가총액(억)": float(output["hts_avls"]),
                # 임시 모멘텀 더미 데이터 (한투 API 수집 1단계 테스트용)
                "1개월_수익률(%)": 5.0, 
                "3개월_수익률(%)": 10.0,
                "5개월_수익률(%)": 15.0
            })
    except Exception as e:
        print(f"⚠️ {name}({code}) 수집 중 오류: {e}")

# 5. CSV 저장
df_master = pd.DataFrame(data_list)
df_master.to_csv("stock_data.csv", index=False, encoding="utf-8-sig")
print(f"✅ 완벽하게 수집 성공! 총 {len(df_master)}개 종목의 'stock_data.csv'가 만들어졌습니다.")
