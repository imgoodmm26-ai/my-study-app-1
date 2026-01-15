import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="인출 훈련기", layout="wide")

# 2. 세션 상태 초기화
if 'session_scores' not in st.session_state:
    st.session_state.session_scores = {}
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
if 'current_index' not in st.session_state:
    st.session_state.current_index = None

# 3. 디자인 설정 (글씨 크기 2포인트 축소 반영)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .info-text { font-size: 1.8rem !important; color: #aaaaaa; font-weight: bold; text-align: center; }
    .session-text { font-size: 1.5rem !important; color: #3498db; font-weight: bold; margin-bottom: 20px; text-align: center; }
    .question-text { font-size: 4.3rem !important; font-weight: bold; color: #f1c40f; line-height: 1.4; text-align: center; margin-bottom: 30px; }
    .answer-text { font-size: 4.3rem !important; font-weight: bold; color: #2ecc71; line-height: 1.4; text-align: center; margin-bottom: 30px; }
    div.stButton > button { width: 100%; height: 140px !important; font-size: 2.8rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
    div.stButton > button[kind="primary"] { background-color: #27ae60; border: none; }
    footer {display: none;}
    </style>
    """, unsafe_allow_html=True)

# 4. 데이터 로드 (에러 원인 추적 기능 추가)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        # Secrets에서 주소를 읽어옵니다.
        target_url = st.secrets["gsheets_url"]
        df = conn.read(spreadsheet=target_url, worksheet="회계학", usecols=[0,1])
        df.columns = ['질문', '정답']
        return df
    except Exception as e:
        # 어디가 문제인지 화면에 직접 표시합니다.
        st.error(f"상세 에러 내용: {e}")
        return None

df = load_data()

# --- 5. 메인 화면 구성 ---
if df is not None:
    for _ in range(5): st.write("") # 상단 여백
    _, col2, _ = st.columns([1, 10, 1])

    with col2:
        if st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">인출 훈련 준비 완료</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", kind="primary"):
                st.session_state.current_index = random.randint(0, len(df)-1)
                st.session_state.state = "QUESTION"
                st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            score = st.session_state.session_scores.get(row['질문'], [0, 0])
            st.markdown('<p class="info-text">인출 훈련 중</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="session-text">맞음: {score[0]} / 틀림: {score[1]}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"
                st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("맞음 (O)", kind="primary"):
                    q = row['질문']
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][0] += 1
                    st.session_state.current_index = random.randint(0, len(df)-1)
                    st.session_state.state = "QUESTION"
                    st.rerun()
            with c2:
                if st.button("틀림 (X)"):
                    q = row['질문']
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][1] += 1
                    st.session_state.current_index = random.randint(0, len(df)-1)
                    st.session_state.state = "QUESTION"
                    st.rerun()

    # 오답 분석표는 질문 영역과 겹치지 않게 아주 멀리 배치
    for _ in range(15): st.write("") 
    st.write("---")
    st.subheader("⚠️ 이번 세션 취약 문제")
    if st.session_state.session_scores:
        summary_df = pd.DataFrame([{'질문': q, '틀림': s[1]} for q, s in st.session_state.session_scores.items() if s[1] > 0])
        if not summary_df.empty:
            st.table(summary_df.sort_values(by='틀림', ascending=False).head(5))
else:
    st.warning("위의 '상세 에러 내용'을 확인해 주세요.")
