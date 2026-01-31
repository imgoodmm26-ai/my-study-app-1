import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="감평 몰입 인출기 PRO", layout="wide")

# 2. 세션 및 피보나치 설정
FIBO_GAP = [0, 5, 13, 21, 34, 55, 89, 144] 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} 
if 'q_wrong_levels' not in st.session_state: st.session_state.q_wrong_levels = {}
if 'schedules' not in st.session_state: st.session_state.schedules = {} 
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0
if 'last_msg' not in st.session_state: st.session_state.last_msg = "시스템 가동. 오늘 목표를 향해 달립시다!"

# 3. 디자인 설정 (버튼 사이즈 2/3 축소 및 반응형)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    .stApp { background-color: black; color: white; font-family: 'Noto Sans KR', sans-serif; }
    
    .feedback-text { font-size: 1.1rem !important; color: #00d4ff; font-weight: bold; text-align: center; margin-bottom: 15px; height: 35px; }
    .status-badge { font-size: 0.85rem; font-weight: bold; padding: 4px 15px; border-radius: 20px; margin-bottom: 15px; display: inline-block; }
    .badge-new { background-color: #f1c40f; color: black; }
    .badge-review { background-color: #3498db; color: white; }
    
    /* 듀얼 게이지 스타일 */
    .dual-gauge-container { display: flex; flex-direction: column; align-items: center; margin-bottom: 25px; width: 100%; }
    .gauge-row { font-size: 1.8rem; font-family: monospace; display: flex; align-items: center; justify-content: center; width: 100%; white-space: nowrap; }
    .wrong-side { color: #e74c3c; text-align: right; width: 40vw; max-width: 450px; }
    .correct-side { color: #9b59b6; text-align: left; width: 40vw; max-width: 450px; }
    .center-line { color: #555; font-weight: bold; margin: 0 10px; }
    
    .question-text { font-size: clamp(1.4rem, 4vw, 3.2rem) !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 15px 0; line-height: 1.3; }
    .answer-text { font-size: clamp(1.6rem, 5vw, 3.8rem) !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 15px 0; line-height: 1.3; }
    
    /* [수정] 버튼 사이즈 2/3 축소 (110px -> 75px) */
    div.stButton > button { 
        width: 100% !important; 
        height: clamp(55px, 8vh, 75px) !important; 
        font-size: clamp(0.9rem, 2.5vw, 1.5rem) !important; 
        font-weight: bold !important; 
        border-radius: 20px !important; 
        color: white !important; 
        background-color: #1e293b !important; 
        border: 1px solid #334155 !important; 
    }
    
    .progress-container { width: 100%; background-color: #222; border-radius: 10px; margin-top: 40px; display: flex; height: 10px; overflow: hidden; }
    .bar-mastered { background-color: #2ecc71; } .bar-review { background-color: #e74c3c; } .bar-new { background-color: #3498db; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드
conn = st.connection("gsheets", type=GSheetsConnection)
@st.cache_data(ttl=1)
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        df_raw = conn.read(spreadsheet=url, worksheet=0)
        df = df_raw.iloc[:, :7]
        df.columns = ['질문', '정답', '정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']
        df = df.dropna(subset=['질문', '정답']).reset_index(drop=True)
        for col in ['정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df
    except: return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()
df = st.session_state.df

# 5. 출제 로직
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
    t_col1, t_col2 = st.columns([7, 3])
    with t_col2:
        if st.button("🔄 데이터 동기화", key="sync_btn"):
            st.cache_data.clear()
            st.session_state.df = load_data()
            st.session_state.last_msg = f"동기화 완료: {len(st.session_state.df)}문항"
            st.rerun()

    if isinstance(st.session_state.current_index, int) and st.session_state.current_index >= len(df):
        st.session_state.current_index = get_next_question(df)

    _, col, _ = st.columns([1, 10, 1])
    with col:
        st.markdown(f'<p class="feedback-text">{st.session_state.last_msg}</p>', unsafe_allow_html=True)
        
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 모든 문항 정복 완료! 🎊</p>', unsafe_allow_html=True)
            if st.button("처음부터 다시 시작하기"):
                st.session_state.q_levels = {}; st.session_state.solve_count = 0
                st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">준비되셨나요?</p>', unsafe_allow_html=True)
            if st.button("시작하기 (Space)"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            c_lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            w_lv = st.session_state.q_wrong_levels.get(st.session_state.current_index, 0)
            
            label = f'<div style="text-align:center;"><span class="status-badge badge-new">🆕 신규 문항</span></div>' if c_lv == 0 else f'<div style="text-align:center;"><span class="status-badge badge-review">🔥 Lv.{c_lv} 복습</span></div>'
            st.markdown(label, unsafe_allow_html=True)
            
            w_bars = "█" * min(w_lv, 20); w_empty = "░" * (20 - len(w_bars))
            c_bars = "█" * min(c_lv, 20); c_empty = "░" * (20 - len(c_bars))
            st.markdown(f'<div class="dual-gauge-container"><div class="gauge-row"><span class="wrong-side">{w_empty}{w_bars}</span><span class="center-line">|</span><span class="correct-side">{c_bars}{c_empty}</span></div></div>', unsafe_allow_html=True)
            
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인 (Space)"): st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            q_idx = st.session_state.current_index
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("어려움 (1/Ctrl)"):
                    st.session_state.q_wrong_levels[q_idx] = st.session_state.q_wrong_levels.get(q_idx, 0) + 1
                    st.session_state.q_levels[q_idx] = 1
                    df.at[q_idx, '오답횟수'] += 1; df.at[q_idx, '어려움횟수'] += 1
                    try: conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except: pass
                    st.session_state.schedules.setdefault(st.session_state.solve_count + 5, []).append(q_idx)
                    st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("정상 (2/Alt)"):
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
                if st.button("너무 쉬움 (3)"):
                    df.at[q_idx, '정답횟수'] = 5; df.at[q_idx, '쉬움횟수'] += 1
                    try: conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except: pass
                    if q_idx in st.session_state.q_levels: del st.session_state.q_levels[q_idx]
                    st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        tot = len(df); m_q = len(df[df['정답횟수'] >= 5]); r_q = len(st.session_state.q_levels); n_q = tot - m_q - r_q
        st.markdown(f'<div class="progress-container"><div class="bar-mastered" style="width:{(m_q/tot)*100}%"></div><div class="bar-review" style="width:{(r_q/tot)*100}%"></div><div class="bar-new" style="width:{(n_q/tot)*100}%"></div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; justify-content:space-between; padding:5px; font-size:0.8rem;"><p>✅정복:{m_q}</p><p>🔥복습:{r_q}</p><p>🆕신규:{n_q}</p></div>', unsafe_allow_html=True)

# 7. 단축키 엔진 (한글 이름에 맞춰 재매핑)
components.html("""<script>const doc = window.parent.document;doc.addEventListener('keydown', function(e) {if (e.code === 'Space') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('확인') || el.innerText.includes('시작')); if (btn) btn.click(); }else if (e.key === 'Control' || e.key === '1') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('어려움')); if (btn) btn.click(); }else if (e.key === 'Alt' || e.key === '2') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('정상')); if (btn) btn.click(); }else if (e.key === '3') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('쉬움')); if (btn) btn.click(); }});</script>""", height=0)
