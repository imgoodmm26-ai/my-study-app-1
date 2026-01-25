import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="감평 하이브리드 인출기", layout="wide")

# 2. 기기 및 세션 초기화
is_pc = not any(x in st.context.headers.get("User-Agent", "").lower() for x in ["iphone", "ipad", "android", "mobile"])

# 피보나치 간격: 이 숫자가 되었을 때만 복습 카드가 튀어나옵니다.
FIBO = [0, 5, 8, 13, 21, 34]

if 'session_scores' not in st.session_state: st.session_state.session_scores = {} 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None

# 레벨 및 스케줄 관리
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} 
if 'schedules' not in st.session_state: st.session_state.schedules = {} 
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0

# 3. 디자인 설정
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    .info-text { font-size: 1.4rem !important; color: #aaaaaa; font-weight: bold; text-align: center; margin-bottom: 10px; }
    .level-tag { color: #3498db; font-weight: bold; font-size: 1.2rem; text-align: center; }
    .question-text { font-size: 3.5rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 30px 0; line-height: 1.3; }
    .answer-text { font-size: 3.5rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 30px 0; line-height: 1.3; }
    div.stButton > button { width: 100%; height: 130px !important; font-size: 2.5rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드
conn = st.connection("gsheets", type=GSheetsConnection)
@st.cache_data(ttl=1)
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

# 5. [핵심] 하이브리드 출제 로직
def get_next_question(dataframe):
    curr_cnt = st.session_state.solve_count
    
    # [Step 1] 현재 순서가 복습 주기(5, 8, 13...) 인가?
    # 혹은 현재 순서 이전에 밀린 복습 문제가 있는가?
    pending_reviews = [k for k in st.session_state.schedules.keys() if k <= curr_cnt and st.session_state.schedules[k]]
    
    if pending_reviews:
        # 가장 오래된 복습 대상 시점의 문제를 꺼냄
        target_key = pending_reviews[0]
        return st.session_state.schedules[target_key].pop(0)

    # [Step 2] 복습할 게 없다면 '무조건' 새로운 문제를 찾음
    # 조건: 시트 정답 5회 미만 + 현재 어떤 스케줄에도 예약되지 않은 것
    all_scheduled = [idx for sublist in st.session_state.schedules.values() for idx in sublist]
    available_new = [i for i in range(len(dataframe)) if int(dataframe.iloc[i]['정답횟수']) < 5 and i not in all_scheduled]
    
    if available_new:
        return random.choice(available_new)

    # [Step 3] 새로운 문제도 다 떨어졌다면, 미래의 복습 문제를 앞당겨옴
    future_reviews = sorted([k for k in st.session_state.schedules.keys() if k > curr_cnt and st.session_state.schedules[k]])
    if future_reviews:
        return st.session_state.schedules[future_reviews[0]].pop(0)
        
    return "GRADUATED"

# --- 6. 화면 구성 ---
if df is not None:
    _, col, _ = st.columns([1, 10, 1])
    with col:
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 모든 회독을 완료했습니다! 🎊</p>', unsafe_allow_html=True)
            if st.button("다시 시작하기"):
                st.session_state.q_levels = {}; st.session_state.schedules = {}
                st.session_state.solve_count = 0; st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">회계학 하이브리드 인출</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", type="primary"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            
            st.markdown(f'<p class="info-text">총 풀이 수: {st.session_state.solve_count}장</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="level-tag">{"🆕 신규 문항 등장!" if lv==0 else f"🔥 Lv.{lv} 복습 (끈질기게!)"}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"): st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            q_idx = st.session_state.current_index
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("맞음 (O)", type="primary"):
                    new_lv = st.session_state.q_levels.get(q_idx, 0) + 1
                    if new_lv > 5:
                        if is_pc:
                            try:
                                df.iloc[q_idx, 2] += 1
                                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                            except: pass
                        st.session_state.q_levels[q_idx] = 0
                    else:
                        st.session_state.q_levels[q_idx] = new_lv
                        # [포인트] 현재 풀이 수에 피보나치 간격을 더해 예약
                        target = st.session_state.solve_count + FIBO[new_lv]
                        if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                        st.session_state.schedules[target].append(q_idx)
                    
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("틀림 (X)"):
                    st.session_state.q_levels[q_idx] = 1 # 1단계로 강등
                    target = st.session_state.solve_count + FIBO[1] # 5장 뒤 예약
                    if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                    st.session_state.schedules[target].append(q_idx)
                    
                    if is_pc:
                        try:
                            df.iloc[q_idx, 3] += 1
                            conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                        except: pass
                    
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
