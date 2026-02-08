import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import streamlit.components.v1 as components
import re
import requests

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
if 'sheet_name' not in st.session_state: st.session_state.sheet_name = None

# 3. 디자인 설정 (PC 2/3, 모바일 1/2 사이즈 최적화 유지)
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    .feedback-text { font-size: 1.1rem !important; color: #00d4ff; font-weight: bold; text-align: center; margin-bottom: 5px; height: 30px; }
    .status-badge { font-size: 0.85rem; font-weight: bold; padding: 4px 12px; border-radius: 15px; margin-bottom: 10px; display: inline-block; }
    .badge-new { background-color: #f1c40f; color: black; }
    .badge-review { background-color: #3498db; color: white; }
    
    .dual-gauge-container { display: flex; flex-direction: column; align-items: center; margin-bottom: 25px; width: 100%; }
    .gauge-row { font-size: 1.8rem; font-family: 'Courier New', monospace; display: flex; align-items: center; justify-content: center; white-space: nowrap; overflow: hidden; width: 100%; }
    .wrong-side { color: #e74c3c; text-align: right; width: 450px; letter-spacing: 1px; }
    .correct-side { color: #9b59b6; text-align: left; width: 450px; letter-spacing: 1px; }
    .center-line { color: #555; font-weight: bold; font-size: 2.2rem; margin: 0 15px; }
    
    .question-text { font-size: 2.8rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 15px 0; line-height: 1.2; }
    .answer-text { font-size: 3.0rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 15px 0; line-height: 1.2; }
    
    /* PC 버튼: 75px (2/3 사이즈) */
    div.stButton > button { 
        width: 100% !important; height: 75px !important; 
        font-size: 1.1rem !important; font-weight: bold !important; 
        border-radius: 20px !important; color: white !important; 
        background-color: #34495e !important; border: 2px solid #555 !important; 
    }
    
    .progress-container { width: 100%; background-color: #222; border-radius: 10px; margin-top: 80px; display: flex; height: 16px; overflow: hidden; border: 1px solid #444; }

    @media (max-width: 600px) {
        .question-text { font-size: 1.6rem !important; margin: 10px 0 !important; }
        .answer-text { font-size: 1.8rem !important; margin: 10px 0 !important; }
        .wrong-side, .correct-side { width: 42vw !important; font-size: 1.1rem !important; }
        .center-line { font-size: 1.4rem !important; margin: 0 5px !important; }
        /* 모바일 버튼: 50px (1/2 사이즈) */
        div.stButton > button { height: 50px !important; font-size: 0.95rem !important; border-radius: 12px !important; }
        .progress-container { margin-top: 30px !important; }
    }
    .bar-mastered { background-color: #2ecc71; } .bar-review { background-color: #e74c3c; } .bar-new { background-color: #3498db; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드 로직 (보강됨)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def get_all_sheet_names():
    try:
        url = st.secrets["gsheets_url"].strip()
        sheet_id = re.search(r"/d/([a-zA-Z0-9-_]+)", url).group(1)
        # requests를 사용하여 더 안정적으로 엑셀 구조를 읽어옴
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        resp = requests.get(export_url)
        xls = pd.ExcelFile(resp.content)
        return xls.sheet_names
    except:
        return [] # 실패 시 빈 리스트 반환

@st.cache_data(ttl=1)
def load_data(sheet_name):
    try:
        url = st.secrets["gsheets_url"].strip()
        df_raw = conn.read(spreadsheet=url, worksheet=sheet_name)
        df = df_raw.iloc[:, :7]
        df.columns = ['질문', '정답', '정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']
        df = df.dropna(subset=['질문']).reset_index(drop=True)
        for col in ['정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']:
            df[col] = pd.to_numeric(df[col]).fillna(0).astype(int)
        return df
    except: return None

# [사이드바] 지능형 시트 선택 도구
sheet_list = get_all_sheet_names()

with st.sidebar:
    st.markdown("### 📂 학습 시트 선택")
    
    # 1단계: 자동 목록 시도
    if sheet_list:
        if st.session_state.sheet_name not in sheet_list:
            st.session_state.sheet_name = sheet_list[0]
        
        selected = st.selectbox("공부할 시트를 선택하세요:", sheet_list, 
                                index=sheet_list.index(st.session_state.sheet_name))
        
        if st.button("목록 새로고침 (Refresh)"):
            st.cache_data.clear(); st.rerun()
    
    # 2단계: 자동 목록 실패 시 수동 입력창 노출 (비상용)
    else:
        st.error("시트 목록을 가져오지 못했습니다.")
        st.info("공유 설정이 '뷰어'인지 확인하시거나, 아래에 시트 이름을 직접 입력해 주세요.")
        selected = st.text_input("시트 이름 직접 입력:", value="시트18")

    # 시트 변경 감지 및 상태 초기화
    if selected != st.session_state.sheet_name:
        st.session_state.sheet_name = selected
        st.cache_data.clear()
        st.session_state.df = load_data(selected)
        st.session_state.current_index = None; st.session_state.state = "IDLE"; st.session_state.solve_count = 0
        st.session_state.q_levels = {}; st.session_state.schedules = {}
        st.session_state.last_msg = f"'{selected}' 시트로 이동했습니다."
        st.rerun()

# 데이터가 없는 경우를 대비한 초기 로드
if 'df' not in st.session_state:
    st.session_state.df = load_data(st.session_state.sheet_name)
df = st.session_state.df

# 5. 출제 로직 (기존 50:50 로직 유지)
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

# --- 6. 메인 화면 ---
if df is not None:
    t_col1, t_col2, t_col3 = st.columns([5, 2.5, 2.5])
    with t_col2:
        if st.button("🔄 동기화", key="sync_btn"):
            st.cache_data.clear(); st.session_state.df = load_data(st.session_state.sheet_name); st.rerun()
    with t_col3:
        # 오답노트 다운로드 기능
        diff_df = df[df['어려움횟수'] > 0].sort_values(by='어려움횟수', ascending=False)
        if not diff_df.empty:
            csv = diff_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 오답노트 받기", data=csv, file_name=f'{st.session_state.sheet_name}_오답.csv', mime='text/csv')
        else: st.button("📥 오답 없음", disabled=True)

    if isinstance(st.session_state.current_index, int) and st.session_state.current_index >= len(df):
        st.session_state.current_index = get_next_question(df)

    _, col, _ = st.columns([1, 10, 1])
    with col:
        st.markdown(f'<p class="feedback-text">{st.session_state.last_msg}</p>', unsafe_allow_html=True)
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 해당 시트 정복 완료! 🎊</p>', unsafe_allow_html=True)
            if st.button("처음부터 다시 시작하기"):
                st.session_state.q_levels = {}; st.session_state.q_wrong_levels = {}; st.session_state.schedules = {}; st.session_state.solve_count = 0; st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()
        elif st.session_state.state == "IDLE":
            st.markdown(f'<p class="question-text">[{st.session_state.sheet_name}] 훈련 시작</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기 (Space)"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            c_lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            w_lv = st.session_state.q_wrong_levels.get(st.session_state.current_index, 0)
            label = f'<div style="text-align:center;"><span class="status-badge badge-new">🆕 신규</span></div>' if c_lv == 0 else f'<div style="text-align:center;"><span class="status-badge badge-review">🔥 Lv.{c_lv}</span></div>'
            st.markdown(label, unsafe_allow_html=True)
            w_bars = "█" * min(w_lv, 15); w_empty = "░" * (15 - len(w_bars))
            c_bars = "█" * min(c_lv, 15); c_empty = "░" * (15 - len(c_bars))
            st.markdown(f'<div class="dual-gauge-container"><div class="gauge-row"><span class="wrong-side">{w_empty}{w_bars}</span><span class="center-line">|</span><span class="correct-side">{c_bars}{c_empty}</span></div></div>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기 (Space)"): st.session_state.state = "ANSWER"; st.rerun()
        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]; q_idx = st.session_state.current_index
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("어려움 (1/Ctrl)"):
                    st.session_state.q_wrong_levels[q_idx] = st.session_state.q_wrong_levels.get(q_idx, 0) + 1
                    st.session_state.q_levels[q_idx] = 1; df.at[q_idx, '오답횟수'] += 1; df.at[q_idx, '어려움횟수'] += 1
                    try: conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except: pass
                    st.session_state.schedules.setdefault(st.session_state.solve_count + 5, []).append(q_idx)
                    st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("정상 (2/Alt)"):
                    new_lv = st.session_state.q_levels.get(q_idx, 0) + 1; df.at[q_idx, '정상횟수'] += 1
                    if new_lv > 7: df.at[q_idx, '정답횟수'] = 5; del st.session_state.q_levels[q_idx]
                    else: st.session_state.q_levels[q_idx] = new_lv; st.session_state.schedules.setdefault(st.session_state.solve_count + FIBO_GAP[new_lv], []).append(q_idx)
                    try: conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    except: pass
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
        st.markdown(f'<div style="display:flex; justify-content:space-between; padding:5px; font-size:0.8rem;"><p>✅{m_q}</p><p>🔥{r_q}</p><p>🆕{n_q}</p></div>', unsafe_allow_html=True)

# 7. 단축키 엔진
components.html("""<script>const doc = window.parent.document;doc.addEventListener('keydown', function(e) {if (e.code === 'Space') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('확인') || el.innerText.includes('시작')); if (btn) btn.click(); }else if (e.key === 'Control' || e.key === '1') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('어려움')); if (btn) btn.click(); }else if (e.key === 'Alt' || e.key === '2') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('정상')); if (btn) btn.click(); }else if (e.key === '3') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('쉬움')); if (btn) btn.click(); }});</script>""", height=0)
