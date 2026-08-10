import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
import os

# 페이지 설정 (와이드 모드)
st.set_page_config(
    page_title="7대 거장 마스터픽 스크리너", 
    page_icon="👑", 
    layout="wide"
)

# 메인 타이틀 및 소개
st.title("👑 7대 거장 마스터픽 주식 스크리너 (Momentum Ver.)")
st.markdown("자동 업데이트되는 데이터베이스를 기반으로 **7대 거장의 투자 철학**에 부합하는 종목을 찾고, 최근 1~5개월간의 **수익률 모멘텀**까지 한눈에 확인하세요.")

# ==========================================
# 🔑 URL 쿼리 파라미터 기반 영구 API 키 관리
# ==========================================
if 'api_keys' not in st.session_state:
    query_keys = st.query_params.get_all("keys")
    if query_keys:
        st.session_state['api_keys'] = list(set(query_keys))
    else:
        st.session_state['api_keys'] = []

with st.sidebar:
    st.header("🔑 AI 설정 및 키 관리")
    st.markdown("<small>등록한 키는 새로고침해도 유지됩니다.</small>", unsafe_allow_html=True)
    
    with st.form("key_form", clear_on_submit=True):
        new_key = st.text_input("새 Gemini API 키 입력", type="password")
        submitted = st.form_submit_button("➕ 키 추가하기", use_container_width=True)
        
        if submitted:
            if new_key.strip():
                key_clean = new_key.strip()
                if key_clean not in st.session_state['api_keys']:
                    st.session_state['api_keys'].append(key_clean)
                    st.query_params["keys"] = st.session_state['api_keys']
                    st.success("API 키가 추가되었습니다!")
                    st.rerun()
                else:
                    st.warning("이미 등록되어 있는 API 키입니다.")
            else:
                st.warning("키를 입력해 주세요.")
            
    st.markdown("---")
    
    registered_keys = st.session_state['api_keys']
    st.subheader(f"📋 등록된 키 목록 ({len(registered_keys)}개)")
    
    current_api_key = ""
    
    if registered_keys:
        key_options = {f"Key {i+1} (*****{k[-5:] if len(k) >= 5 else k})": k for i, k in enumerate(registered_keys)}
        
        selected_label = st.selectbox(
            "사용할 키 선택:",
            options=list(key_options.keys())
        )
        current_api_key = key_options[selected_label]
        
        if st.button("🗑️ 선택한 키 삭제", use_container_width=True):
            st.session_state['api_keys'].remove(current_api_key)
            if st.session_state['api_keys']:
                st.query_params["keys"] = st.session_state['api_keys']
            else:
                st.query_params.clear()
            st.success("선택한 API 키가 삭제되었습니다.")
            st.rerun()
            
        genai.configure(api_key=current_api_key)
        st.success("✨ 활성화 완료")
    else:
        st.info("💡 등록된 키가 없습니다. 위 입력창에 본인의 API 키를 추가해 주세요.")

