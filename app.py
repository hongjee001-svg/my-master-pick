import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from streamlit_localstorage import LocalStorage

# 페이지 설정 (와이드 모드)
st.set_page_config(
    page_title="7대 거장 마스터픽 스크리너", 
    page_icon="👑", 
    layout="wide"
)

# 브라우저 로컬 스토리지 인스턴스 생성
localS = LocalStorage()

# 메인 타이틀 및 소개
st.title("👑 7대 거장 마스터픽 주식 스크리너")
st.markdown("안전하게 업데이트된 데이터베이스를 기반으로 **7대 거장의 투자 철학**에 부합하는 상위 종목을 빠르고 편하게 확인하세요.")

# ==========================================
# 🔑 브라우저 로컬 저장소 기반 영구 API 키 관리 (코드 내 강제 키 없음)
# ==========================================
saved_keys = localS.getItem("user_api_keys")
if saved_keys is not None and isinstance(saved_keys, list):
    st.session_state['api_keys'] = saved_keys
else:
    if 'api_keys' not in st.session_state:
        st.session_state['api_keys'] = []

with st.sidebar:
    st.header("🔑 AI 설정 및 키 관리")
    st.markdown("<small>추가한 키는 새로고침해도 브라우저에 유지됩니다.</small>", unsafe_allow_html=True)
    
    with st.form("key_form", clear_on_submit=True):
        new_key = st.text_input("새 Gemini API 키 입력", type="password")
        submitted = st.form_submit_button("➕ 키 추가하기", use_container_width=True)
        
        if submitted:
            if new_key.strip():
                key_clean = new_key.strip()
                if key_clean not in st.session_state['api_keys']:
                    st.session_state['api_keys'].append(key_clean)
                    # 브라우저 로컬 스토리지에 영구 저장
                    localS.setItem("user_api_keys", st.session_state['api_keys'])
                    st.success("API 키가 추가되었습니다!")
                    st.rerun()
                else:
                    st.warning("이미 등록된 API 키입니다.")
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
        
        # 삭제 버튼 (누르면 목록 및 브라우저 저장소에서 영구 삭제됨)
        if st.button("🗑️ 선택한 키 삭제", use_container_width=True):
            st.session_state['api_keys'].remove(current_api_key)
            localS.setItem("user_api_keys", st.session_state['api_keys'])
            st.success("선택한 API 키가 삭제되었습니다.")
            st.rerun()
            
        genai.configure(api_key=current_api_key)
        st.success("✨ 활성화 완료")
    else:
        st.info("💡 등록된 키가 없습니다. 위 입력창에 본인의 API 키를 추가해 주세요.")
        
    st.markdown("---")
    st.markdown("### 📌 이용 가이드")
    st.markdown("1. 상단의 **종목 불러오기** 버튼을 누릅니다.")
    st.markdown("2. 첫 화면에서 **거장들이 공통으로 선택한 중복 종목**을 먼저 확인하세요!")
    st.markdown("3. 대가별 탭을 눌러 상세 리스트를 확인하고 **AI 심층 리포트**를 생성해보세요.")

