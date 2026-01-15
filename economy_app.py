import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="경제학 인출 훈련기", layout="wide")

# 2. 세션 상태 초기화
if 'session_scores' not in st.session_state:
    st.session_state.session_scores = {}
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
if 'current_index' not in st.session_state:
    st.session_state.current_index = None

# 3. 디자인 설정 (굿잡님 스타일)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .question-text { font-size: 4.3rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 40px 0; }
    .answer-text { font-size: 4.3rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 40px 0; }
    div.stButton > button { width: 100%; height: 140px !important; font-size: 2.8rem !important; border-radius: 40px !important; }
    </style>
    """, unsafe_allow_html=True)

# 4. 데이터 로드 (캐시 문제 해결을 위해 ttl=0 설정)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0) # 캐시를 저장하지 않고 매번 새로 불러옵니다.
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        # 시트 이름 '시트1'을 명시적으로 지정하여 정확도를 높입니다.
        df = conn.read(spreadsheet=url, worksheet="시트1", usecols=[0, 1])
        if df is not None and not df.empty:
            df.columns = ['질문', '정답']
            return df
        return None
    except Exception as e:
        return None

df = load_data()

# --- 5. 화면 구성 및 에러 방지 로직 ---
if df is not None and len(df) > 0:
    _, col2, _ = st.columns([1, 10, 1])
    with col2:
        if st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">경제학 인출 훈련 준비 완료</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", type="primary"):
                st.session_state.current_index = random.randint(0, len(df)-1)
                st.session_state.state = "QUESTION"
                st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"
                st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with (c1, c2):
                if c1.button("맞음 (O)", type="primary"):
                    st.session_state.current_index = random.randint(0, len(df)-1)
                    st.session_state.state = "QUESTION"
                    st.rerun()
                if c2.button("틀림 (X)"):
                    st.session_state.current_index = random.randint(0, len(df)-1)
                    st.session_state.state = "QUESTION"
                    st.rerun()
else:
    st.error("❗ 구글 시트 데이터를 읽지 못했습니다. 앱을 새로고침(F5)하거나 시트 공유 설정을 확인해주세요.")
