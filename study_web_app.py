import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 페이지 설정
st.set_page_config(page_title="회계학 인출기", layout="wide")

# 태블릿 최적화 스타일 (심플 버전)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .block-container { padding-top: 2rem !important; }
    .info-text { font-size: 2.2rem !important; color: #aaaaaa; text-align: center; margin-bottom: 20px; font-weight: bold; }
    .question-text { font-size: 5.5rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 100px 0; line-height: 1.4; word-break: keep-all; }
    .answer-text { font-size: 5.5rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 100px 0; line-height: 1.4; word-break: keep-all; }
    div.stButton > button { width: 100%; height: 160px !important; font-size: 3.5rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
    div.stButton > button[kind="primary"] { background-color: #27ae60; border: none; }
    footer {display: none;}
    </style>
    """, unsafe_allow_html=True)

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
    st.session_state.current_index = None
    st.session_state.target_round = 10

# 데이터 로드 (오직 '회계학' 탭만 가져옴)
@st.cache_data(ttl=5)
def load_data():
    try:
        # worksheet 이름을 '회계학'으로 고정
        df = conn.read(spreadsheet=st.secrets["gsheets_url"], worksheet="회계학", usecols=[0,1,2,3])
        df.columns = ['질문', '정답', '정답횟수', '오답횟수']
        df['정답횟수'] = pd.to_numeric(df['정답횟수'], errors='coerce').fillna(0).astype(int)
        df['오답횟수'] = pd.to_numeric(df['오답횟수'], errors='coerce').fillna(0).astype(int)
        return df
    except:
        return pd.DataFrame()

df = load_data()

def get_next_question():
    if df.empty: return None
    total_counts = df['정답횟수'] + df['오답횟수']
    pending_indices = df[total_counts < st.session_state.target_round].index.tolist()
    if not pending_indices:
        st.session_state.target_round += 10
        pending_indices = df.index.tolist()
    
    subset = df.loc[pending_indices]
    weights = [(fail * 3) + 1 for fail in subset['오답횟수']]
    return random.choices(pending_indices, weights=weights, k=1)[0]

# --- 화면 구성 ---
st.title("📖 회계학 집중 훈련")

if df.empty:
    st.error("⚠️ '회계학' 탭을 찾을 수 없거나 데이터가 없습니다. 시트의 탭 이름과 내용을 확인해주세요.")
else:
    if st.session_state.state == "IDLE":
        st.markdown('<p class="question-text">회계학 훈련 준비 완료</p>', unsafe_allow_html=True)
        if st.button("훈련 시작 하기"):
            st.session_state.current_index = get_next_question()
            st.session_state.state = "QUESTION"
            st.rerun()

    elif st.session_state.state == "QUESTION":
        item = df.iloc[st.session_state.current_index]
        curr_total = item["정답횟수"] + item["오답횟수"]
        st.markdown(f'<p class="info-text">회계학 누적 복습: {int(curr_total % 10) + 1}/10회</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="question-text">Q. {item["질문"]}</p>', unsafe_allow_html=True)
        if st.button("정답 확인하기"):
            st.session_state.state = "ANSWER"
            st.rerun()

    elif st.session_state.state == "ANSWER":
        item = df.iloc[st.session_state.current_index]
        st.markdown(f'<p class="answer-text">A. {item["정답"]}</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("맞음 (O)"):
                # 시트 업데이트
                sub_df = conn.read(spreadsheet=st.secrets["gsheets_url"], worksheet="회계학")
                row_idx = sub_df[sub_df.iloc[:, 0] == item["질문"]].index[0]
                sub_df.iloc[row_idx, 2] = int(sub_df.iloc[row_idx, 2]) + 1
                conn.update(spreadsheet=st.secrets["gsheets_url"], worksheet="회계학", data=sub_df)
                
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.cache_data.clear()
                st.rerun()
        with col2:
            if st.button("틀림 (X)"):
                sub_df = conn.read(spreadsheet=st.secrets["gsheets_url"], worksheet="회계학")
                row_idx = sub_df[sub_df.iloc[:, 0] == item["질문"]].index[0]
                sub_df.iloc[row_idx, 3] = int(sub_df.iloc[row_idx, 3]) + 1
                conn.update(spreadsheet=st.secrets["gsheets_url"], worksheet="회계학", data=sub_df)
                
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.cache_data.clear()
                st.rerun()
