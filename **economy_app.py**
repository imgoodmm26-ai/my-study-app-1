import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

st.set_page_config(page_title="경제학 인출기", layout="wide")

# 사이트 내 점수 저장소
if 'session_scores' not in st.session_state: st.session_state.session_scores = {}
if 'state' not in st.session_state: st.session_state.state = "IDLE"

st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .question-text { font-size: 4.3rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 60px 0; }
    .answer-text { font-size: 4.3rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 60px 0; }
    div.stButton > button { width: 100%; height: 140px !important; font-size: 2.8rem !important; border-radius: 40px !important; background-color: #34495e; color: white; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    # 경제학 전용 앱이므로 주소를 'gsheets_url' 하나만 사용합니다.
    df = conn.read(spreadsheet=st.secrets["gsheets_url"], worksheet=0, usecols=[0,1])
    df.columns = ['질문', '정답']
    return df

df = load_data()

# --- 화면 구성 로직 (회계학 앱과 동일) ---
if df is not None:
    for _ in range(5): st.write("")
    if st.session_state.state == "IDLE":
        st.markdown('<p class="question-text">경제학 훈련 준비 완료</p>', unsafe_allow_html=True)
        if st.button("훈련 시작 하기", type="primary"):
            st.session_state.current_index = random.randint(0, len(df)-1)
            st.session_state.state = "QUESTION"; st.rerun()
    # ... (질문/정답 표시 로직 동일)
