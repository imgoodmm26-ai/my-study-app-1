import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="감평 와이드 인출기: PRO", layout="wide")

# 2. 세션 및 피보나치 설정
FIBO_GAP = [0, 5, 13, 21, 34, 55, 89, 144] 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} 
if 'q_wrong_levels' not in st.session_state: st.session_state.q_wrong_levels = {}
if 'schedules' not in st.session_state: st.session_state.schedules = {} 
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0
if 'last_msg' not in st.session_state: st.session_state.last_msg = "시스템 온라인. 데이터를 최적화 중입니다."

# 3. 디자인 설정 (반응형 최적화 추가)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    .stApp { background-color: black; color: white; font-family: 'Noto Sans KR', sans-serif; }
    
    .feedback-text { font-size: 1.2rem !important; color: #00d4ff; font-weight: bold; text-align: center; margin-bottom: 15px; height: 35px; }
    .status-badge { font-size: 0.9rem; font-weight: bold; padding: 4px 15px; border-radius: 20px; margin-bottom: 15px; display: inline-block; }
    .badge-new { background-color: #f1c40f; color: black; }
    .badge-review { background-color: #3498db; color: white; }
    
    /* 듀얼 게이지 반응형 스타일 */
    .dual-gauge-container { display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; width: 100%; }
    .gauge-row { font-size: 1.8rem; font-family: monospace; display: flex; align-items: center; justify-content: center; width: 100%; white-space: nowrap; }
    .wrong-side { color: #e74c3c; text-align: right; width: 40vw; max-width: 400px; }
    .correct-side { color: #9b59b6; text-align: left; width: 40vw; max-width: 400px; }
    .center-line { color: #555; font-weight: bold; margin: 0 10px; }
    
    /* 텍스트 반응형 (PC/모바일 공통) */
    .question-text { font-size: clamp(1.5rem, 5vw, 3.5rem) !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 20px 0; line-height: 1.3; }
    .answer-text { font-size: clamp(1.8rem, 6vw, 4.0rem) !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 20px 0; line-height: 1.3; }
    
    div.stButton > button { width: 100% !important; height: clamp(60px, 10vh, 110px) !important; font-size: clamp(1rem, 3vw, 1.8rem) !important; font-weight: bold !important; border-radius: 25px !important; color: white !important; background-color: #1e293b !important; border: 1px solid #334155 !important; }
    
    .progress-container { width: 100%; background-color: #222; border-radius: 10px; margin-top: 50px; display: flex; height: 12px; overflow: hidden; }
    .bar-mastered { background-color: #2ecc71; } .bar-review { background-color: #e74c3c; } .bar-new { background-color: #3498db; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드 (스마트 범위 자동 지정)
conn = st.connection("gsheets", type=GSheetsConnection)
@st.cache_data(ttl=1)
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        df_raw = conn.read(spreadsheet=url, worksheet=0)
        
        # [수정] 내용이 존재하는 열(최대 7개)과 행만 필터링
        df = df_raw.iloc[:, :7]
        df.columns = ['질문', '정답', '정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']
        
        # [수정] 질문이나 정답 중 하나라도 비어있으면 아예 제외 ( nan 방지 )
        df = df.dropna(subset=['질문', '정답'])
        df = df[df['질문'].astype(str).str.strip() != ""]
        
        for col in ['정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        return df.reset_index(drop=True)
    except: return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 5. 출제 로직 (50% 신규 보장 하이브리드)
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
    
    future_keys = sorted([k for k in st.session_state.schedules.keys() if k > curr_cnt and st.session_state.schedules[k]])
    if future_keys: return st.session_state.schedules[future_keys[0]].pop(0)
    return "GRADUATED"

# --- 6. 메인 화면 ---
df = st.session_state.df

if df is not None:
    t_col1, t_col2 = st.columns([7, 3])
    with t_col2:
        if st.button("🔄 SYNC DATA", key="sync_btn"):
            st.cache_data.clear()
            st.session_state.df = load_data()
            st.session_state.last_msg = f"SYNC COMPLETE: {len(st.session_state.df)}문항 로드됨"
            st.rerun()

    if isinstance(st.session_state.current_index, int) and st.session_state.current_index >= len(df):
        st.session_state.current_index = get_next_question(df)

    _, col, _ = st.columns([1, 10, 1])
    with col:
        st.markdown(f'<p class="feedback-text">{st.session_state.last_msg}</p>', unsafe_allow_html=True)
        
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 모든 문항 MISSION COMPLETE! 🎊</p>', unsafe_allow_html=True)
            if st.button("REBOOT SYSTEM (다시 시작)"):
                st.session_state.q_levels = {}; st.session_state.solve_count = 0
                st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">READY FOR INITIATION?</p>', unsafe_allow_html=True)
            if st.button("START MISSION (Space)"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            c_lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            w_lv = st.session_state.q_wrong_levels.get(st.session_state.current_index, 0)
            
            label = f'<div style="text-align:center;"><span class="status-badge badge-new">🆕 신규 타겟</span></div>' if c_lv == 0 else f'<div style="text-align:center;"><span class="status-badge badge-review">🔥 Lv.{c_lv} 복습 중</span></div>'
            st.markdown(label, unsafe_allow_html=True)
            
            # 게이지 렌더링
            w_bars = "█" * min(w_lv, 15); w_empty = "░" * (15 - len(w_bars))
            c_bars = "█" * min(c_lv, 15); c_empty = "░" * (15 - len(c_bars))
            st.markdown(f'<div class="dual-gauge-container"><div class="gauge-row"><span class="wrong-side">{w_empty}{w_bars}</span><span class="center-line">|</span><span class="correct-side">{c_bars}{c_empty}</span></div></div>', unsafe_allow_html=True)
            
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("IDENTIFY TARGET (Space)"): st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            q_idx = st.session_state.current_index
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("HARD (1/Ctrl)"):
                    st.session_state.q_wrong_levels[q_idx] = st.session_state.q_wrong_levels.get(q_idx, 0) + 1
                    st.session_state.q_levels[q_idx] = 1
                    df.at[q_idx, '오답횟수'] += 1; df.at[q_idx, '어려움횟수'] += 1
                    try: conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except: pass
                    st.session_state.schedules.setdefault(st.session_state.solve_count + 5, []).append(q_idx)
                    st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("NORM (2/Alt)"):
                    new_lv = st.session_state.q_levels.get(q_idx, 0) + 1
                    df.at[q_idx, '정상횟수'] += 1
                    if new_lv > 7: df.at[q_idx, '정답횟수'] += 1
                    try: conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except: pass
                    if new_lv > 7: del st.session_state.q_levels[q_idx]
                    else:
                        st.session_state.q_levels[q_idx] = new_lv
                        st.session_state.schedules.setdefault(st.session_state.solve_count + FIBO_GAP[min(new_lv, 7)], []).append(q_idx)
                    st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c3:
                if st.button("EASY (3)"):
                    df.at[q_idx, '정답횟수'] = 5; df.at[q_idx, '쉬움횟수'] += 1
                    try: conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except: pass
                    if q_idx in st.session_state.q_levels: del st.session_state.q_levels[q_idx]
                    st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        # 하단 바
        tot = len(df); m_q = len(df[df['정답횟수'] >= 5]); r_q = len(st.session_state.q_levels); n_q = tot - m_q - r_q
        st.markdown(f'<div class="progress-container"><div class="bar-mastered" style="width:{(m_q/tot)*100}%"></div><div class="bar-review" style="width:{(r_q/tot)*100}%"></div><div class="bar-new" style="width:{(n_q/tot)*100}%"></div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; justify-content:space-between; padding:5px; font-size:0.8rem;"><p>✅GRAD:{m_q}</p><p>🔥REV:{r_q}</p><p>🆕NEW:{n_q}</p></div>', unsafe_allow_html=True)

# 7. 단축키 엔진
components.html("""<script>const doc = window.parent.document;doc.addEventListener('keydown', function(e) {if (e.code === 'Space') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('TARGET') || el.innerText.includes('START')); if (btn) btn.click(); }else if (e.key === 'Control' || e.key === '1') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('HARD')); if (btn) btn.click(); }else if (e.key === 'Alt' || e.key === '2') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('NORM')); if (btn) btn.click(); }else if (e.key === '3') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('EASY')); if (btn) btn.click(); }});</script>""", height=0)
