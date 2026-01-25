import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="감평 마스터 인출기", layout="wide")

# 2. 세션 초기화 및 피보나치 확장 (맞춘 문제는 훨씬 뒤로 보냄)
is_pc = not any(x in st.context.headers.get("User-Agent", "").lower() for x in ["iphone", "ipad", "android", "mobile"])

# 맞춘 문제용 확장 간격 (Lv 1~7)
# 틀리면 무조건 5장 뒤(Lv.1), 맞히면 레벨에 따라 기하급수적으로 멀어짐
FIBO_GAP = [0, 5, 13, 21, 34, 55, 89, 144] 

if 'session_scores' not in st.session_state: st.session_state.session_scores = {} 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} 
if 'schedules' not in st.session_state: st.session_state.schedules = {} 
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0

# 3. 디자인 설정 (막대그래프 위치 하향 조정)
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    .info-text { font-size: 1.4rem !important; color: #aaaaaa; font-weight: bold; text-align: center; margin-bottom: 10px; }
    .question-text { font-size: 3.5rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 30px 0; line-height: 1.3; }
    .answer-text { font-size: 3.5rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 30px 0; line-height: 1.3; }
    
    /* 하단 상태바 스타일 - 위치를 더 아래로(margin-top 증가) */
    .progress-container { width: 100%; background-color: #333; border-radius: 10px; margin-top: 120px; display: flex; height: 25px; overflow: hidden; border: 1px solid #555; }
    .bar-mastered { background-color: #2ecc71; height: 100%; transition: width 0.5s; }
    .bar-review { background-color: #e74c3c; height: 100%; transition: width 0.5s; }
    .bar-new { background-color: #3498db; height: 100%; transition: width 0.5s; }
    .bar-label { font-size: 0.9rem; color: #888; text-align: center; margin-top: 8px; }
    
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
        return df
    except: return None

df = load_data()

# 5. 하이브리드 출제 로직 (신규 문제 우선 공급 + 정확한 예약 시점 노출)
def get_next_question(dataframe):
    curr_cnt = st.session_state.solve_count
    
    # [1순위] 현재 시점에 정확히 예약된 복습 문제가 있는가?
    pending_keys = [k for k in st.session_state.schedules.keys() if k <= curr_cnt and st.session_state.schedules[k]]
    if pending_keys:
        return st.session_state.schedules[pending_keys[0]].pop(0)

    # [2순위] 예약된 게 없다면 '무조건' 신규 문제부터 공급 (200개 소화 우선)
    all_scheduled = [idx for sublist in st.session_state.schedules.values() for idx in sublist]
    available_new = [i for i in range(len(dataframe)) if int(dataframe.iloc[i]['정답횟수']) < 5 and i not in all_scheduled]
    
    if available_new:
        return random.choice(available_new)
    
    # [3순위] 신규 문제도 없다면 미래 예약분 중 가장 가까운 것 당겨오기
    future_keys = sorted([k for k in st.session_state.schedules.keys() if k > curr_cnt and st.session_state.schedules[k]])
    if future_keys:
        return st.session_state.schedules[future_keys[0]].pop(0)
        
    return "GRADUATED"

# --- 6. 화면 구성 ---
if df is not None:
    _, col, _ = st.columns([1, 10, 1])
    with col:
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 회계학 완전 정복! 🎊</p>', unsafe_allow_html=True)
            if st.button("처음부터 다시 시작하기"):
                st.session_state.q_levels = {}; st.session_state.schedules = {}
                st.session_state.solve_count = 0; st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">회계학 확장 간격 인출</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기 (Space)", type="primary"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            st.markdown(f'<p class="info-text">총 풀이 수: {st.session_state.solve_count}장 | {"🆕 신규" if lv==0 else f"🔥 Lv.{lv} 복습"}</p>', unsafe_allow_html=True)
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
                    
                    if new_lv >= len(FIBO_GAP):
                        # [졸업] 모든 확장 간격을 통과했을 때만 시트 점수 반영
                        if is_pc:
                            try:
                                df.iloc[q_idx, 2] += 1
                                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                            except: pass
                        if q_idx in st.session_state.q_levels: del st.session_state.q_levels[q_idx]
                    else:
                        st.session_state.q_levels[q_idx] = new_lv
                        # [핵심] 맞힌 문제는 레벨에 따른 긴 간격 뒤로 예약
                        target = st.session_state.solve_count + FIBO_GAP[new_lv]
                        if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                        st.session_state.schedules[target].append(q_idx)
                    
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("틀림 (Alt)"):
                    # [핵심] 틀리면 즉시 Lv.1로 강등 및 가장 짧은 간격(5장 뒤) 예약
                    st.session_state.q_levels[q_idx] = 1
                    target = st.session_state.solve_count + FIBO_GAP[1] # 무조건 5장 뒤
                    if target not in st.session_state.schedules: st.session_state.schedules[target] = []
                    st.session_state.schedules[target].append(q_idx)
                    
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        # --- 📊 상태바 위치 및 계산 ---
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
            <div style="display: flex; justify-content: space-between; padding: 0 10px;">
                <p class="bar-label">✅ 정복: {mastered_q}</p>
                <p class="bar-label">🔥 복습/틀림: {reviewing_q}</p>
                <p class="bar-label">🆕 남은새문제: {new_q}</p>
            </div>
        """, unsafe_allow_html=True)

# 7. 단축키 엔진
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
