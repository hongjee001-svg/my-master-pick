def draw_top10_list(period_col):
    # 수익률 기준 상위 10개 추출
    top10 = all_picks.sort_values(period_col, ascending=False).head(10)
    idx = 1
    for _, row in top10.iterrows():
        icon, style_name = row['거장스타일'].split(' ', 1)
        val = row[period_col]
        color = "#FF4D4F" if val > 0 else "#4C84FF"
        sign = "+" if val > 0 else ""
        
        st.markdown(f"""
        <div class="top10-card">
            <div class="top10-rank">{idx}</div>
            <div class="top10-icon">{icon}</div>
            <div class="top10-info">
                <div class="top10-name">{row['종목명']}</div>
                <div class="top10-desc">{style_name} 스타일</div>
            </div>
            <div class="top10-return" style="color: {color};">{sign}{val}%</div>
        </div>
        """, unsafe_allow_html=True)
        idx += 1