# ==========================================
# 🚀 메인 화면: 스크리닝 실행 버튼
# ==========================================
st.markdown("### 1️⃣ 데이터 스캔")
if st.button("🚀 7대 거장 상위 종목 리스트 불러오기", type="primary", use_container_width=True):
    if not os.path.exists("stock_data.csv"):
        st.error("데이터 파일(stock_data.csv)이 없습니다. 데이터 수집이 완료될 때까지 기다려주세요.")
        st.stop()
        
    with st.spinner("최신 데이터베이스를 분석하여 거장의 조건에 맞는 종목과 모멘텀을 선별 중입니다..."):
        df = pd.read_csv("stock_data.csv")
        
        # [핵심 로직] KRX 기본 데이터에 없는 ROE를 PBR과 PER로 즉석 역산 (ROE = PBR / PER * 100)
        if 'ROE(%)' not in df.columns:
            df['ROE(%)'] = np.where((df['PER'] > 0) & (df['PBR'] > 0), (df['PBR'] / df['PER']) * 100, 0)
            
        # 수익률 및 배당 데이터가 없을 경우를 대비한 안전 장치
        for col in ['1개월_수익률(%)', '3개월_수익률(%)', '5개월_수익률(%)', '현재가', 'DIV', '시가총액(억)']:
            if col not in df.columns:
                df[col] = 0.0
                
        # 7대 거장별 필터링 조건 (상위 30~50개씩 추출)
        strategies = {
            "📈 1. 워렌 버핏": df[(df['PER'] > 0) & (df['PER'] <= 15) & (df['PBR'] > 0) & (df['PBR'] <= 1.5) & (df['ROE(%)'] >= 15)].head(50),
            "🛡️ 2. 벤자민 그레이엄": df[(df['PER'] > 0) & (df['PER'] <= 10) & (df['PBR'] > 0) & (df['PBR'] <= 0.8) & (df['시가총액(억)'] >= 1000)].head(50),
            "🚀 3. 피터 린치": df[(df['PER'] > 0) & (df['PER'] <= 12) & (df['ROE(%)'] >= 10) & (df['DIV'] >= 2.0)].head(50),
            "🧙‍♂️ 4. 조엘 그린블라트": (lambda d: d.assign(
                PER_순위=d[d['PER'] > 0]['PER'].rank(ascending=True),
                ROE_순위=d[d['ROE(%)'] > 0]['ROE(%)'].rank(ascending=False)
            ).assign(종합순위=lambda x: x['PER_순위'] + x['ROE_순위']).sort_values(by='종합순위').head(30))(df),
            "🔄 5. 데이비드 드레먼": df[(df['PER'] > 0) & (df['PER'] <= 10) & (df['PBR'] <= 1.0) & (df['DIV'] >= 3.0)].head(50),
            "📉 6. 존 네프": df[(df['PER'] >= 6) & (df['PER'] <= 10) & (df['DIV'] >= 2.0) & (df['시가총액(억)'] >= 3000)].head(50),
            "💎 7. 켄 피셔": df[(df['시가총액(억)'] >= 500) & (df['시가총액(억)'] <= 2000) & (df['PBR'] > 0) & (df['PBR'] <= 1.0) & (df['PER'] > 0)].head(50)
        }

        # 중복 종목 분석 로직
        stock_matches = {}
        for strat_name, res_df in strategies.items():
            for _, row in res_df.iterrows():
                code = row['종목코드']
                name = row['종목명']
                key = (code, name)
                if key not in stock_matches:
                    stock_matches[key] = []
                stock_matches[key].append(strat_name)
                
        overlap_data = []
        for (code, name), matched_strategies in stock_matches.items():
            if len(matched_strategies) >= 2:
                base_row = strategies[matched_strategies[0]][strategies[matched_strategies[0]]['종목코드'] == code].iloc[0]
                overlap_data.append({
                    '종목명': name,
                    '종목코드': code,
                    '중복 횟수': len(matched_strategies),
                    '선택한 거장들': ", ".join(matched_strategies),
                    '현재가': base_row['현재가'],
                    '1M(%)': base_row['1개월_수익률(%)'],
                    '3M(%)': base_row['3개월_수익률(%)'],
                    '5M(%)': base_row['5개월_수익률(%)'],
                    'PER': base_row['PER'],
                    'PBR': base_row['PBR'],
                    'ROE(%)': base_row['ROE(%)']
                })
                
        overlap_df = pd.DataFrame(overlap_data)
        if not overlap_df.empty:
            overlap_df = overlap_df.sort_values(by='중복 횟수', ascending=False).reset_index(drop=True)
            overlap_df.index = overlap_df.index + 1

        st.session_state['strategies'] = strategies
        st.session_state['overlap_df'] = overlap_df
        st.session_state['loaded'] = True

