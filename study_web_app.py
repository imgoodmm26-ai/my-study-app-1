import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="감평 인출기 (카운팅 완벽 해결)", layout="wide")

# 2. 기기 감지
is_pc = not any(x in st.context.headers.get("User-Agent", "").lower() for x in ["iphone", "ipad", "android", "mobile"])

# 3. 세션 상태 초기화 (핵심: 세션 점수 저장소 확인)
if 'session_scores' not in st.session_state:
    st.session_state.session_scores = {} # { '질문': [맞음, 틀림] }
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
if 'current_index' not in st.session_state:
    st.session_state.current_index = None

# 4. 디자인 설정
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    .device-tag { color: #3498db; font-size: 1.1rem; font-weight: bold; text-align: right; }
    .info-text { font-size: 1.6rem !important; color: #aaaaaa; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .question-text { font-size: 3.5rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 30px 0; line-height: 1.3; }
    .answer-text { font-size: 3.5rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 30px 0; line-height: 1.3; }
    div.stButton > button { width: 100%; height: 130px !important; font-size: 2.5rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
</style>
""", unsafe_allow_html=True)

# 5. 데이터 로드 (시트 헤더를 강제로 맞춰줍니다)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=1) # TTL을 1초로 줄여 실시간 반영을 돕습니다
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        df = conn.read(spreadsheet=url, worksheet=0, usecols=[0,1,2,3])
        # 시트의 열 이름을 강제로 [질문, 정답, 정답횟수, 오답횟수]로 고정
        df.columns = ['질문', '정답', '정답횟수', '오답횟수']
        df['정답횟수'] = pd.to_numeric(df['정답횟수']).fillna(0).astype(int)
        df['오답횟수'] = pd.to_numeric(df['오답횟수']).fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None

df = load_data()

# 5회 성공 시 졸업 로직
def get_next_question(dataframe):
    if dataframe is None: return None
    available = []
    for idx in range(len(dataframe)):
        q_text = str(dataframe.iloc[idx]['질문'])
        # 시트 값 + 이번 판 점수
        score = st.session_state.session_scores.get(q_text, [0, 0])
        total_ok = int(dataframe.iloc[idx]['정답횟수']) + score[0]
        if total_ok < 5:
            available.append(idx)
    return random.choice(available) if available else "GRADUATED"

# --- 6. 화면 구성 ---
if df is not None:
    mode_text = "💻 PC 모드 (기록 동기화)" if is_pc else "📱 모바일 모드 (세션 저장)"
    st.markdown(f'<p class="device-tag">{mode_text}</p>', unsafe_allow_html=True)

    _, col, _ = st.columns([1, 10, 1])
    with col:
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 모든 문제를 정복하셨습니다! 🎊</p>', unsafe_allow_html=True)
            if st.button("처음부터 다시 시작하기"):
                st.session_state.session_scores = {}; st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">회계학 인출 훈련 시작</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", type="primary"):
                st.session_state.current_index = get_next_question(df)
                st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            q_name = str(row['질문'])
            
            # 현재 카운팅 계산 (시트 + 세션)
            session_data = st.session_state.session_scores.get(q_name, [0, 0])
            ok_cnt = int(row['정답횟수']) + session_data[0]
            fail_cnt = int(row['오답횟수']) + session_data[1]
            
            st.markdown(f'<p class="info-text">누적 정답: {ok_cnt}/5 | 누적 오답: {fail_cnt}회</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("맞음 (O)", type="primary"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][0] += 1 # 즉시 카운트 증가
                    
                    if is_pc:
                        try:
                            df.loc[st.session_state.current_index, '정답횟수'] += 1
                            conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                        except: pass
                    
                    st.session_state.current_index = get_next_question(df)
                    st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("틀림 (X)"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][1] += 1 # 즉시 카운트 증가
                    
                    if is_pc:
                        try:
                            df.loc[st.session_state.current_index, '오답횟수'] += 1
                            conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                        except: pass
                    
                    st.session_state.current_index = get_next_question(df)
                    st.session_state.state = "QUESTION"; st.rerun()
