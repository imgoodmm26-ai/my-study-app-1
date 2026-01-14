import streamlit as st
import pandas as pd
import random
import os

# 페이지 설정 (전체 너비 사용)
st.set_page_config(page_title="인출기", layout="wide")

# 태블릿 최적화 초대형 CSS (제목 제거 및 여백 조정)
st.markdown("""
    <style>
    /* 전체 배경 및 기본 글자색 */
    .stApp { background-color: black; color: white; }
    
    /* 상단 기본 여백 제거 */
    .block-container { padding-top: 2rem !important; }
    
    /* 회독 정보/상태 메시지 크기 (상단에 위치) */
    .info-text { 
        font-size: 2.8rem !important; 
        color: #aaaaaa; 
        text-align: center; 
        margin-bottom: 20px;
        font-weight: bold;
    }
    
    /* 질문 및 정답 텍스트 (화면 중앙에 크게) */
    .question-text { 
        font-size: 5.5rem !important; 
        font-weight: bold; 
        color: #f1c40f; 
        text-align: center; 
        margin: 100px 0; 
        line-height: 1.3;
        word-break: keep-all;
    }
    .answer-text { 
        font-size: 5.5rem !important; 
        font-weight: bold; 
        color: #2ecc71; 
        text-align: center; 
        margin: 100px 0; 
        line-height: 1.3;
        word-break: keep-all;
    }

    /* 버튼 스타일 (터치 최적화 거대 버튼) */
    div.stButton > button {
        width: 100%;
        height: 180px !important;  
        font-size: 4rem !important; 
        font-weight: bold !important;
        border-radius: 40px !important; 
        background-color: #34495e;
        color: white;
        border: 3px solid #555;
    }
    
    /* 맞음/틀림 버튼 색상 및 위치 조정 */
    div.stButton > button[kind="primary"] { background-color: #27ae60; border: none; }
    
    /* 모바일/태블릿용 하단 여백 추가 */
    footer {display: none;}
    #MainMenu {display: none;}
    </style>
    """, unsafe_allow_html=True)

# 엑셀 파일 경로
EXCEL_FILE = "study_list.xlsx"

# 세션 상태 초기화
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
    st.session_state.current_index = None
    st.session_state.target_round = 10

def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        # C(맞음), D(틀림) 열 확보
        while len(df.columns) < 4:
            df[f"열_{len(df.columns)}"] = 0
        df.iloc[:, 2] = pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(0).astype(int)
        df.iloc[:, 3] = pd.to_numeric(df.iloc[:, 3], errors='coerce').fillna(0).astype(int)
        return df
    return None

df = load_data()

def get_next_question():
    # C열+D열 합산으로 회독 계산
    total_counts = df.iloc[:, 2] + df.iloc[:, 3]
    pending_indices = df[total_counts < st.session_state.target_round].index.tolist()
    
    if not pending_indices:
        st.session_state.target_round += 10
        pending_indices = df.index.tolist()
    
    # 오답(D열) 가중치 출제 로직 유지
    subset_df = df.loc[pending_indices]
    weights = [(fail * 3) + 1 for fail in subset_df.iloc[:, 3]]
    return random.choices(pending_indices, weights=weights, k=1)[0]

# --- 화면 구성 시작 ---

if df is not None:
    if st.session_state.state == "IDLE":
        st.markdown(f'<p class="question-text">준비 완료!</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="info-text">목표: 전 문제 {st.session_state.target_round}회 복습</p>', unsafe_allow_html=True)
        if st.button("훈련 시작 하기"):
            st.session_state.current_index = get_next_question()
            st.session_state.state = "QUESTION"
            st.rerun()

    elif st.session_state.state == "QUESTION":
        curr_total = df.iloc[st.session_state.current_index, 2] + df.iloc[st.session_state.current_index, 3]
        st.markdown(f'<p class="info-text">이 문제 누적 복습: {(curr_total % 10) + 1} / 10회</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="question-text">Q. {df.iloc[st.session_state.current_index, 0]}</p>', unsafe_allow_html=True)
        
        if st.button("정답 확인하기"):
            st.session_state.state = "ANSWER"
            st.rerun()

    elif st.session_state.state == "ANSWER":
        st.markdown(f'<p class="info-text">정답을 확인하세요!</p>', unsafe_allow_html=True)
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
    st.error("엑셀 파일(study_list.xlsx)이 깃허브에 없습니다.")
