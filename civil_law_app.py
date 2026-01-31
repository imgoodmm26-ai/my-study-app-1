import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="COSMIC STUDY: MOBILE OPT", layout="wide")

# 2. 세션 및 피보나치 설정
FIBO_GAP = [0, 5, 13, 21, 34, 55, 89, 144] 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} 
if 'q_wrong_levels' not in st.session_state: st.session_state.q_wrong_levels = {}
if 'schedules' not in st.session_state: st.session_state.schedules = {} 
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0
if 'last_msg' not in st.session_state: st.session_state.last_msg = "모바일 최적화 시스템 가동."

# 3. [핵심] 반응형 디자인 (Media Query 적용)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Noto+Sans+KR:wght@400;700&display=swap');

    .stApp { background: #020617; color: #f8fafc; font-family: 'Noto Sans KR', sans-serif; }
    
    /* 공통 카드 스타일 */
    .cosmic-card {
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid #0ea5e9;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 0 20px rgba(14, 165, 233, 0.2);
        text-align: center;
        margin: 10px 0;
        min-height: 250px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    /* 반응형 텍스트 설정 */
    .question-text { font-size: 2.5rem !important; font-weight: 700; color: #facc15; }
    .answer-text { font-size: 2.8rem !important; font-weight: 700; color: #22c55e; }
    
    /* 모바일 전용 (600px 이하) */
    @media (max-width: 600px) {
        .question-text { font-size: 1.6rem !important; }
        .answer-text { font-size: 1.8rem !important; }
        .wrong-side, .correct-side { width: 45vw !important; font-size: 1.2rem !important; }
        .center-line { font-size: 1.5rem !important; }
        div.stButton > button { height: 70px !important; font-size: 1.1rem !important; }
    }

    /* 듀얼 게이지 와이드 가변형 */
    .dual-gauge-container { display: flex; flex-direction: column; align-items: center; width: 100%; margin: 15px 0; }
    .gauge-row { display: flex; align-items: center; justify-content: center; white-space: nowrap; }
    .wrong-side { color: #ef4444; text-align: right; width: 350px; letter-spacing: 1px; }
    .correct-side { color: #a855f7; text-align: left; width: 350px; letter-spacing: 1px; }
    .center-line { color: #475569; font-weight: bold; margin: 0 10px; }

    .status-badge { background: #0ea5e9; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-family: 'Orbitron'; }
    
    /* 버튼 스타일 */
    div.stButton > button { 
        width: 100% !important; height: 90px !important; 
        font-family: 'Orbitron', sans-serif !important;
        border-radius: 12px !important;
        background: #1e293b !important; border: 1px solid #334155 !important;
        color: white !important;
    }
    div.stButton > button:hover { border-color: #0ea5e9 !important; box-shadow: 0 0 10px #0ea5e9; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드 (52~84문항 동적 대응)
conn = st.connection("gsheets", type=GSheetsConnection)
@st.cache_data(ttl=1)
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        df_raw = conn.read(spreadsheet=url, worksheet=0)
        df = df_raw.iloc[:, :7]
        df.columns = ['질문', '정답', '정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']
        df = df.dropna(subset=['질문']).reset_index(drop=True)
        for col in ['정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']:
            df[col] = pd.to_numeric(df[col]).fillna(0).astype(int)
        return df
    except: return None

if 'df' not in st.session_state: st.session_state.df = load_data()
df = st.session_state.df

# 5. 하이브리드 로직 (50% 신규 보장)
def get_next_question(dataframe):
    curr_cnt = st.session_state.solve_count
    all_scheduled = [idx for sublist in st.session_state.schedules.values() for idx in sublist]
    available_new = [i for i in range(len(dataframe)) if int(dataframe.iloc[i]['정답횟수']) < 5 and i not in all_scheduled]
    pending_keys = sorted([k for k in st.session_state.schedules.keys() if k <= curr_cnt and st.session_state.schedules[k]])
    
    if available_new and pending_keys:
        if random.random() < 0.5: return random.choice(available_new)
        else: return st.session_state.schedules[pending_keys[0]].pop(0)
    if available_new: return random.choice(available_new)
    if pending_keys: return st.session_state.schedules[pending_keys[0]].pop(0)
    return "GRADUATED"

# --- 6. 화면 구성 ---
if df is not None:
    # 상단 툴바
    t_col1, t_col2 = st.columns([7, 3])
    with t_col1: st.markdown(f"**{st.session_state.solve_count} SOLVED**")
    with t_col2:
        if st.button("🔄 SYNC"):
            st.cache_data.clear()
            st.session_state.df = load_data()
            st.rerun()

    if isinstance(st.session_state.current_index, int) and st.session_state.current_index >= len(df):
        st.session_state.current_index = get_next_question(df)

    # 메인 인출 영역
    if st.session_state.current_index == "GRADUATED":
        st.markdown('<div class="cosmic-card"><p class="question-text">MISSION COMPLETE</p></div>', unsafe_allow_html=True)
        if st.button("RESTART"):
            st.session_state.q_levels = {}; st.session_state.solve_count = 0
            st.session_state.state = "IDLE"; st.rerun()

    elif st.session_state.state == "IDLE":
        st.markdown('<div class="cosmic-card"><p class="question-text">READY?</p></div>', unsafe_allow_html=True)
        if st.button("START MISSION"):
            st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

    elif st.session_state.state == "QUESTION":
        row = df.iloc[st.session_state.current_index]
        c_lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
        
        # 게이지 렌더링 (가변형)
        w_bars = "█" * min(st.session_state.q_wrong_levels.get(st.session_state.current_index, 0), 10)
        c_bars = "█" * min(c_lv, 10)
        st.markdown(f'<div class="dual-gauge-container"><div class="gauge-row"><span class="wrong-side">{w_bars}</span><span class="center-line">|</span><span class="correct-side">{c_bars}</span></div></div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="cosmic-card"><span class="status-badge">LV.{c_lv} TARGET</span><p class="question-text">{row["질문"]}</p></div>', unsafe_allow_html=True)
        if st.button("FLIP (Space)"): st.session_state.state = "ANSWER"; st.rerun()

    elif st.session_state.state == "ANSWER":
        row = df.iloc[st.session_state.current_index]
        st.markdown(f'<div class="cosmic-card"><p class="answer-text">{row["정답"]}</p></div>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("HARD (1)"):
                q_idx = st.session_state.current_index
                df.at[q_idx, '오답횟수'] += 1
                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                st.session_state.schedules.setdefault(st.session_state.solve_count + 5, []).append(q_idx)
                st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
        with c2:
            if st.button("NORM (2)"):
                q_idx = st.session_state.current_index
                new_lv = st.session_state.q_levels.get(q_idx, 0) + 1
                df.at[q_idx, '정상횟수'] += 1
                if new_lv > 7: df.at[q_idx, '정답횟수'] += 1
                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                st.session_state.q_levels[q_idx] = new_lv
                st.session_state.schedules.setdefault(st.session_state.solve_count + FIBO_GAP[min(new_lv, 7)], []).append(q_idx)
                st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
        with c3:
            if st.button("EASY (3)"):
                q_idx = st.session_state.current_index
                df.at[q_idx, '정답횟수'] = 5
                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

# 7. 단축키 (PC 사용 시 대비)
components.html("""<script>const doc = window.parent.document;doc.addEventListener('keydown', function(e) { if (e.key === '1') { doc.querySelectorAll('button')[2].click(); } else if (e.key === '2') { doc.querySelectorAll('button')[3].click(); } else if (e.key === '3') { doc.querySelectorAll('button')[4].click(); } });</script>""", height=0)
