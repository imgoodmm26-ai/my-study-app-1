import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="감평 메모리 마스터", layout="wide")

# 2. 세션 및 피보나치 설정 (맞춘 문제는 기하급수적으로 멀어짐)
is_pc = not any(x in st.context.headers.get("User-Agent", "").lower() for x in ["iphone", "ipad", "android", "mobile"])

# 레벨별 복습 간격 (Lv 1~7)
FIBO_GAP = [0, 5, 13, 21, 34, 55, 89, 144] 

if 'session_scores' not in st.session_state: st.session_state.session_scores = {} 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} 
if 'schedules' not in st.session_state: st.session_state.schedules = {} 
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0

# 3. 디자인 설정 (기억 강도 게이지 및 하단바 위치 조정)
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    .info-text { font-size: 1.1rem !important; color: #888; text-align: center; }
    
    /* 기억 강도 게이지 스타일 */
    .memory-gauge-container { display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; }
    .memory-bars { font-size: 2.2rem; letter-spacing: 3px; margin-bottom: 5px; font-family: monospace; }
    .strength-label { font-size: 0.9rem; font-weight: bold; padding: 4px 18px; border-radius: 20px; }
    
    .question-text { font-size: 3.5rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 25px 0; line-height: 1.3; }
    .answer-text { font-size: 3.5rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 25px 0; line-height: 1.3; }
    
    /* 하단 상태바 위치 (더 아래로) */
    .progress-container { width: 100%; background-color: #222; border-radius: 10px; margin-top: 150px; display: flex; height: 18px; overflow: hidden; border: 1px solid #444; }
    .bar-mastered { background-color: #2ecc71; }
    .bar-review { background-color: #e74c3c; }
    .bar-new { background-color: #3498db; }
    .bar-stats { display: flex; justify-content: space-between; padding: 10px 5px; }
    
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
        df['정답횟수'] = pd.to_numeric(df['정답횟수']).fillna(0).astype(int)
        return df
    except: return None

df = load_data()

# 5. [수정] 세분화된 기억 강도 렌더링 (7칸 대응)
def render_memory_gauge(level):
    # 각 레벨에 따른 시각적 피드백
    gauge_map = {
        0: ("░░░░░░░", "NEW (새로운 자극)", "#3498db"),
        1: ("█░░░░░░", "DANGER (기억 불안정)", "#e74c3c"),
        2: ("██░░░░░", "WARNING (약한 고리)", "#e67e22"),
        3: ("███░░░░", "GOOD (인식 시작)", "#f1c40f"),
        4: ("████░░░", "STABLE (기억 안착)", "#27ae60"),
        5: ("█████░░", "STRONG (장기 기억화)", "#2ecc71"),
        6: ("██████░", "EXPERT (숙달 완료)", "#1abc9c"),
        7: ("███████", "MASTERED (졸업 준비)", "#9b59b6")
    }
    bars, label, color = gauge_map.get(level, gauge_map[7])
    
    return f"""
    <div class="memory-gauge-container">
        <div class="memory-bars" style="color: {color};">{bars}</div>
        <div class="strength-label" style="background-color: {color}; color: white;">{label}</div>
    </div>
    """

# 6. 하이브리드 출제 로직
def get_next_question(dataframe):
    curr_cnt = st.session_state.solve_count
    pending_keys = [k for k in st.session_state.schedules.keys() if k <= curr_cnt and st.session_state.schedules[k]]
    if pending_keys: return st.session_state.schedules[pending_keys[0]].pop(0)

    all_scheduled = [idx for sublist in st.session_state.schedules.values() for idx in sublist]
    available_new = [i for i in range(len(dataframe)) if int(dataframe.iloc[i]['정답횟수']) < 5 and i not in all_scheduled]
    if available_new: return random.choice(available_new)
    
    future_keys = sorted([k for k in st.session_state.schedules.keys() if k > curr_cnt and st.session_state.schedules[k]])
    if future_keys: return st.session_state.schedules[future_keys[0]].pop(0)
    return "GRADUATED"

# --- 7. 화면 구성 ---
if df is not None:
    _, col, _ = st.columns([1, 10, 1])
    with col:
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 회계학 전 문항 정복! 🎊</p>', unsafe_allow_html=True)
            if st.button("다시 시작하기"):
                st.session_state.q_levels = {}; st.session_state.schedules = {}; st.session_state.solve_count = 0
                st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">기억 강도 기반 인출 훈련</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기 (Space)", type="primary"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            
            st.markdown(render_memory_gauge(lv), unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기 (Space)"): st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            q_idx = st.session_state.current_index
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("맞음 (Ctrl)", type="primary"):
                    curr_lv = st.session_state.q_levels.get(q_idx, 0)
                    new_lv = curr_lv + 1
                    
                    if new_lv > 7: # Lv.7 통과 시 시트 반영
                        if is_pc:
                            try:
                                df.iloc[q_idx, 2] += 1
                                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                            except: pass
                        if q_idx in st.session_state.q_levels: del st.session_state.q_levels[q_idx]
                    else:
                        st.session_state.q_levels[q_idx] = new_lv
                        # 맞힌 레벨이 높을수록 훨씬 뒤로 보냄
                        target = st.session_state.solve_count + FIBO_GAP[new_lv]
                        if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                        st.session_state.schedules[target].append(q_idx)
                    
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("틀림 (Alt)"):
                    # 틀리면 즉시 Lv.1로 강등 및 5장 뒤 예약
                    st.session_state.q_levels[q_idx] = 1
                    target = st.session_state.solve_count + 5 
                    if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                    st.session_state.schedules[target].append(q_idx)
                    
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        # --- 📊 하단 통합 상태바 ---
        total_q = len(df)
        mastered_q = len(df[df['정답횟수'] >= 5])
        reviewing_q = len(st.session_state.q_levels)
        new_q = total_q - mastered_q - reviewing_q
        st.markdown(f"""
            <div class="progress-container">
                <div class="bar-mastered" style="width: {(mastered_q/total_q)*100}%"></div>
                <div class="bar-review" style="width: {(reviewing_q/total_q)*100}%"></div>
                <div class="bar-new" style="width: {(new_q/total_q)*100}%"></div>
            </div>
            <div class="bar-stats">
                <p class="info-text">✅ 정복: {mastered_q}</p>
                <p class="info-text">🔥 복습 중: {reviewing_q}</p>
                <p class="info-text">🆕 신규: {new_q}</p>
            </div>
        """, unsafe_allow_html=True)

# 8. 단축키 엔진
components.html("""
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.code === 'Space') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('확인') || el.innerText.includes('시작')); if (btn) btn.click(); }
        else if (e.key === 'Control') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('맞음')); if (btn) btn.click(); }
        else if (e.key === 'Alt') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('틀림')); if (btn) btn.click(); }
    });
    </script>
""", height=0)
