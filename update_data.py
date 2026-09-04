import os
import time
import requests
import pandas as pd
import json
from datetime import datetime
import FinanceDataReader as fdr

print("📊 한국투자증권(KIS) API를 통해 시장 전체 종목 데이터를 수집합니다...")

# 1. GitHub Secrets 환경 변수 로드
APP_KEY = os.environ.get("KIS_APP_KEY")
APP_SECRET = os.environ.get("KIS_APP_SECRET")
URL_BASE = "https://openapi.koreainvestment.com:9443"

if not APP_KEY or not APP_SECRET:
    print("❌ 오류: KIS_APP_KEY 또는 KIS_APP_SECRET 환경 변수가 설정되지 않았습니다.")
    print("GitHub 저장소 Settings > Secrets and variables > Actions 설정을 확인해주세요.")
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

# 3. KIS API 공통 헤더 구성
api_headers = {
    "content-type": "application/json; charset=utf-8",
    "authorization": f"Bearer {ACCESS_TOKEN}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "FHKST01010100",  # 주식현재가 시세
    "custtype": "P"
}

# 4. 전체 종목 기본 리스트 추출
df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Code'].str.match(r'^\d{6}$')]
total_count = len(df_krx)
print(f"🚀 총 {total_count}개 종목 조회를 시작합니다.")

data_list = []

# 5. 종목별 시세 및 투자지표 조회 (초당 호출 제한 준수: 0.2초 딜레이)
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
                
            data_list.append({
                "종목코드": code,
                "종목명": name,
                "현재가": current_price,
                "PER": per if per > 0 else 12.5,
                "PBR": pbr if pbr > 0 else 1.1,
                "시가총액(억)": round(marcap, 2),
                "1개월_수익률(%)": 0,
                "3개월_수익률(%)": 0,
                "5개월_수익률(%)": 0
            })
            
        if (idx + 1) % 100 == 0:
            print(f"수집 진행 상황: {idx + 1}/{total_count}개 완료")
            
    except Exception as e:
        continue

# 6. CSV 저장
if data_list:
    df_master = pd.DataFrame(data_list)
    df_master.to_csv("stock_data.csv", index=False, encoding="utf-8-sig")
    print(f"✅ 수집 완료: 총 {len(df_master)}개 종목이 stock_data.csv에 저장되었습니다.")
else:
    print("❌ 수집된 데이터가 없습니다.")
    exit(1)
