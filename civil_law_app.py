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
if 'last_msg' not in st.session_state: st.session_state.last_msg = "데이터 동기화 준비 완료."

# 3. 개선된 카드형 디자인 설정
st.markdown("""
<style>
    /* 전체 앱 배경 */
    .stApp { 
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
        color: white; 
    }
    
    /* 상단 고정 프로그레스 바 */
    .top-progress-sticky {
        position: sticky;
        top: 0;
        z-index: 1000;
        background: rgba(0, 0, 0, 0.95);
        padding: 10px 0;
        box-shadow: 0 2px 20px rgba(0, 0, 0, 0.5);
        margin-bottom: 20px;
    }
    
    .progress-bar-modern {
        display: flex;
        height: 35px;
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        border: 2px solid rgba(255, 255, 255, 0.1);
    }
    
    .progress-segment {
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        position: relative;
    }
    
    .progress-segment:hover {
        filter: brightness(1.2);
        transform: scaleY(1.05);
    }
    
    .bar-mastered { background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%); }
    .bar-review { background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); }
    .bar-new { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); }
    
    /* 피드백 메시지 */
    .feedback-text { 
        font-size: 1.2rem !important; 
        color: #00d4ff; 
        font-weight: bold; 
        text-align: center; 
        margin: 15px 0;
        text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* 상태 뱃지 개선 */
    .status-badge { 
        font-size: 0.95rem; 
        font-weight: bold; 
        padding: 8px 20px; 
        border-radius: 20px; 
        margin-bottom: 15px; 
        display: inline-block;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .badge-new { 
        background: linear-gradient(135deg, #f1c40f 0%, #f39c12 100%);
        color: black; 
    }
    .badge-review { 
        background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
        color: white; 
    }
    
    /* 카드 컨테이너 */
    .card-container {
        background: linear-gradient(135deg, rgba(52, 73, 94, 0.3) 0%, rgba(44, 62, 80, 0.3) 100%);
        border-radius: 30px;
        padding: 50px 40px;
        margin: 30px 0;
        box-shadow: 
            0 20px 60px rgba(0, 0, 0, 0.4),
            0 0 0 1px rgba(255, 255, 255, 0.1) inset;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;
    }
    
    .card-container:hover {
        box-shadow: 
            0 25px 70px rgba(0, 0, 0, 0.5),
            0 0 0 1px rgba(255, 255, 255, 0.15) inset;
        transform: translateY(-2px);
    }
    
    /* 질문 카드 (그라데이션) */
    .question-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 60px 40px;
        border-radius: 25px;
        box-shadow: 
            0 15px 50px rgba(118, 75, 162, 0.4),
            0 0 0 1px rgba(255, 255, 255, 0.1) inset;
        margin: 20px 0;
        min-height: 250px;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: cardSlideIn 0.4s ease-out;
    }
    
    /* 정답 카드 (다른 그라데이션) */
    .answer-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 60px 40px;
        border-radius: 25px;
        box-shadow: 
            0 15px 50px rgba(245, 87, 108, 0.4),
            0 0 0 1px rgba(255, 255, 255, 0.1) inset;
        margin: 20px 0;
        min-height: 250px;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: cardSlideIn 0.4s ease-out;
    }
    
    @keyframes cardSlideIn {
        from { 
            opacity: 0; 
            transform: translateY(30px) scale(0.95);
        }
        to { 
            opacity: 1; 
            transform: translateY(0) scale(1);
        }
    }
    
    /* 시작 화면 카드 */
    .welcome-card {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 80px 40px;
        border-radius: 25px;
        box-shadow: 
            0 20px 60px rgba(250, 112, 154, 0.4),
            0 0 0 1px rgba(255, 255, 255, 0.1) inset;
        margin: 20px 0;
        animation: cardSlideIn 0.4s ease-out;
    }
    
    /* 완료 화면 카드 */
    .completed-card {
        background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);
        padding: 80px 40px;
        border-radius: 25px;
        box-shadow: 
            0 20px 60px rgba(48, 207, 208, 0.4),
            0 0 0 1px rgba(255, 255, 255, 0.1) inset;
        margin: 20px 0;
        animation: cardSlideIn 0.4s ease-out;
    }
    
    .question-text { 
        font-size: 2.8rem !important; 
        font-weight: bold; 
        color: white;
        text-align: center; 
        margin: 0;
        line-height: 1.3;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }
    
    .answer-text { 
        font-size: 3.0rem !important; 
        font-weight: bold; 
        color: white;
        text-align: center; 
        margin: 0;
        line-height: 1.3;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }
    
    /* 게이지 개선 */
    .dual-gauge-container { 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        margin: 25px 0;
        width: 100%;
        background: rgba(0, 0, 0, 0.2);
        padding: 20px;
        border-radius: 15px;
    }
    
    .gauge-row { 
        font-size: 1.8rem; 
        font-family: 'Courier New', monospace; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        white-space: nowrap; 
        overflow: hidden; 
        width: 100%;
    }
    
    .wrong-side { 
        color: #e74c3c; 
        text-align: right; 
        width: 450px; 
        letter-spacing: 2px;
        text-shadow: 0 0 10px rgba(231, 76, 60, 0.5);
    }
    
    .correct-side { 
        color: #9b59b6; 
        text-align: left; 
        width: 450px; 
        letter-spacing: 2px;
        text-shadow: 0 0 10px rgba(155, 89, 182, 0.5);
    }
    
    .center-line { 
        color: #ecf0f1; 
        font-weight: bold; 
        font-size: 2.2rem; 
        margin: 0 15px;
        text-shadow: 0 0 15px rgba(236, 240, 241, 0.8);
    }
    
    /* 버튼 개선 - 호버 효과 강화 */
    div.stButton > button { 
        width: 100% !important; 
        height: 75px !important; 
        font-size: 1.15rem !important; 
        font-weight: bold !important; 
        border-radius: 20px !important; 
        color: white !important; 
        background: linear-gradient(135deg, #434343 0%, #000000 100%) !important;
        border: 2px solid rgba(255, 255, 255, 0.2) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        transition: all 0.2s ease !important;
        cursor: pointer;
    }
    
    div.stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4) !important;
        border-color: rgba(255, 255, 255, 0.4) !important;
        background: linear-gradient(135deg, #4a4a4a 0%, #1a1a1a 100%) !important;
    }
    
    div.stButton > button:active {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* 주요 액션 버튼 (정답 확인, 훈련 시작) */
    div.stButton > button[kind="primary"],
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        font-size: 1.3rem !important;
        height: 85px !important;
    }
    
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button:first-child:hover {
        background: linear-gradient(135deg, #7e8ef5 0%, #8d5bb5 100%) !important;
        box-shadow: 0 10px 30px rgba(118, 75, 162, 0.5) !important;
    }
    
    /* 하단 프로그레스 */
    .progress-container { 
        width: 100%; 
        background-color: rgba(34, 34, 34, 0.5);
        border-radius: 15px; 
        margin-top: 50px; 
        display: flex; 
        height: 20px; 
        overflow: hidden; 
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    
    /* 모바일 최적화 */
    @media (max-width: 600px) {
        .question-text { font-size: 1.8rem !important; margin: 10px 0 !important; }
        .answer-text { font-size: 2.0rem !important; margin: 10px 0 !important; }
        .wrong-side, .correct-side { width: 42vw !important; font-size: 1.2rem !important; }
        .center-line { font-size: 1.6rem !important; margin: 0 8px !important; }
        
        .card-container { padding: 30px 20px; border-radius: 20px; }
        .question-card, .answer-card, .welcome-card, .completed-card {
            padding: 40px 20px;
            min-height: 200px;
        }
        
        div.stButton > button { 
            height: 65px !important; 
            font-size: 1.05rem !important; 
            border-radius: 15px !important; 
        }
        
        div.stButton > button[kind="primary"],
        div.stButton > button:first-child {
            height: 70px !important;
            font-size: 1.15rem !important;
        }
        
        .progress-container { margin-top: 30px !important; }
        .progress-bar-modern { height: 30px; }
        .progress-segment { font-size: 0.8rem; }
    }
    
    /* 통계 숫자 스타일 */
    .stats-number {
        font-size: 1.0rem;
        font-weight: bold;
        color: rgba(255, 255, 255, 0.9);
    }
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
        df = df.dropna(subset=['질문']).reset_index(drop=True)
        for col in ['정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']:
            df[col] = pd.to_numeric(df[col]).fillna(0).astype(int)
        return df
    except: return None

if 'df' not in st.session_state: st.session_state.df = load_data()
df = st.session_state.df

# 5. 출제 로직 (50% 신규 보장 유지)
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
if df is not None:
    # 통계 계산
    tot = len(df)
    m_q = len(df[df['정답횟수'] >= 5])
    r_q = len(st.session_state.q_levels)
    n_q = tot - m_q - r_q
    
    # 상단 고정 프로그레스 바
    st.markdown('<div class="top-progress-sticky">', unsafe_allow_html=True)
    st.markdown(f'''
    <div class="progress-bar-modern">
        <div class="progress-segment bar-mastered" style="width:{(m_q/tot)*100}%">
            <span class="stats-number">✅ {m_q}</span>
        </div>
        <div class="progress-segment bar-review" style="width:{(r_q/tot)*100}%">
            <span class="stats-number">🔥 {r_q}</span>
        </div>
        <div class="progress-segment bar-new" style="width:{(n_q/tot)*100}%">
            <span class="stats-number">🆕 {n_q}</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 상단 버튼 레이아웃 (동기화 + 오답노트 다운로드)
    t_col1, t_col2, t_col3 = st.columns([5, 2.5, 2.5])
    with t_col2:
        if st.button("🔄 동기화", key="sync_btn"):
            st.cache_data.clear()
            st.session_state.df = load_data()
            st.rerun()
    with t_col3:
        # [핵심] 오답노트 추출 로직
        diff_df = df[df['어려움횟수'] > 0].sort_values(by='어려움횟수', ascending=False)
        if not diff_df.empty:
            csv_data = diff_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 오답노트", data=csv_data, file_name='my_wrong_notes.csv', mime='text/csv')
        else:
            st.button("📥 오답 없음", disabled=True)

    if isinstance(st.session_state.current_index, int) and st.session_state.current_index >= len(df):
        st.session_state.current_index = get_next_question(df)

    _, col, _ = st.columns([1, 10, 1])
    with col:
        # 피드백 메시지
        st.markdown(f'<p class="feedback-text">{st.session_state.last_msg}</p>', unsafe_allow_html=True)
        
        # 완료 화면
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<div class="completed-card">', unsafe_allow_html=True)
            st.markdown('<p class="question-text">🎊 모든 문항 정복 완료! 🎊</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("처음부터 다시 시작하기"):
                st.session_state.q_levels = {}
                st.session_state.q_wrong_levels = {}
                st.session_state.schedules = {}
                st.session_state.solve_count = 0
                st.session_state.state = "IDLE"
                st.session_state.current_index = None
                st.rerun()
        
        # 시작 화면
        elif st.session_state.state == "IDLE":
            st.markdown('<div class="welcome-card">', unsafe_allow_html=True)
            st.markdown('<p class="question-text">📚 인출 시스템</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("🚀 훈련 시작하기 (Space)"):
                st.session_state.current_index = get_next_question(df)
                st.session_state.state = "QUESTION"
                st.rerun()
        
        # 질문 화면
        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            c_lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            w_lv = st.session_state.q_wrong_levels.get(st.session_state.current_index, 0)
            
            # 상태 뱃지
            label = f'<div style="text-align:center;"><span class="status-badge badge-new">🆕 신규</span></div>' if c_lv == 0 else f'<div style="text-align:center;"><span class="status-badge badge-review">🔥 Lv.{c_lv}</span></div>'
            st.markdown(label, unsafe_allow_html=True)
            
            # 게이지
            w_bars = "█" * min(w_lv, 15)
            w_empty = "░" * (15 - len(w_bars))
            c_bars = "█" * min(c_lv, 15)
            c_empty = "░" * (15 - len(c_bars))
            st.markdown(f'<div class="dual-gauge-container"><div class="gauge-row"><span class="wrong-side">{w_empty}{w_bars}</span><span class="center-line">|</span><span class="correct-side">{c_bars}{c_empty}</span></div></div>', unsafe_allow_html=True)
            
            # 질문 카드
            st.markdown('<div class="question-card">', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("💡 정답 확인하기 (Space)"):
                st.session_state.state = "ANSWER"
                st.rerun()
        
        # 정답 화면
        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            q_idx = st.session_state.current_index
            
            # 정답 카드
            st.markdown('<div class="answer-card">', unsafe_allow_html=True)
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 평가 버튼
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("😓 어려움 (1/Ctrl)"):
                    st.session_state.q_wrong_levels[q_idx] = st.session_state.q_wrong_levels.get(q_idx, 0) + 1
                    st.session_state.q_levels[q_idx] = 1
                    df.at[q_idx, '오답횟수'] += 1
                    df.at[q_idx, '어려움횟수'] += 1
                    try:
                        conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except:
                        pass
                    target = st.session_state.solve_count + 5
                    st.session_state.schedules.setdefault(target, []).append(q_idx)
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df)
                    st.session_state.state = "QUESTION"
                    st.rerun()
            with c2:
                if st.button("✅ 정상 (2/Alt)"):
                    new_lv = st.session_state.q_levels.get(q_idx, 0) + 1
                    df.at[q_idx, '정상횟수'] += 1
                    if new_lv > 7:
                        df.at[q_idx, '정답횟수'] = 5
                        del st.session_state.q_levels[q_idx]
                    else:
                        st.session_state.q_levels[q_idx] = new_lv
                        st.session_state.schedules.setdefault(st.session_state.solve_count + FIBO_GAP[new_lv], []).append(q_idx)
                    try:
                        conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except:
                        pass
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df)
                    st.session_state.state = "QUESTION"
                    st.rerun()
            with c3:
                if st.button("😎 쉬움 (3)"):
                    df.at[q_idx, '정답횟수'] = 5
                    df.at[q_idx, '쉬움횟수'] += 1
                    try:
                        conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except:
                        pass
                    if q_idx in st.session_state.q_levels:
                        del st.session_state.q_levels[q_idx]
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df)
                    st.session_state.state = "QUESTION"
                    st.rerun()

        # 하단 프로그레스 (추가 정보)
        st.markdown(f'''
        <div class="progress-container">
            <div class="bar-mastered" style="width:{(m_q/tot)*100}%"></div>
            <div class="bar-review" style="width:{(r_q/tot)*100}%"></div>
            <div class="bar-new" style="width:{(n_q/tot)*100}%"></div>
        </div>
        ''', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; justify-content:space-between; padding:8px; font-size:0.85rem; color: rgba(255,255,255,0.7);"><p>정복: {m_q}개</p><p>복습: {r_q}개</p><p>신규: {n_q}개</p></div>', unsafe_allow_html=True)

# 7. 단축키 엔진
components.html("""<script>const doc = window.parent.document;doc.addEventListener('keydown', function(e) {if (e.code === 'Space') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('확인') || el.innerText.includes('시작')); if (btn) btn.click(); }else if (e.key === 'Control' || e.key === '1') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('어려움')); if (btn) btn.click(); }else if (e.key === 'Alt' || e.key === '2') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('정상')); if (btn) btn.click(); }else if (e.key === '3') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('쉬움')); if (btn) btn.click(); }});</script>""", height=0)
