import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="인출 훈련기", layout="wide")

# 2. 세션 상태 초기화 (맞춤형 학습 데이터 저장)
if 'session_scores' not in st.session_state:
    st.session_state.session_scores = {} # {질문: [맞음횟수, 틀림횟수]}
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
if 'current_index' not in st.session_state:
    st.session_state.current_index = None

# 3. 디자인 설정 (가독성 및 중앙 정렬 최적화)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .info-text { font-size: 1.6rem !important; color: #aaaaaa; font-weight: bold; text-align: center; }
    .session-text { font-size: 1.4rem !important; color: #3498db; font-weight: bold; margin-bottom: 20px; text-align: center; }
    
    /* 질문/정답 텍스트 (기존 4.3rem -> 4.0rem으로 추가 축소) */
    .question-text { font-size: 4.0rem !important; font-weight: bold; color: #f1c40f; line-height: 1.3; text-align: center; margin: 30px 0; word-break: keep-all; }
    .answer-text { font-size: 4.0rem !important; font-weight: bold; color: #2ecc71; line-height: 1.3; text-align: center; margin: 30px 0; word-break: keep-all; }
    
    /* 라벨 스타일 */
    .label-badge { background-color: #e67e22; color: white; padding: 4px 12px; border-radius: 10px; font-size: 1.2rem; margin-right: 5px; }
    
    /* 버튼 스타일 (기존 2.8rem -> 2.5rem으로 축소) */
    div.stButton > button { 
        width: 100%; height: 130px !important; 
        font-size: 2.5rem !important; font-weight: bold !important; 
        border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; 
    }
    footer {display: none;}
    </style>
    """, unsafe_allow_html=True)

# 4. 데이터 로드
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        df = conn.read(spreadsheet=url, worksheet=0, usecols=[0,1])
        df.columns = ['질문', '정답']
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None

df = load_data()

# [핵심 로직] 5번 맞힌 문제를 제외하고 다음 문제를 뽑는 함수
def get_next_question_index(df):
    if df is None: return None
    
    # 5번 미만으로 맞힌 문제들의 인덱스만 필터링
    available_indices = []
    for idx in range(len(df)):
        q_text = str(df.iloc[idx]['질문'])
        # session_scores에서 해당 질문의 '맞음' 횟수 확인
        correct_count = st.session_state.session_scores.get(q_text, [0, 0])[0]
        if correct_count < 5:
            available_indices.append(idx)
    
    if not available_indices:
        return "GRADUATED" # 모든 문제 졸업
    return random.choice(available_indices)

# --- 5. 화면 구성 ---
if df is not None:
    for _ in range(4): st.write("") # 상단 여백
    _, col2, _ = st.columns([1, 10, 1])

    with col2:
        # 모든 문제를 졸업했을 때의 화면
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 축하합니다! 모든 문제를 5회 이상 인출하여 졸업하셨습니다! 🎊</p>', unsafe_allow_html=True)
            if st.button("처음부터 다시 훈련하기", type="primary"):
                st.session_state.session_scores = {}
                st.session_state.state = "IDLE"
                st.session_state.current_index = None
                st.rerun()

        # [IDLE: 준비 화면]
        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">인출 훈련 준비 완료</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", type="primary"):
                st.session_state.current_index = get_next_question_index(df)
                st.session_state.state = "QUESTION"
                st.rerun()

        # [QUESTION: 질문 화면]
        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            q_text = str(row['질문'])
            score = st.session_state.session_scores.get(q_text, [0, 0])
            
            st.markdown(f'<p class="info-text"><span class="label-badge">핵심개념</span> 현재 정답 횟수: {score[0]} / 5회 달성 시 졸업</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {q_text}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"
                st.rerun()

        # [ANSWER: 정답 화면]
        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("맞음 (O)", type="primary"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][0] += 1 # 맞음 횟수 증가
                    
                    st.session_state.current_index = get_next_question_index(df)
                    st.session_state.state = "QUESTION"
                    st.rerun()
            with c2:
                if st.button("틀림 (X)"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][1] += 1 # 틀림 횟수 증가
                    
                    st.session_state.current_index = get_next_question_index(df)
                    st.session_state.state = "QUESTION"
                    st.rerun()

    # 6. 하단 오답 분석 및 졸업 현황
    for _ in range(15): st.write("") 
    st.write("---")
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("⚠️ 취약 문제 Top 5 (이번 세션)")
        if st.session_state.session_scores:
            err_df = pd.DataFrame([{'질문': q, '틀림': s[1]} for q, s in st.session_state.session_scores.items() if s[1] > 0])
            if not err_df.empty:
                st.table(err_df.sort_values(by='틀림', ascending=False).head(5))
            else:
                st.write("틀린 문제가 없습니다. 훌륭해요!")
    
    with col_right:
        st.subheader("🎓 졸업 대기 중 (3회 이상 정답)")
        grad_pending = pd.DataFrame([{'질문': q, '진행도': f"{s[0]}/5"} for q, s in st.session_state.session_scores.items() if 3 <= s[0] < 5])
        if not grad_pending.empty:
            st.table(grad_pending)
        else:
            st.write("열심히 달려서 5회 정답을 채워보세요!")

else:
    st.warning("구글 시트의 첫 번째 탭을 확인해 주세요.")
