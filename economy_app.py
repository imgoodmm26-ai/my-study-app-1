import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="감평사 인출 훈련기", layout="wide")

# 2. 세션 상태 초기화
if 'session_scores' not in st.session_state:
    st.session_state.session_scores = {}
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
if 'current_index' not in st.session_state:
    st.session_state.current_index = None

# 3. 디자인 설정 (검은색 배경 및 대형 텍스트)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .info-text { font-size: 1.8rem !important; color: #aaaaaa; font-weight: bold; text-align: center; }
    .session-text { font-size: 1.5rem !important; color: #3498db; font-weight: bold; margin-bottom: 20px; text-align: center; }
    .question-text { font-size: 4.3rem !important; font-weight: bold; color: #f1c40f; line-height: 1.4; text-align: center; margin: 40px 0; word-break: keep-all; }
    .answer-text { font-size: 4.3rem !important; font-weight: bold; color: #2ecc71; line-height: 1.4; text-align: center; margin: 40px 0; word-break: keep-all; }
    
    div.stButton > button { 
        width: 100%; 
        height: 120px !important; 
        font-size: 2.5rem !important; 
        font-weight: bold !important; 
        border-radius: 40px !important; 
        background-color: #34495e; 
        color: white; 
        border: 3px solid #555; 
    }
    </style>
    """, unsafe_allow_html=True)

# 4. 데이터 로드 (질문, 정답 2개 컬럼 사용)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        # 질문(A), 정답(B) 2개 컬럼만 읽어옵니다.
        df = conn.read(spreadsheet=url, worksheet=0, usecols=[0, 1])
        df.columns = ['질문', '정답']
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None

df = load_data()

# --- 5. 화면 구성 ---
if df is not None:
    for _ in range(3): st.write("")
    _, col2, _ = st.columns([1, 10, 1])

    with col2:
        # 대기 화면
        if st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">준비되셨나요, 굿잡님?<br>인출 훈련 시작!</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", type="primary"):
                st.session_state.current_index = random.randint(0, len(df)-1)
                st.session_state.state = "QUESTION"
                st.rerun()

        # 질문 화면
        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            score = st.session_state.session_scores.get(str(row['질문']), [0, 0])
            st.markdown('<p class="info-text">지금 바로 떠올려보세요!</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="session-text">📈 이번 세션 성적 - 맞음: {score[0]} / 틀림: {score[1]}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"
                st.rerun()

        # 정답 화면
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

    # 하단 오답 분석
    for _ in range(10): st.write("") 
    st.write("---")
    st.subheader("⚠️ 주의가 필요한 취약 문항 (Top 5)")
    if st.session_state.session_scores:
        summary_df = pd.DataFrame([{'질문': q, '틀림': s[1]} for q, s in st.session_state.session_scores.items() if s[1] > 0])
        if not summary_df.empty:
            st.table(summary_df.sort_values(by='틀림', ascending=False).head(5))
else:
    st.warning("구글 시트 설정을 확인해 주세요 (A열: 질문, B열: 정답).")
