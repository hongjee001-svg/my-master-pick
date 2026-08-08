import streamlit as st
from pykrx import stock
import datetime
import pandas as pd
import numpy as np
import google.generativeai as genai

st.set_page_config(page_title="7대 거장 마스터픽 스크리너", layout="wide")

st.title("👑 7대 거장 마스터픽 주식 스크리너 + AI 분석")
st.write("2,000개의 주식 데이터를 실시간 스캔하여 대가의 조건에 맞는 종목을 찾고, 구글 AI가 요약 분석합니다.")

# 1. API 키 입력 및 대가 선택 UI
with st.sidebar:
    st.header("⚙️ 기본 설정")
    api_key = st.text_input("🔑 구글 Gemini API 키를 입력하세요", type="password")
    if api_key:
        genai.configure(api_key=api_key)
        
    st.markdown("---")
    st.header("👨‍🏫 7대 투자 거장 선택")
    strategy = st.radio(
        "어떤 대가의 알고리즘을 사용할까요?",
        (
            "1. 워렌 버핏 (ROE 15% 이상 우량주)",
            "2. 벤자민 그레이엄 (안전마진 딥밸류)",
            "3. 피터 린치 (고성장 배당 가치주)",
            "4. 조엘 그린블라트 (마법공식: 저평가+고효율)",
            "5. 데이비드 드레먼 (역발상 고배당주)",
            "6. 존 네프 (저 PER 가치주)",
            "7. 켄 피셔 (소외된 소형 가치주)"
        )
    )

