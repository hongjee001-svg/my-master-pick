import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
import os

# 1. 페이지 설정 (다크 모드 어울리게 와이드 설정)
st.set_page_config(page_title="7대 거장 마스터픽 스크리너", page_icon="👑", layout="wide")

# ==========================================
# 🎨 커스텀 CSS (대가의 선택 스타일 카드 UI)
# ==========================================
st.markdown("""
<style>
    /* Top 10 카드 스타일 */
    .top10-card {
        background-color: #1E2129; 
        border-radius: 10px; 
        padding: 15px 20px; 
        margin-bottom: 10px; 
        display: flex; 
        align-items: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .top10-rank { font-size: 20px; font-weight: bold; color: #E0E2E7; width: 40px; }
    .top10-icon { font-size: 35px; margin-right: 15px; }
    .top10-info { flex-grow: 1; }
    .top10-name { font-size: 18px; font-weight: bold; color: #FFFFFF; margin-bottom: 2px;}
    .top10-desc { font-size: 12px; color: #8F95A2; }
    .top10-return { font-size: 20px; font-weight: bold; color: #FF4D4F; }
    
    /* 시가총액별 박스 스타일 */
    .cap-box {
        background-color: #1E2129;
        border-radius: 12px;
        padding: 25px 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .cap-icon { font-size: 50px; margin-bottom: 10px; }
    .cap-style { color: #E0E2E7; font-size: 14px; margin-bottom: 5px; }
    .cap-name { color: #FFFFFF; font-size: 20px; font-weight: bold; margin-bottom: 5px; }
    .cap-return { color: #FF4D4F; font-size: 18px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 🔑 API 키 관리 (사이드바)
# ==========================================
if 'api_keys' not in st.session_state:
    st.session_state['api_keys'] = st.query_params.get_all("keys") or []

with st.sidebar:
    st.header("🔑 Gemini AI 설정")
    new_key = st.text_input("새 API 키 입력", type="password")
    if st.button("➕ 키 추가", use_container_width=True) and new_key:
        if new_key not in st.session_state['api_keys']:
            st.session_state['api_keys'].append(new_key)
            st.query_params["keys"] = st.session_state['api_keys']
            st.rerun()
            
    current_api_key = ""
    if st.session_state['api_keys']:
        selected = st.selectbox("사용할 키 선택:", options=st.session_state['api_keys'])
        current_api_key = selected
        genai.configure(api_key=current_api_key)
        st.success("✨ AI 활성화 완료")


# ==========================================
# 🚀 메인 로직: 데이터 스크리닝
# ==========================================
st.title("👑 7대 거장 마스터픽 스크리너")

if not os.path.exists("stock_data.csv"):
    st.info("🔄 데이터를 불러오고 있습니다. 깃허브 액션이 완료될 때까지 잠시만 기다려주세요 (최초 1회 5분 소요).")
    st.stop()

df = pd.read_csv("stock_data.csv")

# ROE 계산 (PBR / PER * 100)
df['ROE(%)'] = np.where((df['PER'] > 0) & (df['PBR'] > 0), (df['PBR'] / df['PER']) * 100, 0)
df = df.fillna(0)

# 7대 거장 필터링 조건 (간소화)
strategies = {
    "👴 워런 버핏": df[(df['PER']>0) & (df['PER']<=15) & (df['PBR']>0) & (df['PBR']<=1.5) & (df['ROE(%)']>=15)],
    "👨‍🦳 피터 린치": df[(df['PER']>0) & (df['PER']<=12) & (df['ROE(%)']>=10)],
    "🧙‍♂️ 조엘 그린블라트": df[(df['PER']>0) & (df['ROE(%)']>0)].assign(rank=lambda x: x['PER'].rank() + x['ROE(%)'].rank(ascending=False)).sort_values('rank'),
    "👨‍💼 벤자민 그레이엄": df[(df['PER']>0) & (df['PER']<=10) & (df['PBR']>0) & (df['PBR']<=0.8) & (df['시가총액(억)']>=1000)],
    "💎 켄 피셔": df[(df['시가총액(억)']>=500) & (df['시가총액(억)']<=2000) & (df['PBR']>0) & (df['PBR']<=1.0)]
}

# 모든 거장 추천 종목을 하나로 합치고, 거장 이름 매핑
master_picks = []
for strat_name, res_df in strategies.items():
    temp = res_df.head(30).copy()
    temp['거장스타일'] = strat_name
    master_picks.append(temp)
all_picks = pd.concat(master_picks).drop_duplicates(subset=['종목코드'], keep='first')

st.markdown("---")

# ==========================================
# 🏆 Section 1: 시가총액별 주도주 (주간/단기 모멘텀 대체)
# ==========================================
st.markdown("### 📊 체급별 주도주 (최근 1개월 기준)")
col1, col2, col3 = st.columns(3)

# 시총 분류 (소형: 1천억 미만 / 중소형: 1천억~5천억 / 대형: 5천억 이상)
small_cap = all_picks[all_picks['시가총액(억)'] < 1000].sort_values('1개월_수익률(%)', ascending=False)
mid_cap = all_picks[(all_picks['시가총액(억)'] >= 1000) & (all_picks['시가총액(억)'] < 5000)].sort_values('1개월_수익률(%)', ascending=False)
large_cap = all_picks[all_picks['시가총액(억)'] >= 5000].sort_values('1개월_수익률(%)', ascending=False)

def draw_cap_card(title, df_cap):
    st.markdown(f"<h4 style='text-align:center; color:#FF9900;'>{title}</h4>", unsafe_allow_html=True)
    if not df_cap.empty:
        top = df_cap.iloc[0]
        icon, style_name = top['거장스타일'].split(' ', 1)
        st.markdown(f"""
        <div class="cap-box">
            <div class="cap-icon">{icon}</div>
            <div class="cap-style">{style_name} 스타일</div>
            <div class="cap-name">{top['종목명']}</div>
            <div class="cap-return">+{top['1개월_수익률(%)']}%</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("조건 부합 종목 없음")

with col1: draw_cap_card("소형주", small_cap)
with col2: draw_cap_card("중소형주", mid_cap)
with col3: draw_cap_card("중대형주", large_cap)

st.markdown("---")

# ==========================================
# 🔥 Section 2: Best 상승률 Top 10 (기간별 탭)
# ==========================================
st.markdown("### 🔥 Best 상승률 Top 10 (거장들의 선택)")
tab1, tab3, tab5 = st.tabs(["1개월", "3개월", "5개월"])

def draw_top10_list(period_col):
    # 수익률 기준 상위 10개 추출
    top10 = all_picks.sort_values(period_col, ascending=False).head(10)
    for idx, row in enumerate(top10.itertuples(), 1):
        icon, style_name = row.거장스타일.split(' ', 1)
        val = getattr(row, period_col.replace('%', '_').replace('(', '').replace(')', '')) # namedtuple 컬럼 접근 보정
        color = "#FF4D4F" if val > 0 else "#4C84FF"
        sign = "+" if val > 0 else ""
        
        st.markdown(f"""
        <div class="top10-card">
            <div class="top10-rank">{idx}</div>
            <div class="top10-icon">{icon}</div>
            <div class="top10-info">
                <div class="top10-name">{row.종목명}</div>
                <div class="top10-desc">{style_name} 스타일</div>
            </div>
            <div class="top10-return" style="color: {color};">{sign}{val}%</div>
        </div>
        """, unsafe_allow_html=True)

with tab1: draw_top10_list("1개월_수익률(%)")
with tab3: draw_top10_list("3개월_수익률(%)")
with tab5: draw_top10_list("5개월_수익률(%)")

st.markdown("---")

# ==========================================
# 🔍 Section 3: 거장별 상세 리스트 & AI 리포트
# ==========================================
st.markdown("### 🔍 거장별 전체 리스트 및 AI 분석")
master_tabs = st.tabs(list(strategies.keys()))

for i, (strat_name, res_df) in enumerate(strategies.items()):
    with master_tabs[i]:
        if res_df.empty:
            st.warning("조건에 만족하는 종목이 없습니다.")
            continue
            
        display_df = res_df[['종목명', '종목코드', '현재가', '1개월_수익률(%)', '3개월_수익률(%)', 'PER', 'PBR', 'ROE(%)']].head(30)
        display_df.index = display_df.index + 1
        st.dataframe(display_df.round(2), use_container_width=True)
        
        col_ai1, col_ai2 = st.columns([2, 1])
        with col_ai1:
            selected_stock = st.selectbox("분석할 종목 선택:", options=display_df['종목명'], key=f"sel_{i}")
        with col_ai2:
            st.write("")
            st.write("")
            if st.button("✨ AI 투자 리포트 생성", key=f"btn_{i}", use_container_width=True):
                if not current_api_key:
                    st.warning("왼쪽 사이드바에서 API 키를 설정해주세요.")
                else:
                    with st.spinner("AI가 재무와 모멘텀을 분석 중입니다..."):
                        info = display_df[display_df['종목명'] == selected_stock].iloc[0]
                        prompt = f"""
                        전략: {strat_name}
                        종목명: {info['종목명']}
                        PER: {info['PER']}, PBR: {info['PBR']}, ROE: {info['ROE(%)']}%
                        1개월 수익률: {info['1개월_수익률(%)']}%, 3개월 수익률: {info['3개월_수익률(%)']}%
                        
                        위 지표를 바탕으로 이 종목이 왜 이 투자 거장의 철학에 부합하는지, 그리고 현재 모멘텀 관점에서 매력도와 리스크를 3문단으로 요약해 줘.
                        """
                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            st.success(f"[{selected_stock}] 분석 완료")
                            st.write(model.generate_content(prompt).text)
                        except Exception as e:
                            st.error(f"오류: {e}")
