import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="감평 몰입 인출기", layout="wide")

# 2. 세션 및 피보나치 설정
FIBO_GAP = [0, 5, 13, 21, 34, 55, 89, 144] 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} 
if 'q_wrong_levels' not in st.session_state: st.session_state.q_wrong_levels = {}
if 'schedules' not in st.session_state: st.session_state.schedules = {} 
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0
if 'last_msg' not in st.session_state: st.session_state.last_msg = "훈련을 시작할 준비가 되셨나요?"

# 3. 디자인 설정 (강화된 피드백 메시지 스타일 추가)
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    .feedback-text { font-size: 1.4rem !important; color: #00d4ff; font-weight: bold; text-align: center; margin-bottom: 5px; height: 30px; }
    .status-badge { font-size: 1rem; font-weight: bold; padding: 4px 12px; border-radius: 15px; margin-bottom: 10px; display: inline-block; }
    .badge-new { background-color: #f1c40f; color: black; }
    .badge-review { background-color: #3498db; color: white; }
    
    .dual-gauge-container { display: flex; flex-direction: column; align-items: center; margin-bottom: 35px; }
    .gauge-row { font-size: 2.2rem; font-family: monospace; display: flex; align-items: center; gap: 15px; }
    .wrong-side { color: #e74c3c; text-align: right; width: 180px; }
    .correct-side { color: #9b59b6; text-align: left; width: 180px; }
    .center-line { color: #555; font-weight: bold; }
    
    .question-text { font-size: 3.5rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 20px 0; line-height: 1.3; }
    .answer-text { font-size: 4.0rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 20px 0; line-height: 1.3; }
    
    div.stButton > button { width: 100% !important; height: 110px !important; font-size: 1.8rem !important; font-weight: bold !important; border-radius: 30px !important; color: white !important; background-color: #34495e !important; border: 2px solid #555 !important; }
    div.stButton > button:hover { border-color: #f1c40f !important; }

    .progress-container { width: 100%; background-color: #222; border-radius: 10px; margin-top: 100px; display: flex; height: 18px; overflow: hidden; border: 1px solid #444; }
    .bar-mastered { background-color: #2ecc71; }
    .bar-review { background-color: #e74c3c; }
    .bar-new { background-color: #3498db; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드 (빈 줄 제거 & 인덱스 리셋)
conn = st.connection("gsheets", type=GSheetsConnection)
@st.cache_data(ttl=1)
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        df_raw = conn.read(spreadsheet=url, worksheet=0)
        df = df_raw.iloc[:, :7]
        df.columns = ['질문', '정답', '정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']
        df = df.dropna(subset=['질문'])
        df = df[df['질문'].astype(str).str.strip() != ""]
        for col in ['정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']:
            df[col] = pd.to_numeric(df[col]).fillna(0).astype(int)
        return df.reset_index(drop=True)
    except: return None

df = load_data()

# 5. 유틸리티 로직
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
    if isinstance(st.session_state.current_index, int) and st.session_state.current_index >= len(df):
        st.session_state.current_index = get_next_question(df)

    _, col, _ = st.columns([1, 10, 1])
    with col:
        # 상단 메시지 및 라벨 영역
        st.markdown(f'<p class="feedback-text">{st.session_state.last_msg}</p>', unsafe_allow_html=True)
        
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 모든 회독 목표 달성! 🎊</p>', unsafe_allow_html=True)
            if st.button("처음부터 다시 시작하기"):
                st.session_state.q_levels = {}; st.session_state.q_wrong_levels = {}; st.session_state.schedules = {}; st.session_state.solve_count = 0
                st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">데이터 기반 인출 시스템</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기 (Space)"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            c_lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            w_lv = st.session_state.q_wrong_levels.get(st.session_state.current_index, 0)
            
            # [신규] 라벨 표시
            badge_html = '<div style="text-align:center;">'
            if c_lv == 0: badge_html += '<span class="status-badge badge-new">🆕 신규 문항 등장!</span>'
            else: badge_html += f'<span class="status-badge badge-review">🔥 Lv.{c_lv} 복습 중</span>'
            badge_html += '</div>'
            st.markdown(badge_html, unsafe_allow_html=True)

            # 게이지 렌더링
            w_bars = "█" * min(w_lv, 7); w_empty = "░" * (7 - len(w_bars))
            c_bars = "█" * min(c_lv, 7); c_empty = "░" * (7 - len(c_bars))
            st.markdown(f'<div class="dual-gauge-container"><div class="gauge-row"><span class="wrong-side">{w_empty}{w_bars}</span><span class="center-line">|</span><span class="correct-side">{c_bars}{c_empty}</span></div></div>', unsafe_allow_html=True)
            
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기 (Space)"): st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            q_idx = st.session_state.current_index
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("어려움/헷갈림 (1/Ctrl)"):
                    st.session_state.q_wrong_levels[q_idx] = st.session_state.q_wrong_levels.get(q_idx, 0) + 1
                    st.session_state.q_levels[q_idx] = 1
                    st.session_state.last_msg = random.choice(["이 고비가 실력이 됩니다!", "망각 곡선을 이겨내세요.", "5장 뒤에 다시 공략합시다!"])
                    try:
                        df.at[q_idx, '오답횟수'] += 1; df.at[q_idx, '어려움횟수'] += 1
                        conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except: pass
                    target = st.session_state.solve_count + 5
                    if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                    st.session_state.schedules[target].append(q_idx)
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("정상/알겠음 (2/Alt)"):
                    new_lv = st.session_state.q_levels.get(q_idx, 0) + 1
                    st.session_state.last_msg = random.choice(["뇌세포가 강화되었습니다!", "장기 기억 저장소로 이동 중!", "훌륭한 인출 성공입니다."])
                    try:
                        df.at[q_idx, '정상횟수'] += 1
                        if new_lv > 7: 
                            df.at[q_idx, '정답횟수'] += 1
                            st.session_state.last_msg = "🎊 한 문항 마스터! 졸업을 축하합니다."
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
                    st.session_state.last_msg = "완벽히 정복하셨군요! 목록에서 제외합니다."
                    try:
                        df.at[q_idx, '정답횟수'] += 1; df.at[q_idx, '쉬움횟수'] += 1
                        conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except: pass
                    if q_idx in st.session_state.q_levels: del st.session_state.q_levels[q_idx]
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        # 하단 바
        tot = len(df); m_q = len(df[df['정답횟수'] >= 5]); r_q = len(st.session_state.q_levels); n_q = tot - m_q - r_q
        st.markdown(f'<div class="progress-container"><div class="bar-mastered" style="width:{(m_q/tot)*100}%"></div><div class="bar-review" style="width:{(r_q/tot)*100}%"></div><div class="bar-new" style="width:{(n_q/tot)*100}%"></div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; justify-content:space-between; padding:10px;"><p>✅정복:{m_q}</p><p>🔥복습:{r_q}</p><p>🆕남은새문제:{n_q}</p></div>', unsafe_allow_html=True)

# 7. 단축키 엔진
components.html("""
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.code === 'Space') {
            e.preventDefault();
            const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('확인') || el.innerText.includes('시작'));
            if (btn) btn.click();
        } else if (e.key === 'Control' || e.key === '1') {
            const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('어려움'));
            if (btn) btn.click();
        } else if (e.key === 'Alt' || e.key === '2') {
            e.preventDefault();
            const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('정상'));
            if (btn) btn.click();
        }
    });
    </script>
""", height=0)
