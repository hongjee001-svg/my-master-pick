import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

st.set_page_config(page_title="7대 거장 마스터픽 스크리너", layout="wide")

st.title("👑 7대 거장 마스터픽 주식 스크리너")
st.write("안전하게 업데이트된 데이터베이스를 기반으로 7대 거장의 조건에 맞는 상위 종목들을 한눈에 비교하고 상세히 분석합니다.")

# ==========================================
# 🔑 세션 스테이트를 이용한 API 키 영구 저장/삭제 시스템
# ==========================================
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = ""

with st.sidebar:
    st.header("⚙️ API 키 및 설정")
    
    # 사용자가 입력할 수 있는 입력창 (저장된 게 있다면 기본값으로 보여줌)
    input_key = st.text_input(
        "🔑 구글 Gemini API 키 입력", 
        value=st.session_state['api_key'], 
        type="password",
        help="한 번 입력하면 브라우저에 저장되어 다시 입력할 필요가 없습니다."
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 키 저장"):
            if input_key.strip():
                st.session_state['api_key'] = input_key.strip()
                st.success("API 키가 저장되었습니다!")
            else:
                st.warning("키를 입력해주세요.")
    with col2:
        if st.button("🗑️ 키 삭제"):
            st.session_state['api_key'] = ""
            st.success("저장된 키가 삭제되었습니다.")
            st.rerun()
            
    # 등록된 키가 있다면 설정 적용
    current_api_key = st.session_state['api_key']
    if current_api_key:
        genai.configure(api_key=current_api_key)
        st.info("✅ API 키가 활성화되어 있습니다.")
    else:
        st.warning("⚠️ API 키가 등록되지 않았습니다. AI 분석을 위해 키를 저장해주세요.")
        
    st.markdown("---")
    st.info("💡 **사용 가이드**\n1. 상단 버튼을 눌러 종목 리스트를 불러옵니다.\n2. 7대 거장 탭에서 종목들을 확인합니다.\n3. 원하는 종목의 상세보기 및 AI 리포트를 생성하세요!")

# 2. 메인 스크리닝 실행 버튼
if st.button("🚀 7대 거장 상위 종목 리스트 불러오기"):
    if not os.path.exists("stock_data.csv"):
        st.error("데이터 파일(stock_data.csv)이 없습니다. 깃허브에 파일을 업로드해주세요.")
        st.stop()
        
    with st.spinner("데이터베이스를 분석하여 7대 거장의 종목을 추출 중입니다..."):
        df = pd.read_csv("stock_data.csv")
        
        # 7가지 전략별 결과 dict 생성
        strategies = {
            "1. 워렌 버핏 (ROE 15% 이상 우량주)": df[(df['PER'] > 0) & (df['PER'] <= 15) & (df['PBR'] > 0) & (df['PBR'] <= 1.5) & (df['ROE(%)'] >= 15)],
            "2. 벤자민 그레이엄 (안전마진 딥밸류)": df[(df['PER'] > 0) & (df['PER'] <= 10) & (df['PBR'] > 0) & (df['PBR'] <= 0.8) & (df['시가총액(억)'] >= 1000)],
            "3. 피터 린치 (고성장 배당 가치주)": df[(df['PER'] > 0) & (df['PER'] <= 12) & (df['ROE(%)'] >= 10) & (df['DIV'] >= 2.0)],
            "4. 조엘 그린블라트 (마법공식: 저평가+고효율)": (lambda d: d.assign(
                PER_순위=d[d['PER'] > 0]['PER'].rank(ascending=True),
                ROE_순위=d[d['ROE(%)'] > 0]['ROE(%)'].rank(ascending=False)
            ).assign(종합순위=lambda x: x['PER_순위'] + x['ROE_순위']).sort_values(by='종합순위').head(50))(df),
            "5. 데이비드 드레먼 (역발상 고배당주)": df[(df['PER'] > 0) & (df['PER'] <= 10) & (df['PBR'] <= 1.0) & (df['DIV'] >= 3.0)],
            "6. 존 네프 (저 PER 가치주)": df[(df['PER'] >= 6) & (df['PER'] <= 10) & (df['DIV'] >= 2.0) & (df['시가총액(억)'] >= 3000)],
            "7. 켄 피셔 (소외된 소형 가치주)": df[(df['시가총액(억)'] >= 500) & (df['시가총액(억)'] <= 2000) & (df['PBR'] > 0) & (df['PBR'] <= 1.0) & (df['PER'] > 0)]
        }

        # 세션 스테이트에 결과 저장
        st.session_state['strategies'] = strategies
        st.session_state['loaded'] = True

# 데이터가 로드된 경우 탭 화면 구성
if st.session_state.get('loaded', False):
    strategies = st.session_state['strategies']
    
    st.markdown("---")
    st.subheader("📊 7대 투자 거장별 추천 종목 리스트 (상위 최대 50개)")
    
    # 7개의 탭으로 거장별 리스트 분리
    tabs = st.tabs(list(strategies.keys()))
    
    for idx, (strat_name, res_df) in enumerate(strategies.items()):
        with tabs[idx]:
            st.write(f"**[{strat_name}]** 조건에 맞는 종목 총 **{len(res_df)}개**가 검색되었습니다.")
            
            if res_df.empty:
                st.warning("조건에 만족하는 종목이 없습니다.")
            else:
                # 상위 50개만 깔끔하게 자르기
                display_df = res_df.head(50).copy()
                display_df['ROE(%)'] = display_df['ROE(%)'].round(2)
                display_df['PER'] = display_df['PER'].round(2)
                display_df['PBR'] = display_df['PBR'].round(2)
                
                # 1단계: 종목 리스트 표 보여주기
                st.dataframe(display_df[['종목명', '종목코드', 'PER', 'PBR', 'ROE(%)', 'DIV', '시가총액(억)']].reset_index(drop=True), use_container_width=True)
                
                # 2단계: 상세보기 및 AI 리포트 섹션
                st.markdown("---")
                st.markdown(f"#### 🔍 [{strat_name.split(' ')[1]} {strat_name.split(' ')[2]}] 심층 상세보기 및 AI 리포트")
                
                # 해당 탭 안에서 상세보기할 종목 선택
                selected_stock = st.selectbox(
                    "상세 분석을 원하는 종목을 선택하세요:",
                    options=display_df['종목명'].tolist(),
                    key=f"select_{idx}"
                )
                
                if st.button("🤖 이 종목 AI 상세 리포트 생성하기", key=f"btn_{idx}"):
                    if not st.session_state['api_key']:
                        st.warning("⚠️ 왼쪽 사이드바에 구글 Gemini API 키를 저장해주세요!")
                    else:
                        with st.spinner(f"구글 AI가 '{selected_stock}' 종목을 정밀 분석 중입니다..."):
                            try:
                                # 선택한 종목의 데이터 가져오기
                                stock_info = display_df[display_df['종목명'] == selected_stock].iloc[0]
                                
                                prompt = f"""
                                당신은 월스트리트 최고의 주식 애널리스트입니다.
                                사용자가 선택한 투자 전략: {strat_name}
                                분석할 종목명: {stock_info['종목명']} (종목코드: {stock_info['종목코드']})
                                주요 재무 지표: PER {stock_info['PER']}, PBR {stock_info['PBR']}, ROE {stock_info['ROE(%)']}%, 배당수익률 {stock_info['DIV']}%, 시가총액 {stock_info['시가총액(억)']}억원
                                
                                위 데이터를 바탕으로 이 종목이 왜 이 거장의 투자 철학에 부합하는지, 그리고 현재 한국 시장 상황에서 투자할 때 주의해야 할 점을 3문단으로 나누어 전문가처럼 친절하고 명확하게 요약해 주세요.
                                """
                                
                                model = genai.GenerativeModel('gemini-1.5-flash')
                                response = model.generate_content(prompt)
                                
                                st.success(f"✨ [{selected_stock}] AI 분석 리포트 완료")
                                st.info(response.text)
                                
                            except Exception as e:
                                st.error(f"AI 분석 중 오류가 발생했습니다: {e}")
