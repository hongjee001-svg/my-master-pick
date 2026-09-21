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
    .cap-icon-small { font-size: 32px; margin-right: 12px; }
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

st.title("👑 7대 거장 마스터픽 스크리너 (V3.1 Pro)")

if not os.path.exists("stock_data.csv"):
    st.info("🔄 데이터를 수집 중입니다. 잠시만 기다려주세요.")
    st.stop()

df = pd.read_csv("stock_data.csv")
# 업종 컬럼이 없는 구버전 CSV일 경우 에러 방지용
if '업종' not in df.columns:
    df['업종'] = '기타'
df['업종'] = df['업종'].fillna('기타').astype(str)
df = df.fillna(0)

# 기초 위생 필터: 정상 흑자 기업만 통과
safe_df = df[(df['PER'] > 0) & (df['PBR'] > 0)].copy()

# 1. 벤저민 그레이엄
graham_df = safe_df[(safe_df['PER'] * safe_df['PBR'] <= 22.5) & (safe_df['배당률(%)'] > 0)].copy()
graham_df['그레이엄지수'] = graham_df['PER'] * graham_df['PBR']
graham_picks = graham_df.sort_values('그레이엄지수', ascending=True).head(30)

# 2. 워런 버핏
buffett_picks = safe_df[(safe_df['ROE(%)'] >= 15) & (safe_df['PER'] <= 15) & (safe_df['시가총액(억)'] >= 10000)].sort_values('ROE(%)', ascending=False).head(30)

# 3. 필립 피셔
fisher_picks = safe_df[(safe_df['ROE(%)'] >= 15) & (safe_df['시가총액(억)'] >= 10000) & (safe_df['3개월_수익률(%)'] > 0)].sort_values('3개월_수익률(%)', ascending=False).head(30)

# 4. 존 네프
neff_picks = safe_df[(safe_df['PER'] >= 5) & (safe_df['PER'] <= 10) & (safe_df['배당률(%)'] >= 2.0)].sort_values('배당률(%)', ascending=False).head(30)

# 5. 피터 린치
lynch_picks = safe_df[(safe_df['PEG'] > 0) & (safe_df['PEG'] <= 1.0) & (safe_df['시가총액(억)'] <= 10000)].sort_values('PEG', ascending=True).head(30)

# 6. 조엘 그린블랫
magic_df = safe_df[safe_df['시가총액(억)'] >= 500].copy()
magic_df['마법순위'] = magic_df['PER'].rank(ascending=True) + magic_df['ROE(%)'].rank(ascending=False)
greenblatt_picks = magic_df.sort_values('마법순위', ascending=True).head(30)

# 7. 윌리엄 오닐
oneil_picks = safe_df[(safe_df['ROE(%)'] >= 15) & (safe_df['시가총액(억)'] >= 1000)].sort_values('1개월_수익률(%)', ascending=False).head(30)

strategies_order = [
    ("📚 벤저민 그레이엄", graham_picks),
    ("👴 워런 버핏", buffett_picks),
    ("📈 필립 피셔", fisher_picks),
    ("👨‍🦳 피터 린치", lynch_picks),
    ("🎯 존 네프", neff_picks),
    ("🧙‍♂️ 조엘 그린블랫", greenblatt_picks),
    ("🚀 윌리엄 오닐", oneil_picks)
]

all_picks = pd.concat([res_df.assign(거장스타일=name) for name, res_df in strategies_order]).drop_duplicates(subset=['종목코드'])