# ==========================================
# 📊 UI 렌더링
# ==========================================
if st.session_state.get('loaded', False):
    strategies = st.session_state['strategies']
    overlap_df = st.session_state['overlap_df']
    
    st.markdown("---")
    
    st.markdown("### 🔥 [종합 추천] 2명 이상의 거장이 선택한 종목 & 과거 수익률 모멘텀")
    if overlap_df.empty:
        st.info("현재 2개 이상의 거장 조건에 동시에 겹치는 종목이 없습니다.")
    else:
        st.success(f"🎉 총 **{len(overlap_df)}개**의 종목이 교집합으로 추출되었습니다! 우측의 과거 수익률(1M, 3M, 5M)을 통해 추세를 확인하세요.")
        
        # 소수점 정리
        display_overlap = overlap_df.copy()
        display_overlap['ROE(%)'] = display_overlap['ROE(%)'].round(2)
        display_overlap['PER'] = display_overlap['PER'].round(2)
        display_overlap['PBR'] = display_overlap['PBR'].round(2)
        
        # 스트림릿 내장 스타일링을 통해 수익률이 양수면 붉은색, 음수면 푸른색 계열로 표기하면 더 좋지만 
        # 심플함을 위해 기본 표 형태로 깔끔하게 띄워줍니다.
        st.dataframe(display_overlap, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 2️⃣ 🌟 투자 거장별 개별 리스트 및 AI 심층 분석")
    st.markdown("어떤 거장의 투자 종목 리스트를 확인하고 싶으신가요? 아래에서 원하는 거장을 선택해 주세요.")
    
    tab_titles = list(strategies.keys())
    tabs = st.tabs(tab_titles)
    
    for idx, strat_key in enumerate(tab_titles):
        res_df = strategies[strat_key]
        with tabs[idx]:
            st.info(f"🎯 **{strat_key}** 전략 조건에 부합하는 종목 총 **{len(res_df)}개**가 검색되었습니다.")
            
            if res_df.empty:
                st.warning("조건에 만족하는 종목이 없습니다.")
            else:
                display_df = res_df.copy()
                display_df['ROE(%)'] = display_df['ROE(%)'].round(2)
                display_df['PER'] = display_df['PER'].round(2)
                display_df['PBR'] = display_df['PBR'].round(2)
                
                # 보여줄 컬럼 재배치
                cols_to_show = ['종목명', '종목코드', '현재가', '1개월_수익률(%)', '3개월_수익률(%)', 'PER', 'PBR', 'ROE(%)', 'DIV']
                # 실제 데이터프레임에 존재하는 컬럼만 필터링해서 보여주기
                cols_to_show = [c for c in cols_to_show if c in display_df.columns]
                
                display_df = display_df[cols_to_show].reset_index(drop=True)
                display_df.index = display_df.index + 1
                
                st.dataframe(display_df, use_container_width=True)
                
                st.markdown("---")
                st.markdown(f"#### 🤖 AI 종목 심층 분석 리포트")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    selected_stock = st.selectbox(
                        "상세 분석을 원하는 종목을 선택하세요:",
                        options=display_df['종목명'].tolist(),
                        key=f"select_{idx}"
                    )
                with col2:
                    st.write("") 
                    st.write("")
                    ai_button = st.button("✨ AI 리포트 생성", key=f"btn_{idx}", use_container_width=True)
                
                if ai_button:
                    if not current_api_key:
                        st.warning("⚠️ 왼쪽 사이드바에서 사용할 Gemini API 키를 선택해 주세요!")
                    else:
                        with st.spinner(f"구글 AI가 '{selected_stock}' 종목을 정밀 분석 중입니다..."):
                            try:
                                stock_info = display_df[display_df['종목명'] == selected_stock].iloc[0]
                                
                                prompt = f"""
                                당신은 월스트리트 최고의 주식 애널리스트입니다.
                                사용자가 선택한 투자 전략: {strat_key}
                                분석할 종목명: {stock_info['종목명']}
                                
                                주요 재무 지표 및 모멘텀:
                                - PER: {stock_info.get('PER', 'N/A')}
                                - PBR: {stock_info.get('PBR', 'N/A')}
                                - ROE: {stock_info.get('ROE(%)', 'N/A')}%
                                - 배당수익률: {stock_info.get('DIV', 'N/A')}%
                                - 최근 1개월 수익률: {stock_info.get('1개월_수익률(%)', 'N/A')}%
                                - 최근 3개월 수익률: {stock_info.get('3개월_수익률(%)', 'N/A')}%
                                
                                위 데이터를 바탕으로 이 종목이 왜 이 거장의 투자 철학에 부합하는지, 그리고 최근 주가 흐름(모멘텀)을 고려했을 때 현재 시점에서 투자 매력도와 주의해야 할 리스크를 3문단으로 나누어 전문가처럼 친절하게 요약해 주세요.
                                """
                                
                                model = genai.GenerativeModel('gemini-3.6-flash')
                                response = model.generate_content(prompt)
                                
                                st.success(f"[{selected_stock}] AI 분석 완료")
                                st.markdown(response.text)
                                
                            except Exception as e:
                                st.error(f"AI 분석 중 오류가 발생했습니다: {e}")
