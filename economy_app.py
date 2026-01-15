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

# 3. 디자인 설정 (블랙 배경 & 노란 질문 & 초록 정답)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .info-text { font-size: 1.8rem !important; color: #aaaaaa; font-weight: bold; text-align: center; }
    .session-text { font-size: 1.5rem !important; color: #3498db; font-weight: bold; margin-bottom: 20px; text-align: center; }
    .question-text { font-size: 4.3rem !important; font-weight: bold; color: #f1c40f; line-height: 1.4; text-align: center; margin: 40px 0; word-break: keep-all; }
    .answer-text { font-size: 4.3rem !important; font-weight: bold; color: #2ecc71; line-height: 1.4; text-align: center; margin: 40px 0; word-break: keep-all; }
    
    div.stButton > button { 
        width: 100%; height: 120px !important; 
        font-size: 2.5rem !important; font-weight: bold !important; 
        border-radius: 40px !important; background-color: #34495e; 
        color: white; border: 3px solid #555; 
    }
    </style>
    """, unsafe_allow_html=True)

# 4. 데이터 로드 로직 보완
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        # 시트의 첫 번째 탭에서 첫 2개 열을 읽음
        df = conn.read(spreadsheet=url, worksheet=0, usecols=[0, 1])
        if df is not None and not df.empty:
            df.columns = ['질문', '정답']
            return df
        return None
    except Exception as e:
        st.error(f"시트 연결 오류: {e}")
        return None

df = load_data()

# --- 5. 화면 구성 및 에러 방지 ---
if df is not None and len(df) > 0:
    for _ in range(3): st.write("")
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
            score = st.session_state.session_scores.get(str(row['질문']), [0, 0])
            st.markdown('<p class="info-text">지금 바로 떠올려보세요!</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="session-text">📈 성적 - 맞음: {score[0]} / 틀림: {score[1]}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"
                st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("맞음 (O)", type="primary"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][0] += 1
                    st.session_state.current_index = random.randint(0, len(df)-1)
                    st.session_state.state = "QUESTION"
                    st.rerun()
            with c2:
                if st.button("틀림 (X)"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][1] += 1
                    st.session_state.current_index = random.randint(0, len(df)-1)
                    st.session_state.state = "QUESTION"
                    st.rerun()
else:
    st.error("❗ 구글 시트에서 데이터를 불러오지 못했습니다. 시트 안에 내용이 있는지 확인해 주세요.")
