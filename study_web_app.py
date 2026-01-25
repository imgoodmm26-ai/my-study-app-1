import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="감평 듀얼 인출기", layout="wide")

# 2. 세션 초기화
is_pc = not any(x in st.context.headers.get("User-Agent", "").lower() for x in ["iphone", "ipad", "android", "mobile"])
FIBO_GAP = [0, 5, 13, 21, 34, 55, 89, 144] 

if 'session_scores' not in st.session_state: st.session_state.session_scores = {} 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} 
if 'q_wrong_levels' not in st.session_state: st.session_state.q_wrong_levels = {} # 틀린 레벨 저장
if 'schedules' not in st.session_state: st.session_state.schedules = {} 
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0

# 3. 디자인 설정
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    
    /* 듀얼 게이지 스타일 */
    .dual-gauge-container { display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; }
    .gauge-row { font-size: 2.2rem; font-family: monospace; display: flex; align-items: center; gap: 10px; }
    .wrong-side { color: #e74c3c; text-align: right; width: 180px; }
    .correct-side { color: #9b59b6; text-align: left; width: 180px; }
    .center-line { color: #555; font-weight: bold; }
    
    .label-row { display: flex; gap: 20px; margin-top: 10px; }
    .gauge-label { font-size: 0.8rem; font-weight: bold; padding: 2px 12px; border-radius: 10px; color: white; }

    .question-text { font-size: 3.5rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 25px 0; line-height: 1.3; }
    .answer-text { font-size: 3.5rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 25px 0; line-height: 1.3; }
    
    .progress-container { width: 100%; background-color: #222; border-radius: 10px; margin-top: 150px; display: flex; height: 18px; overflow: hidden; }
    .bar-mastered { background-color: #2ecc71; }
    .bar-review { background-color: #e74c3c; }
    .bar-new { background-color: #3498db; }
    
    div.stButton > button { width: 100%; height: 120px !important; font-size: 2.2rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
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

# 5. [신규] 듀얼 게이지 렌더링 함수
def render_dual_gauge(correct_lv, wrong_lv):
    # 틀린 쪽 (왼쪽으로 차오름)
    w_bars = "█" * min(wrong_lv, 7)
    w_empty = "░" * (7 - len(w_bars))
    wrong_visual = f"{w_empty}{w_bars}"
    
    # 맞은 쪽 (오른쪽으로 차오름)
    c_bars = "█" * min(correct_lv, 7)
    c_empty = "░" * (7 - len(c_bars))
    correct_visual = f"{c_bars}{c_empty}"
    
    w_label = "LEECH" if wrong_lv >= 5 else "WRONG" if wrong_lv > 0 else "CLEAN"
    c_label = "MASTERED" if correct_lv >= 7 else "LEARNING" if correct_lv > 0 else "NEW"

    return f"""
    <div class="dual-gauge-container">
        <div class="gauge-row">
            <span class="wrong-side">{wrong_visual}</span>
            <span class="center-line">|</span>
            <span class="correct-side">{correct_visual}</span>
        </div>
        <div class="label-row">
            <span class="gauge-label" style="background-color: #e74c3c;">{w_label} ({wrong_lv})</span>
            <span class="gauge-label" style="background-color: #9b59b6;">{c_label} ({correct_lv})</span>
        </div>
    </div>
    """

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

# --- 6. 화면 구성 ---
if df is not None:
    _, col, _ = st.columns([1, 10, 1])
    with col:
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 회계학 듀얼 훈련 완료! 🎊</p>', unsafe_allow_html=True)
            if st.button("다시 시작하기"):
                st.session_state.q_levels = {}; st.session_state.q_wrong_levels = {}
                st.session_state.schedules = {}; st.session_state.solve_count = 0
                st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">듀얼 게이지 인출 시스템</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기 (Space)", type="primary"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            c_lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            w_lv = st.session_state.q_wrong_levels.get(st.session_state.current_index, 0)
            
            st.markdown(render_dual_gauge(c_lv, w_lv), unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기 (Space)"): st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            q_idx = st.session_state.current_index
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("맞음 (Ctrl)", type="primary"):
                    st.session_state.q_levels[q_idx] = st.session_state.q_levels.get(q_idx, 0) + 1
                    if st.session_state.q_levels[q_idx] > 7:
                        if is_pc:
                            try:
                                df.iloc[q_idx, 2] += 1
                                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                            except: pass
                        del st.session_state.q_levels[q_idx]
                        if q_idx in st.session_state.q_wrong_levels: del st.session_state.q_wrong_levels[q_idx]
                    else:
                        target = st.session_state.solve_count + FIBO_GAP[st.session_state.q_levels[q_idx]]
                        if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                        st.session_state.schedules[target].append(q_idx)
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("틀림 (Alt)"):
                    # 틀림 레벨 증가 (최대 7)
                    st.session_state.q_wrong_levels[q_idx] = st.session_state.q_wrong_levels.get(q_idx, 0) + 1
                    st.session_state.q_levels[q_idx] = 1 # 정답 레벨은 1로 강등
                    
                    target = st.session_state.solve_count + 5 
                    if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                    st.session_state.schedules[target].append(q_idx)
                    
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        # 하단 바
        tot = len(df)
        m_q = len(df[df['정답횟수'] >= 5])
        r_q = len(st.session_state.q_levels)
        n_q = tot - m_q - r_q
        st.markdown(f'<div class="progress-container"><div class="bar-mastered" style="width:{(m_q/tot)*100}%"></div><div class="bar-review" style="width:{(r_q/tot)*100}%"></div><div class="bar-new" style="width:{(n_q/tot)*100}%"></div></div>', unsafe_allow_html=True)

# 단축키 엔진
components.html("""<script>const doc = window.parent.document;doc.addEventListener('keydown', function(e) {if (e.code === 'Space') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('확인') || el.innerText.includes('시작')); if (btn) btn.click(); }else if (e.key === 'Control') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('맞음')); if (btn) btn.click(); }else if (e.key === 'Alt') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('틀림')); if (btn) btn.click(); }});</script>""", height=0)
