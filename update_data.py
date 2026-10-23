import os
import time
import requests
import pandas as pd
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import FinanceDataReader as fdr
from pykrx import stock

print("📊 [V4.0] 7대 거장 퀀트 지표 + 월봉 엔벨로프 하단 이탈 수집 시작...")

APP_KEY = os.environ.get("KIS_APP_KEY")
APP_SECRET = os.environ.get("KIS_APP_SECRET")
URL_BASE = "https://openapi.koreainvestment.com:9443"

if not APP_KEY or not APP_SECRET:
    print("❌ 오류: API 키가 없습니다.")
    exit(1)

token_headers = {"content-type": "application/json"}
token_body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
try:
    res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers=token_headers, data=json.dumps(token_body), timeout=10)
    ACCESS_TOKEN = res.json().get("access_token")
    print("✅ KIS API 접근 토큰 발급 완료")
except Exception as e:
    print(f"❌ 인증 실패: {e}"); exit(1)

api_headers = {
    "content-type": "application/json; charset=utf-8",
    "authorization": f"Bearer {ACCESS_TOKEN}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "FHKST01010100",  
    "custtype": "P"
}

now = datetime.now()
try:
    kospi_df = fdr.DataReader('KS11', now - relativedelta(months=1), now)
    valid_days = kospi_df.index
    today_str = valid_days[-1].strftime("%Y%m%d")
except:
    today_str = now.strftime("%Y%m%d")

print("📈 전체 상장사 배당(DIV) 및 업종 데이터 확보 중...")
try:
    time.sleep(1)
    df_fund = stock.get_market_fundamental(today_str, market="ALL")
except:
    df_fund = pd.DataFrame()

try:
    df_desc = fdr.StockListing('KRX-DESC')
    sector_dict = dict(zip(df_desc['Code'], df_desc['Sector']))
except:
    sector_dict = {}

df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Code'].str.match(r'^\d{6}$')]
total_count = len(df_krx)

data_list = []

for idx, row in df_krx.iterrows():
    code = str(row['Code'])
    name = row['Name']
    
    try:
        time.sleep(0.2) 
        
        url = f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code}
        response = requests.get(url, headers=api_headers, params=params, timeout=5)
        res_data = response.json()
        
        current_price = float(row.get('Close') or 0)
        per, pbr, marcap = 0.0, 0.0, 0.0
        
        if res_data.get('rt_cd') == '0':
            output = res_data.get('output', {})
            current_price = float(output.get('stck_prpr') or current_price)
            per = float(output.get('per') or 0)
            pbr = float(output.get('pbr') or 0)
            marcap = float(output.get('hts_avls') or 0) / 100 
            
        if current_price == 0: continue

        sector = sector_dict.get(code, "기타")
        if pd.isna(sector) or not sector: sector = "기타"
        
        div = float(df_fund.loc[code, 'DIV']) if not df_fund.empty and code in df_fund.index else 0.0
        roe = round((pbr / per) * 100, 2) if per > 0 else 0.0
        peg = round(per / roe, 2) if roe > 0 else 0.0

        ret_1m, ret_3m, ret_5m = 0.0, 0.0, 0.0
        env_20_sma, env_down_10, env_down_20, env_down_30 = 0.0, 0.0, 0.0, 0.0
        
        try:
            # 💡 20개월 이평선 계산을 위해 과거 25개월치 주가 데이터를 수집
            hist = fdr.DataReader(code, now - relativedelta(months=25), now)
            if not hist.empty and len(hist) > 5:
                p_current = hist['Close'].iloc[-1]
                
                # 1. 과거 수익률 계산
                p_1m = hist['Close'].iloc[-20] if len(hist) >= 20 else hist['Close'].iloc[0]
                p_3m = hist['Close'].iloc[-60] if len(hist) >= 60 else hist['Close'].iloc[0]
                p_5m = hist['Close'].iloc[-100] if len(hist) >= 100 else hist['Close'].iloc[0]
                
                if p_1m > 0: ret_1m = round(((p_current - p_1m) / p_1m) * 100, 2)
                if p_3m > 0: ret_3m = round(((p_current - p_3m) / p_3m) * 100, 2)
                if p_5m > 0: ret_5m = round(((p_current - p_5m) / p_5m) * 100, 2)
                
                # 2. 💡 월봉 엔벨로프 계산
                # 일별 데이터를 월봉(월말 종가) 기준으로 리샘플링
                try:
                    hist_m = hist['Close'].resample('ME').last() # 최신 pandas 버전에 맞춤
                except:
                    hist_m = hist['Close'].resample('M').last()  # 구버전 pandas 호환
                
                # 데이터가 20개월 이상 존재할 경우에만 계산
                if len(hist_m) >= 20:
                    env_20_sma = round(hist_m.tail(20).mean(), 2)
                    env_down_10 = round(env_20_sma * 0.9, 2) # -10% 하단선
                    env_down_20 = round(env_20_sma * 0.8, 2) # -20% 하단선
                    env_down_30 = round(env_20_sma * 0.7, 2) # -30% 하단선
        except: pass
            
        data_list.append({
            "종목코드": code, "종목명": name, "업종": sector, "현재가": current_price,
            "PER": per, "PBR": pbr, "ROE(%)": roe, "PEG": peg, "배당률(%)": div,
            "시가총액(억)": round(marcap, 2),
            "1개월_수익률(%)": ret_1m, "3개월_수익률(%)": ret_3m, "5개월_수익률(%)": ret_5m,
            "월봉_20선": env_20_sma, "엔벨_하단_10": env_down_10, "엔벨_하단_20": env_down_20, "엔벨_하단_30": env_down_30
        })
            
        if (idx + 1) % 100 == 0:
            print(f"수집 진행 상황: {idx + 1}/{total_count}개 완료")
            
    except: continue

if data_list:
    df_master = pd.DataFrame(data_list)
    df_master.to_csv("stock_data.csv", index=False, encoding="utf-8-sig")
    print(f"✅ V4.0 수집 완료: 총 {len(df_master)}개 종목 저장 완료.")
else:
    print("❌ 수집된 데이터가 없습니다."); exit(1)
