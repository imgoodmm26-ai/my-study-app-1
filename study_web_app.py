import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="인출 훈련기", layout="wide")

# 2. 사이트 내 카운팅 저장소 초기화
if 'local_stats' not in st.session_state:
    st.session_state.local_stats = {} # {질문: {'O': 0, 'X': 0}}
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
if 'current_index' not in st.session_state:
    st.session_state.current_index = None

# 3. 태블릿 최적화 디자인 (글씨 크기 2포인트 축소 적용)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .block-container { padding-top: 1rem !important; }
    
    /* 상단 정보 텍스트 (기존 2.2rem -> 1.8rem) */
    .info-text { font-size: 1.8rem !important; color: #aaaaaa; text-align: center; margin-bottom: 20px; font-weight: bold; }
    
    /* 질문 텍스트 (기존 5.5rem -> 4.8rem) */
    .question-text { font-size: 4.8rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 80px 0; line-height: 1.4; word-break: keep-all; }
    
    /* 정답 텍스트 (기존 5.5rem -> 4.8rem) */
    .answer-text { font-size: 4.8rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 80px 0; line-height: 1.4; word-break: keep-all; }
    
    /* 버튼 글자 크기 (기존 3.5rem -> 3.0rem) */
    div.stButton > button { width: 100%; height: 160px !important; font-size: 3.0rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
    div.stButton > button[kind="primary"] { background-color: #27ae60; border: none; }
    footer {display: none;}
    </style>
    """, unsafe_allow_html=True)

# 4. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    try:
        df = conn.read(spreadsheet=st.secrets["gsheets_url"], worksheet="회계학", usecols=[0,1])
        df.columns = ['질문', '정답']
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data()

def get_next_question():
    if df.empty: return None
    return random.randint(0, len(df)-1)

# --- 5. 화면 구성 ---

if df.empty:
    st.error("⚠️ 시트 데이터를 불러올 수 없습니다. 주소와 탭 이름(회계학)을 확인해주세요.")
else:
    if st.session_state.state == "IDLE":
        st.markdown('<p class="question-text">인출 훈련 준비 완료</p>', unsafe_allow_html=True)
        if st.button("훈련 시작 하기"):
            st.session_state.current_index = get_next_question()
            st.session_state.state = "QUESTION"
            st.rerun()

    elif st.session_state.state == "QUESTION":
        item = df.iloc[st.session_state.current_index]
        q_text = item["질문"]
        score = st.session_state.local_stats.get(q_text, {'O': 0, 'X': 0})
        st.markdown(f'<p class="info-text">현재 세션 성적 - 맞음: {score["O"]} / 틀림: {score["X"]}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="question-text">Q. {q_text}</p>', unsafe_allow_html=True)
        if st.button("정답 확인하기"):
            st.session_state.state = "ANSWER"
            st.rerun()

    elif st.session_state.state == "ANSWER":
        item = df.iloc[st.session_state.current_index]
        st.markdown(f'<p class="answer-text">A. {item["정답"]}</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("맞음 (O)"):
                q_text = item["질문"]
                if q_text not in st.session_state.local_stats: st.session_state.local_stats[q_text] = {'O': 0, 'X': 0}
                st.session_state.local_stats[q_text]['O'] += 1
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.rerun()
        with col2:
            if st.button("틀림 (X)"):
                q_text = item["질문"]
                if q_text not in st.session_state.local_stats: st.session_state.local_stats[q_text] = {'O': 0, 'X': 0}
                st.session_state.local_stats[q_text]['X'] += 1
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.rerun()
