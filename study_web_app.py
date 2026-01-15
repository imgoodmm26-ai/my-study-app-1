import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="인출 훈련기", layout="wide")

# 2. 세션 상태 초기화 (에러 방지용)
if 'session_scores' not in st.session_state:
    st.session_state.session_scores = {}
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
if 'current_index' not in st.session_state:
    st.session_state.current_index = None

# 3. CSS 설정 (디자인만 입히고, 구조는 건드리지 않음)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    
    /* 텍스트 스타일: 이전보다 2포인트 작게 조정 */
    .info-text { font-size: 1.8rem !important; color: #aaaaaa; font-weight: bold; text-align: center; }
    .session-text { font-size: 1.5rem !important; color: #3498db; font-weight: bold; margin-bottom: 20px; text-align: center; }
    
    .question-text { font-size: 4.3rem !important; font-weight: bold; color: #f1c40f; line-height: 1.4; text-align: center; margin-bottom: 30px; }
    .answer-text { font-size: 4.3rem !important; font-weight: bold; color: #2ecc71; line-height: 1.4; text-align: center; margin-bottom: 30px; }
    
    /* 버튼 스타일: 글자 크기 2.8rem */
    div.stButton > button { 
        width: 100%; 
        height: 140px !important; 
        font-size: 2.8rem !important; 
        font-weight: bold !important; 
        border-radius: 40px !important; 
        background-color: #34495e; 
        color: white; 
        border: 3px solid #555;
    }
    div.stButton > button[kind="primary"] { background-color: #27ae60; border: none; }
    
    footer {display: none;}
    </style>
    """, unsafe_allow_html=True)

# 4. 데이터 로드 (읽기 전용)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        df = conn.read(spreadsheet=st.secrets["gsheets_url"], worksheet="회계학", usecols=[0,1])
        df.columns = ['질문', '정답']
        return df
    except:
        return None

df = load_data()

def get_next_question():
    if df is not None:
        return random.randint(0, len(df)-1)
    return None

# --- 5. 화면 구성 (에러 없는 중앙 정렬 방식) ---

if df is not None:
    # 수직 중앙 정렬을 위해 위에 빈 공간을 만듭니다.
    for _ in range(5):
        st.write("")

    # 가로 중앙 정렬을 위해 3개의 컬럼을 만들고 가운데(col2)만 사용합니다.
    _, col2, _ = st.columns([1, 8, 1])

    with col2:
        # [준비 화면]
        if st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">인출 훈련 준비 완료</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", kind="primary"):
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.rerun()

        # [질문 화면]
        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            q_text = row['질문']
            score = st.session_state.session_scores.get(q_text, [0, 0])
            
            st.markdown('<p class="info-text">인출 훈련 중</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="session-text">맞음: {score[0]} / 틀림: {score[1]}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {q_text}</p>', unsafe_allow_html=True)
            
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"
                st.rerun()

        # [정답 화면]
        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("맞음 (O)", kind="primary"):
                    q_text = row['질문']
                    if q_text not in st.session_state.session_scores: st.session_state.session_scores[q_text] = [0, 0]
                    st.session_state.session_scores[q_text][0] += 1
                    st.session_state.current_index = get_next_question()
                    st.session_state.state = "QUESTION"
                    st.rerun()
            with btn_col2:
                if st.button("틀림 (X)"):
                    q_text = row['질문']
                    if q_text not in st.session_state.session_scores: st.session_state.session_scores[q_text] = [0, 0]
                    st.session_state.session_scores[q_text][1] += 1
                    st.session_state.current_index = get_next_question()
                    st.session_state.state = "QUESTION"
                    st.rerun()

    # 하단 오답 분석 영역 (충분한 간격 유지)
    for _ in range(10): st.write("") # 질문 영역과 분석표 사이 간격 확보
    st.write("---")
    st.subheader("⚠️ 이번 세션 취약 문제")
    if st.session_state.session_scores:
        summary_data = [{'질문': q, '틀림': s[1]} for q, s in st.session_state.session_scores.items() if s[1] > 0]
        if summary_data:
            summary_df = pd.DataFrame(summary_data).sort_values(by='틀림', ascending=False).head(5)
            st.table(summary_df)
        else:
            st.write("아직 틀린 문제가 없습니다. 굿잡!")
    else:
        st.write("데이터가 쌓이면 여기에 표시됩니다.")

else:
    st.error("데이터 로드 실패. 주소와 탭 이름을 확인해 주세요.")
