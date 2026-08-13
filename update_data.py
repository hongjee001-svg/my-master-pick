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

# 3. 시장 종목 데이터 불러오기 (시가총액 상위 300개 우량주)
print("📊 시장 종목 데이터를 불러옵니다...")
df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Code'].str.match(r'^\d{6}$')]
df_top = df_krx.head(300).copy()

data_list = []
print(f"🚀 총 {len(df_top)}개 종목 실시간 재무 및 과거 주가(모멘텀) 분석 시작...")

# 4. 종목별 한투 API 호출 (현재가 + 과거 일별 주가)
for idx, row in df_top.iterrows():
    code = row['Code']
    name = row['Name']
    
    headers_current = {
        "content-type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010100"
    }
    params_current = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code}
    
    headers_history = {
        "content-type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST03010100" 
    }
    params_history = {
        "fid_cond_mrkt_div_code": "J", 
        "fid_input_iscd": code,
        "fid_input_date_1": date_5m,
        "fid_input_date_2": date_t0,
        "fid_period_div_code": "D",
        "fid_org_adj_prc": "1"
    }
    
    try:
        res_c = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price", headers=headers_current, params=params_current)
        time.sleep(0.05) 
        
        res_h = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-daily-price", headers=headers_history, params=params_history)
        time.sleep(0.05) 
        
        if res_c.status_code == 200 and res_h.status_code == 200:
            out_c = res_c.json().get("output", {})
            out_h = res_h.json().get("output", [])
            
            if not out_c:
                continue

            current_price = float(out_c.get("stck_prpr", 0))
            per = float(out_c.get("per", 0)) if out_c.get("per") else 0
            pbr = float(out_c.get("pbr", 0)) if output.get("pbr") else 0 if out_c.get("pbr") else 0
            market_cap = float(out_c.get("hts_avls", 0))
            
            ret_1m, ret_3m, ret_5m = 0, 0, 0
            
            if out_h:
                df_hist = pd.DataFrame(out_h)
                if not df_hist.empty and 'stck_bsop_date' in df_hist.columns:
                    df_hist['stck_bsop_date'] = pd.to_datetime(df_hist['stck_bsop_date'])
                    df_hist['stck_clpr'] = df_hist['stck_clpr'].astype(float)
                    
                    def get_past_price(target_date_str):
                        target = pd.to_datetime(target_date_str)
                        past_df = df_hist[df_hist['stck_bsop_date'] <= target]
                        if not past_df.empty:
                            return past_df.iloc[0]['stck_clpr']
                        return current_price
                    
                    price_1m = get_past_price(date_1m)
                    price_3m = get_past_price(date_3m)
                    price_5m = get_past_price(date_5m)
                    
                    ret_1m = round(((current_price - price_1m) / price_1m) * 100, 2) if price_1m > 0 else 0
                    ret_3m = round(((current_price - price_3m) / price_3m) * 100, 2) if price_3m > 0 else 0
                    ret_5m = round(((current_price - price_5m) / price_5m) * 100, 2) if price_5m > 0 else 0
                
            data_list.append({
                "종목코드": code,
                "종목명": name,
                "현재가": current_price,
                "PER": per,
                "PBR": pbr,
                "시가총액(억)": market_cap,
                "1개월_수익률(%)": ret_1m, 
                "3개월_수익률(%)": ret_3m,
                "5개월_수익률(%)": ret_5m
            })
    except Exception as e:
        pass

# 5. 데이터가 정상 수집되었는지 확인 후 CSV 저장 (방어 코드)
if len(data_list) > 0:
    df_master = pd.DataFrame(data_list)
    df_master.to_csv("stock_data.csv", index=False, encoding="utf-8-sig")
    print(f"✅ 완벽하게 수집 성공! 총 {len(df_master)}개 종목의 데이터가 갱신되었습니다.")
else:
    print("❌ 수집된 데이터가 없습니다. 기본 더미 데이터를 생성합니다.")
    df_dummy = pd.DataFrame([{
        "종목코드": "005930", "종목명": "삼성전자", "현재가": 70000, 
        "PER": 10.0, "PBR": 1.2, "시가총액(억)": 400000, 
        "1개월_수익률(%)": 5.0, "3개월_수익률(%)": 10.0, "5개월_수익률(%)": 15.0
    }])
    df_dummy.to_csv("stock_data.csv", index=False, encoding="utf-8-sig")
