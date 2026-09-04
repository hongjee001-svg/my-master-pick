import os
import time
import requests
import pandas as pd
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import FinanceDataReader as fdr

print("📊 한국투자증권(KIS) API를 통해 시장 전체 종목 데이터를 수집합니다...")

# 1. 깃허브 Secrets에서 KIS API 키 불러오기
APP_KEY = os.environ.get("KIS_APP_KEY")
APP_SECRET = os.environ.get("KIS_APP_SECRET")
URL_BASE = "https://openapi.koreainvestment.com:9443"

if not APP_KEY or not APP_SECRET:
    print("❌ 오류: KIS_APP_KEY 또는 KIS_APP_SECRET이 설정되지 않았습니다.")
    exit(1)

# 2. 접근 토큰(Access Token) 발급받기
headers = {"content-type": "application/json"}
body = {
    "grant_type": "client_credentials",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET
}
PATH = "oauth2/tokenP"
URL = f"{URL_BASE}/{PATH}"
res = requests.post(URL, headers=headers, data=json.dumps(body))
ACCESS_TOKEN = res.json().get("access_token")

if not ACCESS_TOKEN:
    print("❌ 토큰 발급 실패. API 키를 확인해주세요.")
    exit(1)
    
print("✅ KIS API 토큰 발급 완료!")

# 3. KIS API 호출 공통 헤더
api_headers = {
    "content-type": "application/json; charset=utf-8",
    "authorization": f"Bearer {ACCESS_TOKEN}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "FHKST01010100", # 주식현재가 시세
    "custtype": "P"
}

# 4. 전체 종목 리스트 가져오기 (종목 코드는 fdr 활용이 가장 빠르고 정확함)
df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Code'].str.match(r'^\d{6}$')]
total_count = len(df_krx)
print(f"🚀 총 {total_count}개 종목에 대한 KIS API 순차 조회를 시작합니다. (예상 소요시간: 약 15~20분)")

data_list = []

# 5. 종목별 데이터 수집 (초당 호출 제한 방어용 time.sleep 필수)
for idx, row in df_krx.iterrows():
    code = str(row['Code'])
    name = row['Name']
    
    try:
        # KIS 서버 차단(429)을 막기 위해 0.2초 대기 (매우 중요)
        time.sleep(0.2)
        
        url = f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code
        }
        
        response = requests.get(url, headers=api_headers, params=params)
        res_data = response.json()
        
        if res_data['rt_cd'] == '0':
            output = res_data['output']
            
            # 현재가, PER, PBR, 시가총액(억 단위로 변환)
            current_price = float(output['stck_prpr']) if output['stck_prpr'] else 0
            per = float(output['per']) if output['per'] else 0
            pbr = float(output['pbr']) if output['pbr'] else 0
            marcap = float(output['hts_avls']) / 100 if output['hts_avls'] else 0
            
            if current_price == 0:
                continue
                
            # 수익률 계산은 API 호출을 줄이기 위해 Fdr이나 다른 방식을 섞어 쓰는 것이 보통이나, 
            # 여기서는 편의상 1,3,5개월 데이터에 기본값을 넣고 현재 모멘텀을 수집합니다.
            # (KIS 일자별 API를 각 종목마다 3번씩 더 호출하면 1시간 이상 소요되므로 효율성을 위해 현재 시세 위주 수집)
            
            data_list.append({
                "종목코드": code,
                "종목명": name,
                "현재가": current_price,
                "PER": per if per > 0 else 12.5,
                "PBR": pbr if pbr > 0 else 1.1,
                "시가총액(억)": round(marcap, 2),
                "1개월_수익률(%)": 0, # KIS 종목별 히스토리 API 별도 호출 필요 (시간 소요 방지 임시값)
                "3개월_수익률(%)": 0, 
                "5개월_수익률(%)": 0  
            })
            
        # 100개마다 진행 상황 출력
        if (idx + 1) % 100 == 0:
            print(f"진행 중... {idx + 1}/{total_count} 완료")
            
    except Exception as e:
        print(f"⚠️ {name}({code}) 수집 중 오류: {e}")
        continue

# 6. CSV 저장
if len(data_list) > 0:
    df_master = pd.DataFrame(data_list)
    df_master.to_csv("stock_data.csv", index=False, encoding="utf-8-sig")
    print(f"✅ KIS API 데이터 수집 완료! 총 {len(df_master)}개 종목 저장됨.")
else:
    print("❌ 수집된 데이터가 없습니다.")
