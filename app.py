import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

st.set_page_config(page_title="7대 거장 마스터픽 스크리너", layout="wide")

st.title("👑 7대 거장 마스터픽 주식 스크리너 + AI 분석")
st.write("안전하게 업데이트된 데이터베이스를 기반으로 대가의 조건에 맞는 종목을 1초 만에 발굴합니다.")

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

# 2. 메인 스크리닝 엔진 (CSV 파일 읽기)
if st.button("🚀 스크리닝 및 AI 분석 시작"):
    if not os.path.exists("stock_data.csv"):
        st.error("데이터 파일(stock_data.csv)이 없습니다. 깃허브에 파일을 업로드해주세요.")
        st.stop()
        
    with st.spinner("데이터베이스를 스캔 중입니다..."):
        df = pd.read_csv("stock_data.csv")
        
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

        st.success(f"🎉 스캔 완료! [{strategy}] 조건에 맞는 종목이 {len(result)}개 발견되었습니다.")
        
        if not result.empty:
            display_df = result.copy()
            display_df['ROE(%)'] = display_df['ROE(%)'].round(2)
            display_df['PER'] = display_df['PER'].round(2)
            display_df['PBR'] = display_df['PBR'].round(2)
            
            st.dataframe(display_df.reset_index(drop=True), use_container_width=True)

            # ==========================================
            # 🤖 구글 Gemini AI 리포트
            # ==========================================
            st.markdown("---")
            st.subheader("🤖 구글 Gemini AI 종목 요약 리포트")
            if not api_key:
                st.warning("왼쪽 사이드바에 Gemini API 키를 입력하시면 AI 투자 분석이 생성됩니다.")
            else:
                with st.spinner("구글 AI가 리포트를 작성하고 있습니다..."):
                    try:
                        top_stocks = ", ".join(result['종목명'].head(5).tolist())
                        prompt = f"당신은 월스트리트 최고의 주식 애널리스트입니다.\n'{strategy}' 조건식을 통과한 상위 종목: {top_stocks}\n이 종목들이 대가의 철학에 부합하는 이유와 투자 주의점을 3문단으로 요약해주세요."
                        model = genai.GenerativeModel('gemini-3.6-flash')
                        response = model.generate_content(prompt)
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"AI 분석 오류: {e}")
        else:
            st.warning("조건에 만족하는 종목이 없습니다.")