col1, col2, col3 = st.columns(3)
def draw_cap(title, cap_df, col):
    with col:
        st.markdown(f"<h4 style='text-align:center'>{title}</h4>", unsafe_allow_html=True)
        if not cap_df.empty:
            top_3 = cap_df.sort_values('1개월_수익률(%)', ascending=False).head(3)
            for idx, row in top_3.iterrows():
                icon, name = row['거장스타일'].split(' ', 1)
                ret_val = row['1개월_수익률(%)']
                color = "#FF4D4F" if ret_val >= 0 else "#4C84FF"
                sign = "+" if ret_val > 0 else ""
                
                # 💡 요약 카드에 업종 명시
                st.markdown(f"""
                <div class='cap-box-small'>
                    <div class='cap-left'>
                        <div class='cap-icon-small'>{icon}</div>
                        <div class='cap-info-small'>
                            <div class='cap-style-small'>{name} | {row['업종']}</div>
                            <div class='cap-name-small'>{row['종목명']}</div>
                        </div>
                    </div>
                    <div class='cap-return-small' style='color:{color};'>{sign}{ret_val}%</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("조건에 맞는 종목 없음")

draw_cap("소형주 (3,000억원 이하)", all_picks[all_picks['시가총액(억)'] <= 3000], col1)
draw_cap("중소형주 (3,000억원~1조원)", all_picks[(all_picks['시가총액(억)'] > 3000) & (all_picks['시가총액(억)'] <= 10000)], col2)
draw_cap("중대형주 (1조원 초과)", all_picks[all_picks['시가총액(억)'] > 10000], col3)

def draw_top10(period_col):
    top_df = all_picks.sort_values(period_col, ascending=False).head(10)
    if top_df.empty:
        st.warning("표시할 종목이 없습니다.")
        return
    for idx, row in enumerate(top_df.iterrows(), 1):
        row_data = row[1]
        icon, name = row_data['거장스타일'].split(' ', 1)
        val = row_data[period_col]
        color = "#FF4D4F" if val >= 0 else "#4C84FF"
        sign = "+" if val > 0 else ""
        # 💡 Top 10 리스트에도 거장 이름 옆에 업종 표시
        st.markdown(f"<div class='top10-card'><div class='top10-rank'>{idx}</div><div class='top10-icon'>{icon}</div><div class='top10-info'><div class='top10-name'>{row_data['종목명']}</div><div class='top10-desc'>{name} | {row_data['업종']}</div></div><div class='top10-return' style='color:{color};'>{sign}{val}%</div></div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("### 🔥 Best 상승률 Top 10")

col_1m, col_3m, col_5m = st.columns(3)

with col_1m:
    st.markdown("<h5 style='text-align:center; color:#E0E2E7;'>1개월 Best</h5>", unsafe_allow_html=True)
    draw_top10("1개월_수익률(%)")

with col_3m:
    st.markdown("<h5 style='text-align:center; color:#E0E2E7;'>3개월 Best</h5>", unsafe_allow_html=True)
    draw_top10("3개월_수익률(%)")

with col_5m:
    st.markdown("<h5 style='text-align:center; color:#E0E2E7;'>5개월 Best</h5>", unsafe_allow_html=True)
    draw_top10("5개월_수익률(%)")

st.markdown("---")
st.markdown("### 🔍 7대 거장별 전체 리스트 및 AI 분석")
strategies_dict = {name: df for name, df in strategies_order}
master_tabs = st.tabs(list(strategies_dict.keys()))

for i, (strat_name, res_df) in enumerate(strategies_dict.items()):
    with master_tabs[i]:
        if res_df.empty:
            st.warning("조건에 만족하는 종목이 없습니다.")
            continue
            
        # 💡 데이터프레임 컬럼에 업종 추가
        display_df = res_df[['종목명', '종목코드', '업종', '현재가', '1개월_수익률(%)', '3개월_수익률(%)', 'PER', 'PBR', 'ROE(%)', 'PEG', '배당률(%)']].head(30)
        display_df.index = range(1, len(display_df) + 1)
        
        st.dataframe(display_df.round(2), width="stretch")
        
        col_ai1, col_ai2 = st.columns([2, 1])
        with col_ai1:
            selected_stock = st.selectbox("분석할 종목 선택:", options=display_df['종목명'], key=f"sel_{i}")
        with col_ai2:
            st.write("")
            st.write("")
            if st.button("✨ AI 투자 리포트 생성", key=f"btn_{i}", width="stretch"):
                if not saved_keys:
                    st.warning("왼쪽 사이드바에서 API 키를 먼저 추가해주세요.")
                else:
                    with st.spinner("Gemini Pro가 심층 분석을 진행 중입니다..."):
                        info = display_df[display_df['종목명'] == selected_stock].iloc[0]
                        # 💡 프롬프트에 업종 정보 주입하여 AI가 산업 특징을 반영하게 유도
                        prompt = f"""
                        전략: {strat_name}
                        종목명: {info['종목명']} (업종: {info['업종']})
                        PER: {info['PER']}, PBR: {info['PBR']}, ROE: {info['ROE(%)']}%, PEG: {info['PEG']}, 배당률: {info['배당률(%)']}%
                        1개월 수익률: {info['1개월_수익률(%)']}%, 3개월 수익률: {info['3개월_수익률(%)']}%
                        
                        위의 상세 퀀트 지표와 해당 산업(업종)의 특징을 바탕으로, 이 종목이 왜 이 투자 거장의 철학에 부합하는지, 그리고 현재 모멘텀 관점에서 매력도와 리스크를 3문단으로 심도 있게 요약해 줘.
                        """
                        try:
                            model = genai.GenerativeModel('gemini-1.5-pro')
                            st.success(f"[{selected_stock}] Gemini Pro 심층 분석 완료")
                            st.write(model.generate_content(prompt).text)
                        except Exception as e:
                            st.error(f"오류가 발생했습니다: {e}")
