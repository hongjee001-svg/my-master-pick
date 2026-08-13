import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
import os

st.set_page_config(page_title="7대 거장 마스터픽 스크리너", page_icon="👑", layout="wide")

st.markdown("""
<style>
    .top10-card { background-color: #1E2129; border-radius: 10px; padding: 15px 20px; margin-bottom: 10px; display: flex; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .top10-rank { font-size: 20px; font-weight: bold; color: #E0E2E7; width: 40px; }
    .top10-icon { font-size: 35px; margin-right: 15px; }
    .top10-info { flex-grow: 1; }
    .top10-name { font-size: 18px; font-weight: bold; color: #FFFFFF; margin-bottom: 2px;}
    .top10-desc { font-size: 12px; color: #8F95A2; }
    .top10-return { font-size: 20px; font-weight: bold; color: #FF4D4F; }
    .cap-box { background-color: #1E2129; border-radius: 12px; padding: 25px 15px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .cap-icon { font-size: 50px; margin-bottom: 10px; }
    .cap-style { color: #E0E2E7; font-size: 14px; margin-bottom: 5px; }
    .cap-name { color: #FFFFFF; font-size: 20px; font-weight: bold; margin-bottom: 5px; }
    .cap-return { color: #FF4D4F; font-size: 18px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# API 키 설정
if 'api_keys' not in st.session_state: st.session_state['api_keys'] = []
with st.sidebar:
    st.header("🔑 AI 설정")
    new_key = st.text_input("Gemini API 키 입력", type="password")
    if st.button("➕ 키 추가") and new_key:
        st.session_state['api_keys'].append(new_key)
        st.rerun()
    current_api_key = st.selectbox("사용할 키:", options=st.session_state['api_keys']) if st.session_state['api_keys'] else ""
    if current_api_key: genai.configure(api_key=current_api_key)

st.title("👑 7대 거장 마스터픽 스크리너")

if not os.path.exists("stock_data.csv"):
    st.info("🔄 데이터를 수집 중입니다. 잠시만 기다려주세요.")
    st.stop()

df = pd.read_csv("stock_data.csv")
df['ROE(%)'] = np.where((df['PER'] > 0) & (df['PBR'] > 0), (df['PBR'] / df['PER']) * 100, 0)
df = df.fillna(0)

strategies = {
    "👴 워런 버핏": df[(df['PER']>0) & (df['PER']<=15) & (df['ROE(%)']>=15)],
    "👨‍🦳 피터 린치": df[(df['PER']>0) & (df['ROE(%)']>=10)],
    "💎 켄 피셔": df[(df['시가총액(억)']>=500) & (df['PBR']<=1.0)]
}

all_picks = pd.concat([res.assign(거장스타일=name) for name, res in strategies.items()]).drop_duplicates(subset=['종목코드'])

col1, col2, col3 = st.columns(3)
def draw_cap(title, cap_df, col):
    with col:
        st.markdown(f"<h4 style='text-align:center'>{title}</h4>", unsafe_allow_html=True)
        if not cap_df.empty:
            top = cap_df.sort_values('1개월_수익률(%)', ascending=False).iloc[0]
            icon, name = top['거장스타일'].split(' ', 1)
            st.markdown(f"<div class='cap-box'><div class='cap-icon'>{icon}</div><div class='cap-style'>{name}</div><div class='cap-name'>{top['종목명']}</div><div class='cap-return'>+{top['1개월_수익률(%)']}%</div></div>", unsafe_allow_html=True)

draw_cap("소형주", all_picks[all_picks['시가총액(억)'] < 1000], col1)
draw_cap("중소형주", all_picks[(all_picks['시가총액(억)'] >= 1000) & (all_picks['시가총액(억)'] < 5000)], col2)
draw_cap("중대형주", all_picks[all_picks['시가총액(억)'] >= 5000], col3)

def draw_top10(period_col):
    for idx, row in enumerate(all_picks.sort_values(period_col, ascending=False).head(10).iterrows(), 1):
        row_data = row[1]
        icon, name = row_data['거장스타일'].split(' ', 1)
        val = row_data[period_col]
        st.markdown(f"<div class='top10-card'><div class='top10-rank'>{idx}</div><div class='top10-icon'>{icon}</div><div class='top10-info'><div class='top10-name'>{row_data['종목명']}</div><div class='top10-desc'>{name}</div></div><div class='top10-return'>{val}%</div></div>", unsafe_allow_html=True)

tab1, tab3, tab5 = st.tabs(["1개월", "3개월", "5개월"])
with tab1: draw_top10("1개월_수익률(%)")
with tab3: draw_top10("3개월_수익률(%)")
with tab5: draw_top10("5개월_수익률(%)")
