import streamlit as st
import pandas as pd
import random
import os

# 페이지 설정
st.set_page_config(page_title="굿잡님의 인출 훈련기", layout="centered")

# CSS로 배경색 및 폰트 크기 조절 (태블릿 가독성 최적화)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .stButton>button { width: 100%; height: 3em; font-size: 1.5em !important; }
    h1, h2, h3 { color: white !important; }
    .question-text { font-size: 2.5em; font-weight: bold; color: #f1c40f; text-align: center; margin: 50px 0; }
    .answer-text { font-size: 2.5em; font-weight: bold; color: #2ecc71; text-align: center; margin: 50px 0; }
    </style>
    """, unsafe_allow_html=True)

# 데이터 로드 및 세션 상태 초기화
EXCEL_FILE = "study_list.xlsx"

if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
    st.session_state.current_index = None
    st.session_state.target_round = 10

def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        while len(df.columns) < 4:
            df[f"열_{len(df.columns)}"] = 0
        df.iloc[:, 2] = pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(0).astype(int)
        df.iloc[:, 3] = pd.to_numeric(df.iloc[:, 3], errors='coerce').fillna(0).astype(int)
        return df
    return None

df = load_data()

def get_next_question():
    total_counts = df.iloc[:, 2] + df.iloc[:, 3]
    pending_indices = df[total_counts < st.session_state.target_round].index.tolist()
    
    if not pending_indices:
        st.session_state.target_round += 10
        pending_indices = df.index.tolist()
        st.warning(f"🎉 모든 문제 완료! 다음 목표 {st.session_state.target_round}회로 넘어갑니다.")

    subset_df = df.loc[pending_indices]
    weights = [(fail * 3) + 1 for fail in subset_df.iloc[:, 3]]
    return random.choices(pending_indices, weights=weights, k=1)[0]

# UI 구성
st.title("🛡️ 고난도 인출 훈련기")

if df is not None:
    if st.session_state.state == "IDLE":
        if st.button("훈련 시작 (Space/Click)"):
            st.session_state.current_index = get_next_question()
            st.session_state.state = "QUESTION"
            st.rerun()

    elif st.session_state.state == "QUESTION":
        curr_total = df.iloc[st.session_state.current_index, 2] + df.iloc[st.session_state.current_index, 3]
        st.subheader(f"회독 정보: {(curr_total % 10) + 1} / 10회")
        st.markdown(f'<p class="question-text">Q. {df.iloc[st.session_state.current_index, 0]}</p>', unsafe_allow_html=True)
        
        if st.button("머릿속으로 정답 인출 후 클릭!"):
            st.session_state.state = "ANSWER"
            st.rerun()

    elif st.session_state.state == "ANSWER":
        st.markdown(f'<p class="answer-text">A. {df.iloc[st.session_state.current_index, 1]}</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("맞음 (O)"):
                df.iloc[st.session_state.current_index, 2] += 1
                df.to_excel(EXCEL_FILE, index=False)
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.rerun()
        with col2:
            if st.button("틀림 (X)"):
                df.iloc[st.session_state.current_index, 3] += 1
                df.to_excel(EXCEL_FILE, index=False)
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.rerun()
else:
    st.error("엑셀 파일을 찾을 수 없습니다.")