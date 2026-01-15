import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="인출 훈련기", layout="wide")

# 2. 세션 상태(사이트 내 메모리) 초기화
if 'session_scores' not in st.session_state:
    st.session_state.session_scores = {} # {질문내용: [맞음, 틀림]}
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
if 'current_index' not in st.session_state:
    st.session_state.current_index = None

# 3. 태블릿 최적화 CSS (글씨 크기 약 2포인트 축소 적용)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .block-container { padding-top: 1rem !important; }
    
    /* 상단 정보 텍스트 (기존 2.5rem -> 2.0rem) */
    .info-text { font-size: 2.0rem !important; color: #aaaaaa; text-align: center; margin-bottom: 5px; font-weight: bold; }
    
    /* 세션 성적 텍스트 (기존 2.0rem -> 1.6rem) */
    .session-text { font-size: 1.6rem !important; color: #3498db; text-align: center; margin-bottom: 20px; font-weight: bold; }
    
    /* 질문/정답 텍스트 (기존 5.0rem -> 4.3rem) */
    .question-text { font-size: 4.3rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 60px 0; line-height: 1.3; word-break: keep-all; }
    .answer-text { font-size: 4.3rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 60px 0; line-height: 1.3; word-break: keep-all; }
    
    /* 버튼 글자 크기 (기존 3.5rem -> 2.8rem) */
    div.stButton > button { width: 100%; height: 160px !important; font-size: 2.8rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
    div.stButton > button[kind="primary"] { background-color: #27ae60; border: none; }
    footer {display: none;}
    
    /* 오답 분석표 스타일 */
    .stDataFrame { background-color: white; border-radius: 10px; margin-top: 30px; }
    </style>
    """, unsafe_allow_html=True)

# 4. 구글 시트 연결 (읽기 전용)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    try:
        # 시트에서 질문(0), 정답(1) 열을 기본으로 가져옵니다.
        data = conn.read(spreadsheet=st.secrets["gsheets_url"], usecols=[0,1])
        data.columns = ['질문', '정답']
        return data
    except:
        return None

df = load_data()

# 다음 문제 추출 로직
def get_next_question():
    if df is None: return None
    # 현재 세션에서 많이 틀린 문제에 가중치를 줄 수 있습니다.
    indices = df.index.tolist()
    return random.choice(indices)

# --- 5. 화면 구성 시작 ---

if df is not None:
    # [IDLE: 준비 화면]
    if st.session_state.state == "IDLE":
        st.markdown('<p class="question-text">인출 준비 완료!</p>', unsafe_allow_html=True)
        if st.button("훈련 시작 하기"):
            st.session_state.current_index = get_next_question()
            st.session_state.state = "QUESTION"
            st.rerun()

    # [QUESTION: 앞면 질문]
    elif st.session_state.state == "QUESTION":
        row = df.iloc[st.session_state.current_index]
        q_text = row['질문']
        
        # 세션 내 점수 계산
        score = st.session_state.session_scores.get(q_text, [0, 0])
        st.markdown(f'<p class="info-text">현재 문제 인출 훈련 중</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="session-text">📈 현재 세션 성적 - 맞음: {score[0]} / 틀림: {score[1]}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="question-text">Q. {q_text}</p>', unsafe_allow_html=True)
        
        if st.button("정답 확인하기"):
            st.session_state.state = "ANSWER"
            st.rerun()

    # [ANSWER: 뒷면 정답]
    elif st.session_state.state == "ANSWER":
        row = df.iloc[st.session_state.current_index]
        st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("맞음 (O)"):
                q_text = row['질문']
                if q_text not in st.session_state.session_scores:
                    st.session_state.session_scores[q_text] = [0, 0]
                st.session_state.session_scores[q_text][0] += 1 # 세션 맞음 카운트 업
                
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.rerun()
        with col2:
            if st.button("틀림 (X)"):
                q_text = row['질문']
                if q_text not in st.session_state.session_scores:
                    st.session_state.session_scores[q_text] = [0, 0]
                st.session_state.session_scores[q_text][1] += 1 # 세션 틀림 카운트 업
                
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.rerun()

    # 6. 하단 세션 오답 분석 (사이트 내 카운팅 기반)
    st.markdown("---")
    st.subheader("⚠️ 현재 세션 취약 문제 (많이 틀린 순)")
    
    if st.session_state.session_scores:
        # 세션 데이터를 표로 변환
        summary_data = []
        for q, s in st.session_state.session_scores.items():
            summary_data.append({'질문': q, '맞음': s[0], '틀림': s[1]})
        
        summary_df = pd.DataFrame(summary_data)
        top_session_errors = summary_df.sort_values(by='틀림', ascending=False).head(10)
        st.table(top_session_errors[['질문', '틀림']])
    else:
        st.write("훈련을 시작하면 오답 분석표가 여기에 표시됩니다.")

else:
    st.error("데이터를 불러올 수 없습니다. Secrets의 URL과 시트 설정을 확인해주세요.")
