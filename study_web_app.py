import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 페이지 설정
st.set_page_config(page_title="인출기", layout="wide")

# 태블릿 최적화 CSS (오답 분석표 디자인 추가)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .block-container { padding-top: 2rem !important; }
    .info-text { font-size: 2.5rem !important; color: #aaaaaa; text-align: center; margin-bottom: 10px; font-weight: bold; }
    .error-count-text { font-size: 2rem !important; color: #ff4b4b; text-align: center; margin-bottom: 20px; }
    .question-text { font-size: 5rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 80px 0; line-height: 1.3; word-break: keep-all; }
    .answer-text { font-size: 5rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 80px 0; line-height: 1.3; word-break: keep-all; }
    div.stButton > button { width: 100%; height: 160px !important; font-size: 3.5rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
    div.stButton > button[kind="primary"] { background-color: #27ae60; border: none; }
    footer {display: none;}
    
    /* 오답 분석표 스타일 */
    .stDataFrame { background-color: white; border-radius: 10px; margin-top: 30px; }
    </style>
    """, unsafe_allow_html=True)

# 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

# 세션 상태 초기화
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
    st.session_state.current_index = None
    st.session_state.target_round = 10

# 데이터 로드
def load_data():
    return conn.read(spreadsheet=st.secrets["gsheets_url"], usecols=[0,1,2,3])

df = load_data()

def get_next_question():
    total_counts = df.iloc[:, 2] + df.iloc[:, 3]
    pending_indices = df[total_counts < st.session_state.target_round].index.tolist()
    if not pending_indices:
        st.session_state.target_round += 10
        pending_indices = df.index.tolist()
    
    subset_df = df.loc[pending_indices]
    weights = [(fail * 3) + 1 for fail in subset_df.iloc[:, 3]]
    return random.choices(pending_indices, weights=weights, k=1)[0]

# --- 화면 구성 시작 ---

if df is not None:
    # 1. 메인 학습 영역
    if st.session_state.state == "IDLE":
        st.markdown('<p class="question-text">준비 완료!</p>', unsafe_allow_html=True)
        if st.button("훈련 시작 하기"):
            st.session_state.current_index = get_next_question()
            st.session_state.state = "QUESTION"
            st.rerun()

    elif st.session_state.state == "QUESTION":
        row = df.iloc[st.session_state.current_index]
        st.markdown(f'<p class="info-text">복습 횟수: {int((row[2]+row[3]) % 10) + 1}/10회</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="error-count-text">⚠️ 이 문제 누적 오답: {int(row[3])}회</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="question-text">Q. {row[0]}</p>', unsafe_allow_html=True)
        if st.button("정답 확인하기"):
            st.session_state.state = "ANSWER"
            st.rerun()

    elif st.session_state.state == "ANSWER":
        row = df.iloc[st.session_state.current_index]
        st.markdown(f'<p class="answer-text">A. {row[1]}</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("맞음 (O)"):
                df.iloc[st.session_state.current_index, 2] += 1
                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.rerun()
        with col2:
            if st.button("틀림 (X)"):
                df.iloc[st.session_state.current_index, 3] += 1
                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.rerun()

    # 2. 하단 오답 분석 영역 (굿잡님의 요청 사항)
    st.markdown("---")
    st.subheader("⚠️ 취약 문제 Top 10 (많이 틀린 순)")
    
    # 엑셀의 A열(질문)과 D열(틀림)만 추출하여 정렬
    # (제목은 시트의 첫 번째 줄에 따라 '질문', '틀림' 등으로 자동 인식됩니다)
    error_analysis = df.copy()
    error_analysis.columns = ['질문', '정답', '맞음', '틀림'] # 열 이름 강제 지정
    top_errors = error_analysis[['질문', '틀림']].sort_values(by='틀림', ascending=False).head(10)
    
    st.table(top_errors) # 태블릿에서 보기 편하도록 깔끔한 표 형태로 출력

else:
    st.error("데이터를 불러올 수 없습니다.")
