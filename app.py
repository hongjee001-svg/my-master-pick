# ==========================================
# 🔑 영구 저장형 API 키 관리 (사이드바)
# ==========================================
with st.sidebar:
    st.header("🔑 AI 설정")
    
    # URL 파라미터에서 키를 불러옴 (새로고침해도 유지되는 핵심)
    saved_keys = st.query_params.get_all("gemini_key")
    
    new_key = st.text_input("새 Gemini API 키 입력", type="password")
    if st.button("➕ 키 추가"):
        if new_key and new_key not in saved_keys:
            saved_keys.append(new_key)
            st.query_params["gemini_key"] = saved_keys
            st.rerun()

    if saved_keys:
        selected_key = st.selectbox("사용할 키 선택:", options=saved_keys)
        
        # 삭제 기능
        if st.button("🗑️ 선택한 키 삭제"):
            saved_keys.remove(selected_key)
            st.query_params["gemini_key"] = saved_keys
            st.rerun()
            
        genai.configure(api_key=selected_key)
        st.success("✨ 키가 활성화되었습니다.")
    else:
        st.warning("API 키를 추가해주세요.")