# 2. 메인 스크리닝 엔진
if st.button("🚀 스크리닝 및 AI 분석 시작"):
    with st.spinner("한국거래소(KRX) 데이터를 스캔하고 수학적 공식을 계산 중입니다..."):
        
        # ⭐️ 에러 수정 부: 가장 최근 영업일을 안정적으로 자동 탐색하는 로직 ⭐️
        today = datetime.datetime.today()
        recent_day = today.strftime("%Y%m%d")
        for i in range(10):
            check_date = (today - datetime.timedelta(days=i)).strftime("%Y%m%d")
            try:
                # 📌 [수정된 부분] _by_date 를 _by_ticker 로 변경!
                chk_df = stock.get_market_fundamental_by_ticker(check_date, market="KOSPI")
                if not chk_df.empty and chk_df['PER'].sum() > 0:
                    recent_day = check_date
                    break
            except Exception:
                continue
        
        # 코스피/코스닥 데이터 로드
        # 📌 [수정된 부분] _by_date 를 _by_ticker 로 변경!
        df_kospi = stock.get_market_fundamental_by_ticker(recent_day, market="KOSPI")
        df_kosdaq = stock.get_market_fundamental_by_ticker(recent_day, market="KOSDAQ")
        df = pd.concat([df_kospi, df_kosdaq])
        
        # 시가총액 데이터 추가 로드
        # 📌 [수정된 부분] _by_date 를 _by_ticker 로 변경!
        cap_kospi = stock.get_market_cap_by_ticker(recent_day, market="KOSPI")
        cap_kosdaq = stock.get_market_cap_by_ticker(recent_day, market="KOSDAQ")
        df_cap = pd.concat([cap_kospi, cap_kosdaq])
        
        # 데이터 병합
        df = df.join(df_cap[['시가총액']])
        df['종목명'] = [stock.get_market_ticker_name(t) for t in df.index]
        df = df.reset_index().rename(columns={'티커': '종목코드'})
        
        # PBR과 PER을 역산하여 ROE(자기자본이익률) 추출: ROE = (PBR / PER) * 100
        df['ROE(%)'] = np.where(df['PER'] > 0, (df['PBR'] / df['PER']) * 100, 0)
        df['시가총액(억)'] = (df['시가총액'] / 100000000).round(0)

        # ==========================================
        # 👑 7명의 대가별 조건식 필터링
        # ==========================================
        if "워렌 버핏" in strategy:
            result = df[(df['PER'] > 0) & (df['PER'] <= 15) & (df['PBR'] > 0) & (df['PBR'] <= 1.5) & (df['ROE(%)'] >= 15)]
        
        elif "벤자민 그레이엄" in strategy:
            result = df[(df['PER'] > 0) & (df['PER'] <= 10) & (df['PBR'] > 0) & (df['PBR'] <= 0.8) & (df['시가총액(억)'] >= 1000)]
            
        elif "피터 린치" in strategy:
            result = df[(df['PER'] > 0) & (df['PER'] <= 12) & (df['ROE(%)'] >= 10) & (df['DIV'] >= 2.0)]
            
        elif "조엘 그린블라트" in strategy:
            valid_df = df[(df['PER'] > 0) & (df['ROE(%)'] > 0)].copy()
            valid_df['PER_순위'] = valid_df['PER'].rank(ascending=True)
            valid_df['ROE_순위'] = valid_df['ROE(%)'].rank(ascending=False)
            valid_df['종합순위'] = valid_df['PER_순위'] + valid_df['ROE_순위']
            result = valid_df.sort_values(by='종합순위').head(20)
            
        elif "데이비드 드레먼" in strategy:
            result = df[(df['PER'] > 0) & (df['PER'] <= 10) & (df['PBR'] <= 1.0) & (df['DIV'] >= 3.0)]
            
        elif "존 네프" in strategy:
            result = df[(df['PER'] >= 6) & (df['PER'] <= 10) & (df['DIV'] >= 2.0) & (df['시가총액(억)'] >= 3000)]
            
        elif "켄 피셔" in strategy:
            result = df[(df['시가총액(억)'] >= 500) & (df['시가총액(억)'] <= 2000) & (df['PBR'] > 0) & (df['PBR'] <= 1.0) & (df['PER'] > 0)]

        # 결과 출력 정리
        st.success(f"🎉 스캔 완료! ({recent_day} 기준 데이터) [{strategy}] 조건에 맞는 종목이 {len(result)}개 발견되었습니다.")
        
        display_df = result[['종목명', '종목코드', 'PER', 'PBR', 'ROE(%)', 'DIV', '시가총액(억)']].copy()
        display_df['ROE(%)'] = display_df['ROE(%)'].round(2)
        display_df['PER'] = display_df['PER'].round(2)
        display_df['PBR'] = display_df['PBR'].round(2)
        
        st.dataframe(display_df.reset_index(drop=True), use_container_width=True)

        # ==========================================
        # 🤖 구글 Gemini AI 리포트 자동 생성기
        # ==========================================
        if len(result) > 0:
            st.markdown("---")
            st.subheader("🤖 구글 Gemini AI 종목 요약 리포트")
            
            if not api_key:
                st.warning("왼쪽 사이드바에 Gemini API 키를 입력하시면, 이 종목들에 대한 AI 투자 분석 리포트가 생성됩니다.")
            else:
                with st.spinner("구글 AI가 종목들을 분석하여 리포트를 작성하고 있습니다..."):
                    try:
                        top_stocks = ", ".join(result['종목명'].head(5).tolist())
                        
                        prompt = f"""
                        당신은 월스트리트 최고의 주식 애널리스트입니다.
                        오늘 한국 시장에서 '{strategy}'의 조건식을 완벽히 통과한 상위 종목들은 다음과 같습니다: {top_stocks}
                        
                        이 종목들이 왜 이 대가의 투자 철학에 부합하는지, 그리고 한국 시장 현재 상황을 고려할 때 투자 시 주의할 점은 무엇인지 3문단으로 전문가처럼 요약해서 한국어로 설명해주세요.
                        """
                        
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(prompt)
                        
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"AI 분석 중 오류가 발생했습니다. API 키가 정확한지 확인해주세요. (에러: {e})")
