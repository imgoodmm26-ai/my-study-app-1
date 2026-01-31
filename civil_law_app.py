import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="감평 반응형 인출기", layout="wide")

# 2. 세션 및 피보나치 설정
FIBO_GAP = [0, 5, 13, 21, 34, 55, 89, 144] 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} 
if 'q_wrong_levels' not in st.session_state: st.session_state.q_wrong_levels = {}
if 'schedules' not in st.session_state: st.session_state.schedules = {} 
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0
if 'last_msg' not in st.session_state: st.session_state.last_msg = "기기 맞춤형 인터페이스를 가동합니다."

# 3. [핵심] 미디어 쿼리를 활용한 반응형 CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Noto+Sans+KR:wght@400;700&display=swap');
    
    .stApp { background: #020617; color: #f8fafc; font-family: 'Noto Sans KR', sans-serif; }
    
    /* 기본 카드 (PC용) */
    .cosmic-card {
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid #0ea5e9;
        border-radius: 20px;
        padding: 40px;
        box-shadow: 0 0 25px rgba(14, 165, 233, 0.2);
        text-align: center;
        margin: 20px 0;
        min-height: 350px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .question-text { font-size: 3.2rem !important; font-weight: 700; color: #facc15; line-height: 1.4; }
    .answer-text { font-size: 3.5rem !important; font-weight: 700; color: #22c55e; line-height: 1.4; }

    /* 게이지 공통 스타일 */
    .dual-gauge-container { display: flex; flex-direction: column; align-items: center; width: 100%; margin: 20px 0; }
    .gauge-row { display: flex; align-items: center; justify-content: center; white-space: nowrap; font-family: 'Courier New', monospace; }
    .wrong-side { color: #ef4444; text-align: right; width: 450px; font-size: 2.2rem; }
    .correct-side { color: #a855f7; text-align: left; width: 450px; font-size: 2.2rem; }
    .center-line { color: #475569; font-weight: bold; margin: 0 15px; font-size: 2.5rem; }

    /* [반응형] 모바일 화면 최적화 (600px 이하) */
    @media (max-width: 600px) {
        .cosmic-card { min-height: 200px; padding: 20px; margin: 10px 0; border-radius: 12px; }
        .question-text { font-size: 1.6rem !important; }
        .answer-text { font-size: 1.8rem !important; }
        .wrong-side, .correct-side { width: 40vw !important; font-size: 1.2rem !important; } /* 게이지 축소 */
        .center-line { font-size: 1.5rem !important; margin: 0 5px; }
        div.stButton > button { height: 75px !important; font-size: 1.2rem !important; }
        .progress-container { margin-top: 30px !important; } /* 하단바 밀착 */
    }

    div.stButton > button { 
        width: 100% !important; height: 100px !important; 
        font-family: 'Orbitron', sans-serif !important; border-radius: 12px !important;
        background: #1e293b !important; color: white !important; border: 1px solid #334155 !important;
    }
    .status-badge { background: #0ea5e9; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.9rem; font-family: 'Orbitron'; margin-bottom: 15px; display: inline-block; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드 및 동기화
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

# [동기화 버튼] 상단 배치
t_col1, t_col2 = st.columns([8, 2])
with t_col2:
    if st.button("🔄 SYNC"):
        st.cache_data.clear()
        st.session_state.df = load_data()
        st.rerun()

if 'df' not in st.session_state: st.session_state.df = load_data()
df = st.session_state.df

# 5. 출제 로직 (50% 신규 보장)
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
    if isinstance(st.session_state.current_index, int) and st.session_state.current_index >= len(df):
        st.session_state.current_index = get_next_question(df)

    _, col, _ = st.columns([1, 10, 1])
    with col:
        st.markdown(f'<p style="text-align:center; color:#94a3b8; font-size:0.9rem;">{st.session_state.last_msg}</p>', unsafe_allow_html=True)
        
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<div class="cosmic-card"><p class="question-text">MISSION COMPLETE</p></div>', unsafe_allow_html=True)
            if st.button("RESTART"):
                st.session_state.q_levels = {}; st.session_state.solve_count = 0; st.session_state.state = "IDLE"; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<div class="cosmic-card"><p class="question-text">READY?</p></div>', unsafe_allow_html=True)
            if st.button("START MISSION (Space)"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            c_lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            w_lv = st.session_state.q_wrong_levels.get(st.session_state.current_index, 0)
            
            # 게이지 렌더링
            w_bars = "█" * min(w_lv, 15); w_empty = "░" * (15 - len(w_bars))
            c_bars = "█" * min(c_lv, 15); c_empty = "░" * (15 - len(c_bars))
            st.markdown(f'<div class="dual-gauge-container"><div class="gauge-row"><span class="wrong-side">{w_empty}{w_bars}</span><span class="center-line">|</span><span class="correct-side">{c_bars}{c_empty}</span></div></div>', unsafe_allow_html=True)
            
            st.markdown(f'<div class="cosmic-card"><span class="status-badge">{"🆕 NEW" if c_lv==0 else f"🔥 LV.{c_lv}"}</span><p class="question-text">{row["질문"]}</p></div>', unsafe_allow_html=True)
            if st.button("SHOW ANSWER (Space)"): st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            q_idx = st.session_state.current_index
            st.markdown(f'<div class="cosmic-card"><p class="answer-text">{row["정답"]}</p></div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("HARD (1)"):
                    st.session_state.q_levels[q_idx] = 1; df.at[q_idx, '오답횟수'] += 1; conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    st.session_state.schedules.setdefault(st.session_state.solve_count + 5, []).append(q_idx)
                    st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("NORM (2)"):
                    new_lv = st.session_state.q_levels.get(q_idx, 0) + 1
                    df.at[q_idx, '정상횟수'] += 1; 
                    if new_lv > 7: df.at[q_idx, '정답횟수'] += 1; del st.session_state.q_levels[q_idx]
                    else: st.session_state.q_levels[q_idx] = new_lv; st.session_state.schedules.setdefault(st.session_state.solve_count + FIBO_GAP[new_lv], []).append(q_idx)
                    conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c3:
                if st.button("EASY (3)"):
                    df.at[q_idx, '정답횟수'] = 5; conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    if q_idx in st.session_state.q_levels: del st.session_state.q_levels[q_idx]
                    st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        # 하단 바 (모바일에서 여백 줄임)
        tot = len(df); m_q = len(df[df['정답횟수'] >= 5]); r_q = len(st.session_state.q_levels); n_q = tot - m_q - r_q
        st.markdown(f'<div class="progress-container"><div class="bar-mastered" style="width:{(m_q/tot)*100}%"></div><div class="bar-review" style="width:{(r_q/tot)*100}%"></div><div class="bar-new" style="width:{(n_q/tot)*100}%"></div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; justify-content:space-between; padding:5px; font-size:0.8rem;"><p>✅{m_q}</p><p>🔥{r_q}</p><p>🆕{n_q}</p></div>', unsafe_allow_html=True)

# 7. 단축키 엔진
components.html("""<script>const doc = window.parent.document;doc.addEventListener('keydown', function(e) {if (e.code === 'Space') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('Space')); if (btn) btn.click(); }else if (e.key === '1') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('HARD')); if (btn) btn.click(); }else if (e.key === '2') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('NORM')); if (btn) btn.click(); }else if (e.key === '3') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('EASY')); if (btn) btn.click(); }});</script>""", height=0)
