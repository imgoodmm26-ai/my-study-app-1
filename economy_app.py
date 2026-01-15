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

# 3. 디자인 설정 (디자인은 그대로 유지)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .info-text { font-size: 1.8rem !important; color: #aaaaaa; font-weight: bold; text-align: center; }
    .question-text { font-size: 4.3rem !important; font-weight: bold; color: #f1c40f; line-height: 1.4; text-align: center; margin: 40px 0; word-break: keep-all; }
    .answer-text { font-size: 4.3rem !important; font-weight: bold; color: #2ecc71; line-height: 1.4; text-align: center; margin: 40px 0; word-break: keep-all; }
    div.stButton > button { width: 100%; height: 140px !important; font-size: 2.8rem !important; border-radius: 40px !important; background-color: #34495e; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 4. 데이터 로드 로직 (강화된 버전)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=1) # 문제를 고치기 위해 TTL을 1초로 줄여 즉시 반영되게 합니다.
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        # 시트를 읽어온 뒤 데이터가 있는지 확인
        df = conn.read(spreadsheet=url, worksheet=0) 
        if df is not None and not df.empty:
            df = df.iloc[:, :2] # 첫 2개 컬럼만 선택
            df.columns = ['질문', '정답']
            return df
        return pd.DataFrame(columns=['질문', '정답'])
    except Exception as e:
        return pd.DataFrame(columns=['질문', '정답'])

df = load_data()

# --- 5. 화면 구성 (ValueError 방지 핵심 로직) ---
if not df.empty: # 데이터가 1개 이상 있을 때만 시작
    for _ in range(4): st.write("")
    _, col2, _ = st.columns([1, 10, 1])

    with col2:
        if st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">준비되셨나요, 굿잡님?<br>인출 훈련 시작!</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", type="primary"):
                st.session_state.current_index = random.randint(0, len(df)-1)
                st.session_state.state = "QUESTION"
                st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            st.markdown('<p class="info-text">지금 바로 떠올려보세요!</p>', unsafe_allow_html=True)
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
    st.error("❗ 구글 시트에서 데이터를 불러오지 못했습니다. 시트 내용을 다시 확인해 주세요.")
    if st.button("데이터 다시 불러오기"):
        st.cache_data.clear() # 캐시 강제 삭제
        st.rerun()
