import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="감평 피보나치 마스터", layout="wide")

# 2. 기기 및 세션 초기화
is_pc = not any(x in st.context.headers.get("User-Agent", "").lower() for x in ["iphone", "ipad", "android", "mobile"])

# [핵심] 피보나치 스케줄링 변수
FIBO = [0, 5, 8, 13, 21, 34] # 레벨별 간격

if 'session_scores' not in st.session_state: st.session_state.session_scores = {} 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None

# [신규] 레벨 관리 및 스케줄러
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} # {idx: current_level}
if 'schedules' not in st.session_state: st.session_state.schedules = {} # {target_solve_count: [indices]}
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0

# 3. 디자인 설정
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    .info-text { font-size: 1.4rem !important; color: #aaaaaa; text-align: center; margin-bottom: 10px; }
    .level-tag { color: #f39c12; font-weight: bold; font-size: 1.2rem; text-align: center; }
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
        return df
    except: return None

df = load_data()

# 5. [핵심] 피보나치 스케줄러 출제 로직
def get_next_question(dataframe):
    curr_count = st.session_state.solve_count
    
    # 1. 현재 카운트에 예약된 복습 문제가 있는가?
    if curr_count in st.session_state.schedules and st.session_state.schedules[curr_count]:
        return st.session_state.schedules[curr_count].pop(0)
    
    # 2. 없다면, 졸업하지 않은 문제 중 랜덤 추출 (시트 정답 5회 미만)
    available = [i for i in range(len(dataframe)) if int(dataframe.iloc[i]['정답횟수']) < 5]
    
    # 예약된 미래 문제 제외 (중복 방지)
    scheduled_indices = [idx for sublist in st.session_state.schedules.values() for idx in sublist]
    available = [i for i in available if i not in scheduled_indices]
    
    if not available:
        # 모든 문제가 예약되었거나 졸업했다면, 가장 가까운 예약 문제 가져오기
        future_counts = sorted([k for k in st.session_state.schedules.keys() if k > curr_count])
        if future_counts:
            next_target = future_counts[0]
            return st.session_state.schedules[next_target].pop(0)
        return "GRADUATED"
    
    return random.choice(available)

# --- 6. 화면 구성 ---
if df is not None:
    _, col, _ = st.columns([1, 10, 1])
    with col:
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 회계학 완전 정복! 🎊</p>', unsafe_allow_html=True)
            if st.button("다시 시작하기"):
                st.session_state.q_levels = {}; st.session_state.schedules = {}; st.session_state.solve_count = 0
                st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">피보나치 Lv.5 인출 시작</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", type="primary"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            st.markdown(f'<p class="info-text">진행 수: {st.session_state.solve_count}장 | 현재 문항 숙달도</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="level-tag">{"🆕 신규 문항" if lv==0 else f"🔥 Level {lv} (복습)"}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"): st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            q_idx = st.session_state.current_index
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("맞음 (O)", type="primary"):
                    # 레벨 업!
                    new_lv = st.session_state.q_levels.get(q_idx, 0) + 1
                    if new_lv > 5:
                        # [졸업] 최종 Level 5 통과 시 시트에 1점 추가
                        if is_pc:
                            try:
                                df.iloc[q_idx, 2] += 1
                                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                            except: pass
                        st.session_state.q_levels[q_idx] = 0 # 레벨 리셋
                    else:
                        st.session_state.q_levels[q_idx] = new_lv
                        # 피보나치 간격 뒤로 예약
                        target = st.session_state.solve_count + FIBO[new_lv]
                        if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                        st.session_state.schedules[target].append(q_idx)
                    
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("틀림 (X)"):
                    # 틀리면 레벨 1로 강등 및 5장 뒤 예약
                    st.session_state.q_levels[q_idx] = 1
                    target = st.session_state.solve_count + FIBO[1]
                    if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                    st.session_state.schedules[target].append(q_idx)
                    
                    if is_pc:
                        try:
                            df.iloc[q_idx, 3] += 1
                            conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                        except: pass
                    
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
