import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="감평 인출기 (카운팅 보강)", layout="wide")

# 2. 기기 감지
is_pc = not any(x in st.context.headers.get("User-Agent", "").lower() for x in ["iphone", "ipad", "android", "mobile"])

# 3. 세션 상태 초기화 (공부 기록 저장소)
if 'session_scores' not in st.session_state: st.session_state.session_scores = {} 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None

# 4. 디자인 설정
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    .info-text { font-size: 1.8rem !important; color: #2ecc71; font-weight: bold; text-align: center; margin-bottom: 10px; }
    .question-text { font-size: 3.5rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 30px 0; }
    .answer-text { font-size: 3.5rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 30px 0; }
    div.stButton > button { width: 100%; height: 130px !important; font-size: 2.5rem !important; font-weight: bold !important; border-radius: 40px !important; }
</style>
""", unsafe_allow_html=True)

# 5. 데이터 로드
conn = st.connection("gsheets", type=GSheetsConnection)
@st.cache_data(ttl=1) # 1초마다 갱신하여 숫자 반영 속도를 높임
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        df = conn.read(spreadsheet=url, worksheet=0, usecols=[0,1,2,3])
        df.columns = ['질문', '정답', '정답횟수', '오답횟수']
        df['정답횟수'] = pd.to_numeric(df['정답횟수']).fillna(0).astype(int)
        df['오답횟수'] = pd.to_numeric(df['오답횟수']).fillna(0).astype(int)
        return df
    except: return None

df = load_data()

def get_next_question(dataframe):
    if dataframe is None: return None
    available = [idx for idx in range(len(dataframe)) if (int(dataframe.iloc[idx]['정답횟수']) + st.session_state.session_scores.get(str(dataframe.iloc[idx]['질문']), [0, 0])[0]) < 5]
    return random.choice(available) if available else "GRADUATED"

# --- 6. 화면 구성 ---
if df is not None:
    _, col, _ = st.columns([1, 10, 1])
    with col:
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 모든 문제를 정복하셨습니다! 🎊</p>', unsafe_allow_html=True)
            if st.button("처음부터 다시 시작하기"):
                st.session_state.session_scores = {}; st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">회계학 인출 훈련 시작</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", type="primary"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            q_text = str(row['질문'])
            # 시트 점수 + 현재 세션 점수 합산 (실시간 카운팅 핵심)
            session_data = st.session_state.session_scores.get(q_text, [0, 0])
            ok_total = int(row['정답횟수']) + session_data[0]
            fail_total = int(row['오답횟수']) + session_data[1]
            
            st.markdown(f'<p class="info-text">누적 정답: {ok_total}/5 | 누적 오답: {fail_total}회</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"): st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("맞음 (O)", type="primary"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][0] += 1 # 세션 점수 즉시 반영
                    if is_pc:
                        try:
                            df.iloc[st.session_state.current_index, 2] += 1
                            conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                        except: pass
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("틀림 (X)"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][1] += 1 # 세션 점수 즉시 반영
                    if is_pc:
                        try:
                            df.iloc[st.session_state.current_index, 3] += 1
                            conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                        except: pass
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