# ==========================================
# 🚀 메인 화면: 스크리닝 실행 버튼
# ==========================================
st.markdown("### 1️⃣ 데이터 스캔")
if st.button("🚀 7대 거장 상위 종목 리스트 불러오기", type="primary", use_container_width=True):
    if not os.path.exists("stock_data.csv"):
        st.error("데이터 파일(stock_data.csv)이 없습니다. 깃허브에 최신 데이터를 업로드해주세요.")
        st.stop()
        
    with st.spinner("데이터베이스를 분석하여 7대 거장의 조건에 맞는 종목을 선별 중입니다..."):
        df = pd.read_csv("stock_data.csv")
        
        strategies = {
            "📈 1. 워렌 버핏": df[(df['PER'] > 0) & (df['PER'] <= 15) & (df['PBR'] > 0) & (df['PBR'] <= 1.5) & (df['ROE(%)'] >= 15)].head(50),
            "🛡️ 2. 벤자민 그레이엄": df[(df['PER'] > 0) & (df['PER'] <= 10) & (df['PBR'] > 0) & (df['PBR'] <= 0.8) & (df['시가총액(억)'] >= 1000)].head(50),
            "🚀 3. 피터 린치": df[(df['PER'] > 0) & (df['PER'] <= 12) & (df['ROE(%)'] >= 10) & (df['DIV'] >= 2.0)].head(50),
            "🧙‍♂️ 4. 조엘 그린블라트": (lambda d: d.assign(
                PER_순위=d[d['PER'] > 0]['PER'].rank(ascending=True),
                ROE_순위=d[d['ROE(%)'] > 0]['ROE(%)'].rank(ascending=False)
            ).assign(종합순위=lambda x: x['PER_순위'] + x['ROE_순위']).sort_values(by='종합순위').head(50))(df),
            "🔄 5. 데이비드 드레먼": df[(df['PER'] > 0) & (df['PER'] <= 10) & (df['PBR'] <= 1.0) & (df['DIV'] >= 3.0)].head(50),
            "📉 6. 존 네프": df[(df['PER'] >= 6) & (df['PER'] <= 10) & (df['DIV'] >= 2.0) & (df['시가총액(억)'] >= 3000)].head(50),
            "💎 7. 켄 피셔": df[(df['시가총액(억)'] >= 500) & (df['시가총액(억)'] <= 2000) & (df['PBR'] > 0) & (df['PBR'] <= 1.0) & (df['PER'] > 0)].head(50)
        }

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
                    'PER': base_row['PER'],
                    'PBR': base_row['PBR'],
                    'ROE(%)': base_row['ROE(%)'],
                    'DIV': base_row['DIV'],
                    '시가총액(억)': base_row['시가총액(억)']
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
    
    st.markdown("### 🔥 [종합 추천] 2명 이상의 거장이 동시에 선택한 '중복 집중 공략' 종목")
    if overlap_df.empty:
        st.info("현재 2개 이상의 거장 조건에 동시에 겹치는 종목이 없습니다.")
    else:
        st.success(f"🎉 총 **{len(overlap_df)}개**의 종목이 여러 거장의 선택을 동시에 받았습니다! 공통으로 겹치는 종목들을 확인해 보세요.")
        st.dataframe(
            overlap_df[['종목명', '종목코드', '중복 횟수', '선택한 거장들', 'PER', 'PBR', 'ROE(%)', 'DIV', '시가총액(억)']],
            use_container_width=True
        )
    
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
                
                display_df = display_df.reset_index(drop=True)
                display_df.index = display_df.index + 1
                
                st.dataframe(
                    display_df[['종목명', '종목코드', 'PER', 'PBR', 'ROE(%)', 'DIV', '시가총액(억)']], 
                    use_container_width=True
                )
                
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
                                분석할 종목명: {stock_info['종목명']} (종목코드: {stock_info['종목코드']})
                                주요 재무 지표: PER {stock_info['PER']}, PBR {stock_info['PBR']}, ROE {stock_info['ROE(%)']}%, 배당수익률 {stock_info['DIV']}%, 시가총액 {stock_info['시가총액(억)']}억원
                                
                                위 데이터를 바탕으로 이 종목이 왜 이 거장의 투자 철학에 부합하는지, 그리고 현재 한국 시장 상황에서 투자할 때 주의해야 할 점을 3문단으로 나누어 전문가처럼 친절하고 명확하게 요약해 주세요.
                                """
                                
                                model = genai.GenerativeModel('gemini-3.6-flash')
                                response = model.generate_content(prompt)
                                
                                st.success(f"[{selected_stock}] AI 분석 완료")
                                st.markdown(response.text)
                                
                            except Exception as e:
                                st.error(f"AI 분석 중 오류가 발생했습니다: {e}")
