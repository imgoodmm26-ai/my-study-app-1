import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="감평 데이터 마스터 (단축키 복구)", layout="wide")

# 2. 세션 및 피보나치 설정
is_pc = not any(x in st.context.headers.get("User-Agent", "").lower() for x in ["iphone", "ipad", "android", "mobile"])
FIBO_GAP = [0, 5, 13, 21, 34, 55, 89, 144] 

if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} 
if 'q_wrong_levels' not in st.session_state: st.session_state.q_wrong_levels = {}
if 'schedules' not in st.session_state: st.session_state.schedules = {} 
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0

# 3. 디자인 설정 (디자인 유지 및 하얀 버튼 방지)
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    .dual-gauge-container { display: flex; flex-direction: column; align-items: center; margin-bottom: 35px; }
    .gauge-row { font-size: 2.2rem; font-family: monospace; display: flex; align-items: center; gap: 15px; }
    .wrong-side { color: #e74c3c; text-align: right; width: 180px; }
    .correct-side { color: #9b59b6; text-align: left; width: 180px; }
    .center-line { color: #555; font-weight: bold; }
    .question-text { font-size: 3.5rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 25px 0; line-height: 1.3; }
    .answer-text { font-size: 4.0rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 25px 0; line-height: 1.3; }
    
    div.stButton > button { 
        width: 100%; height: 110px !important; 
        font-size: 1.8rem !important; font-weight: bold !important; 
        border-radius: 30px !important; 
        color: white !important; 
        background-color: #34495e !important; 
        border: 2px solid #555 !important; 
    }
    .progress-container { width: 100%; background-color: #222; border-radius: 10px; margin-top: 100px; display: flex; height: 18px; overflow: hidden; border: 1px solid #444; }
    .bar-mastered { background-color: #2ecc71; }
    .bar-review { background-color: #e74c3c; }
    .bar-new { background-color: #3498db; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드 (7개 열 읽기)
conn = st.connection("gsheets", type=GSheetsConnection)
@st.cache_data(ttl=1)
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        df = conn.read(spreadsheet=url, worksheet=0, usecols=[0,1,2,3,4,5,6])
        df.columns = ['질문', '정답', '정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']
        for col in ['정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']:
            df[col] = pd.to_numeric(df[col]).fillna(0).astype(int)
        return df
    except: return None

df = load_data()

# 5. 듀얼 게이지 렌더링
def render_dual_gauge(correct_lv, wrong_lv):
    w_bars = "█" * min(wrong_lv, 7); w_empty = "░" * (7 - len(w_bars))
    c_bars = "█" * min(correct_lv, 7); c_empty = "░" * (7 - len(c_bars))
    return f'<div class="dual-gauge-container"><div class="gauge-row"><span class="wrong-side">{w_empty}{w_bars}</span><span class="center-line">|</span><span class="correct-side">{c_bars}{c_empty}</span></div></div>'

# 6. 출제 로직
def get_next_question(dataframe):
    curr_cnt = st.session_state.solve_count
    pending = [k for k in st.session_state.schedules.keys() if k <= curr_cnt and st.session_state.schedules[k]]
    if pending: return st.session_state.schedules[pending[0]].pop(0)
    all_sched = [idx for sublist in st.session_state.schedules.values() for idx in sublist]
    avail = [i for i in range(len(dataframe)) if int(dataframe.iloc[i]['정답횟수']) < 5 and i not in all_sched]
    if avail: return random.choice(avail)
    future = sorted([k for k in st.session_state.schedules.keys() if k > curr_cnt and st.session_state.schedules[k]])
    if future: return st.session_state.schedules[future[0]].pop(0)
    return "GRADUATED"

# --- 7. 화면 구성 ---
if df is not None:
    _, col, _ = st.columns([1, 10, 1])
    with col:
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 모든 회독 완료! 🎊</p>', unsafe_allow_html=True)
            if st.button("다시 시작하기"):
                st.session_state.q_levels = {}; st.session_state.q_wrong_levels = {}; st.session_state.schedules = {}; st.session_state.solve_count = 0
                st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">단축키 복구 인출 시스템</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기 (Space)"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            st.markdown(render_dual_gauge(st.session_state.q_levels.get(st.session_state.current_index, 0), st.session_state.q_wrong_levels.get(st.session_state.current_index, 0)), unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기 (Space)"): st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            q_idx = st.session_state.current_index
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("어려움/헷갈림 (1/Alt)"):
                    st.session_state.q_wrong_levels[q_idx] = st.session_state.q_wrong_levels.get(q_idx, 0) + 1
                    st.session_state.q_levels[q_idx] = 1
                    if is_pc:
                        try:
                            df.iloc[q_idx, 3] += 1 # 오답횟수
                            df.iloc[q_idx, 4] += 1 # 어려움횟수
                            conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                        except: pass
                    target = st.session_state.solve_count + 5
                    if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                    st.session_state.schedules[target].append(q_idx)
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("정상/알겠음 (2/Ctrl)"):
                    new_lv = st.session_state.q_levels.get(q_idx, 0) + 1
                    if is_pc:
                        try:
                            df.iloc[q_idx, 5] += 1 # 정상횟수
                            if new_lv > 7: df.iloc[q_idx, 2] += 1 # 정답횟수
                            conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                        except: pass
                    if new_lv > 7:
                        if q_idx in st.session_state.q_levels: del st.session_state.q_levels[q_idx]
                    else:
                        st.session_state.q_levels[q_idx] = new_lv
                        target = st.session_state.solve_count + FIBO_GAP[new_lv]
                        if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                        st.session_state.schedules[target].append(q_idx)
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c3:
                if st.button("너무 쉬움/졸업"):
                    if is_pc:
                        try:
                            df.iloc[q_idx, 2] += 1 # 정답횟수
                            df.iloc[q_idx, 6] += 1 # 쉬움횟수
                            conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                        except: pass
                    if q_idx in st.session_state.q_levels: del st.session_state.q_levels[q_idx]
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        # 하단 상태바
        tot = len(df); m_q = len(df[df['정답횟수'] >= 5]); r_q = len(st.session_state.q_levels); n_q = tot - m_q - r_q
        st.markdown(f'<div class="progress-container"><div class="bar-mastered" style="width:{(m_q/tot)*100}%"></div><div class="bar-review" style="width:{(r_q/tot)*100}%"></div><div class="bar-new" style="width:{(n_q/tot)*100}%"></div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; justify-content:space-between; padding:10px;"><p>✅정복:{m_q}</p><p>🔥복습:{r_q}</p><p>🆕남은새문제:{n_q}</p></div>', unsafe_allow_html=True)

# 8. [핵심] 단축키 엔진 (Ctrl, Alt, 1, 2 모두 지원)
components.html("""
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.code === 'Space') {
            e.preventDefault();
            const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('확인') || el.innerText.includes('시작'));
            if (btn) btn.click();
        } else if (e.key === 'Control' || e.key === '2') {
            const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('정상'));
            if (btn) btn.click();
        } else if (e.key === 'Alt' || e.key === '1') {
            e.preventDefault();
            const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('어려움'));
            if (btn) btn.click();
        }
    });
    </script>
""", height=0)
