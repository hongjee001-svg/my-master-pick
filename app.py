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
    
    .cap-box-small { background-color: #1E2129; border-radius: 12px; padding: 15px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .cap-left { display: flex; align-items: center; }
    .cap-icon-small { font-size: 32px; margin-right: 12px; letter-spacing: -5px; }
    .cap-info-small { text-align: left; }
    .cap-style-small { color: #8F95A2; font-size: 11px; margin-bottom: 2px; }
    .cap-name-small { color: #FFFFFF; font-size: 16px; font-weight: bold; }
    .cap-return-small { font-size: 16px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 AI 설정")
    saved_keys = st.query_params.get_all("gemini_key")
    new_key = st.text_input("새 Gemini API 키 입력", type="password")
    if st.button("➕ 키 추가"):
        if new_key and new_key not in saved_keys:
            saved_keys.append(new_key)
            st.query_params["gemini_key"] = saved_keys
            st.rerun()

    if saved_keys:
        selected_key = st.selectbox("사용할 키 선택:", options=saved_keys)
        if st.button("🗑️ 선택한 키 삭제"):
            saved_keys.remove(selected_key)
            st.query_params["gemini_key"] = saved_keys
            st.rerun()
        genai.configure(api_key=selected_key)
        st.success("✨ 키가 활성화되었습니다.")
    else:
        st.warning("API 키를 추가해주세요.")

st.title("👑 7대 거장 마스터픽 스크리너 (V5.3 Pro)")

if not os.path.exists("stock_data.csv"):
    st.info("🔄 데이터를 수집 중입니다. 잠시만 기다려주세요.")
    st.stop()

df = pd.read_csv("stock_data.csv")
if '업종' not in df.columns: df['업종'] = '기타'
if '엔벨_하단_10' not in df.columns: df['엔벨_하단_10'] = 0.0
if '엔벨_하단_20' not in df.columns: df['엔벨_하단_20'] = 0.0
if '일봉_20선' not in df.columns: df['일봉_20선'] = df.get('월봉_20선', 0.0)

df['업종'] = df['업종'].fillna('기타').astype(str)
df = df.fillna(0)

safe_df = df[(df['PER'] > 0) & (df['PBR'] > 0)].copy()

graham_df = safe_df[(safe_df['PER'] * safe_df['PBR'] <= 22.5)].copy()
graham_df['그레이엄지수'] = graham_df['PER'] * graham_df['PBR']
graham_picks = graham_df.sort_values('그레이엄지수', ascending=True).head(30)

buffett_picks = safe_df[(safe_df['ROE(%)'] >= 10) & (safe_df['PER'] <= 20) & (safe_df['시가총액(억)'] >= 10000)].sort_values('ROE(%)', ascending=False).head(30)
fisher_picks = safe_df[(safe_df['ROE(%)'] >= 10) & (safe_df['시가총액(억)'] >= 10000)].sort_values('3개월_수익률(%)', ascending=False).head(30)
neff_picks = safe_df[(safe_df['PER'] >= 5) & (safe_df['PER'] <= 15)].sort_values('배당률(%)', ascending=False).head(30)
lynch_picks = safe_df[(safe_df['PEG'] > 0) & (safe_df['PEG'] <= 1.0) & (safe_df['시가총액(억)'] <= 10000)].sort_values('PEG', ascending=True).head(30)

magic_df = safe_df[safe_df['시가총액(억)'] >= 500].copy()
magic_df['마법순위'] = magic_df['PER'].rank(ascending=True) + magic_df['ROE(%)'].rank(ascending=False)
greenblatt_picks = magic_df.sort_values('마법순위', ascending=True).head(30)

oneil_picks = safe_df[(safe_df['ROE(%)'] >= 10) & (safe_df['시가총액(억)'] >= 1000)].sort_values('1개월_수익률(%)', ascending=False).head(
