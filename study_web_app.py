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

# 3. 중앙 배치를 위한 강력한 CSS 설정
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .block-container { padding-top: 0rem !important; }
    
    /* 중앙 정렬 컨테이너 */
    .center-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 65vh; /* 화면 높이의 65%를 차지하여 중앙 유지 */
        text-align: center;
    }
    
    .info-text { font-size: 1.8rem !important; color: #aaaaaa; margin-bottom: 5px; font-weight: bold; }
    .session-text { font-size: 1.5rem !important; color: #3498db; margin-bottom: 20px; font-weight: bold; }
    
    /* 질문/정답 텍스트 (4.3rem 유지 및 가독성 최적화) */
    .question-text { font-size: 4.3rem !important; font-weight: bold; color: #f1c40f; line-height: 1.4; word-break: keep-all; margin: 20px 0; }
    .answer-text { font-size: 4.3rem !important; font-weight: bold; color: #2ecc71; line-height: 1.4; word-break: keep-all; margin: 20px 0; }
    
    /* 버튼 스타일 */
    div.stButton > button { width: 100%; height: 140px !important; font-size: 2.8rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
    div.stButton > button[kind="primary"] { background-color: #27ae60; border: none; }
    footer {display: none;}
    
    /* 하단 분석표 여백 */
    .analysis-area { margin-top: 50px; padding-top: 30px; border-top: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# 4. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    try:
        data = conn.read(spreadsheet=st.secrets["gsheets_url"], worksheet="회계학", usecols=[0,1])
        data.columns = ['질문', '정답']
        return data
    except:
        return None

df = load_data()

def get_next_question():
    if df is None: return None
    return random.choice(df.index.tolist())

# --- 5. 화면 구성 시작 ---

if df is not None:
    # 모든 메인 콘텐츠를 중앙 컨테이너로 감쌉니다.
    with st.container():
        st.markdown('<div class="center-container">', unsafe_allow_html=True)
        
        # [준비 화면]
        if st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">인출 준비 완료!</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기"):
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.rerun()

        # [질문 화면]
        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            q_text = row['질문']
            score = st.session_state.session_scores.get(q_text, [0, 0])
            st.markdown(f'<p class="info-text">현재 문제 인출 훈련 중</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="session-text">📈 현재 세션 성적 - 맞음: {score[0]} / 틀림: {score[1]}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {q_text}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"
                st.rerun()

        # [정답 화면]
        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("맞음 (O)"):
                    q_text = row['질문']
                    if q_text not in st.session_state.session_scores: st.session_state.session_scores[q_text] = [0, 0]
                    st.session_state.session_scores[q_text][0] += 1
                    st.session_state.current_index = get_next_question()
                    st.session_state.state = "QUESTION"
                    st.rerun()
            with col2:
                if st.button("틀림 (X)"):
                    q_text = row['질문']
                    if q_text not in st.session_state.session_scores: st.session_state.session_scores[q_text] = [0, 0]
                    st.session_state.session_scores[q_text][1] += 1
                    st.session_state.current_index = get_next_question()
                    st.session_state.state = "QUESTION"
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    # 6. 하단 세션 오답 분석 (별도 영역으로 분리)
    st.markdown('<div class="analysis-area">', unsafe_allow_html=True)
    st.subheader("⚠️ 현재 세션 취약 문제 (많이 틀린 순)")
    if st.session_state.session_scores:
        summary_data = [{'질문': q, '틀림': s[1]} for q, s in st.session_state.session_scores.items() if s[1] > 0]
        if summary_data:
            summary_df = pd.DataFrame(summary_data).sort_values(by='틀림', ascending=False).head(10)
            st.table(summary_df)
        else:
            st.write("아직 틀린 문제가 없습니다. 화이팅!")
    else:
        st.write("훈련을 시작하면 오답 분석표가 여기에 표시됩니다.")
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.error("데이터 로드 실패")
