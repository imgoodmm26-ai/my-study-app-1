import streamlit as st
import pandas as pd
import random
import streamlit.components.v1 as components
import re
import requests
from urllib.parse import quote

# 1. 페이지 설정
st.set_page_config(page_title="감평 최종 인출기", layout="wide")

# 2. 세션 설정
FIBO_GAP = [0, 5, 13, 21, 34, 55, 89, 144] 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'q_levels' not in st.session_state: st.session_state.q_levels = {} 
if 'q_wrong_levels' not in st.session_state: st.session_state.q_wrong_levels = {}
if 'schedules' not in st.session_state: st.session_state.schedules = {} 
if 'solve_count' not in st.session_state: st.session_state.solve_count = 0
if 'last_msg' not in st.session_state: st.session_state.last_msg = "데이터 로드 준비 중..."
if 'sheet_name' not in st.session_state: st.session_state.sheet_name = None

# 3. 디자인 설정 (기존 유지)
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    .feedback-text { font-size: 1.1rem !important; color: #00d4ff; font-weight: bold; text-align: center; margin-bottom: 5px; height: 30px; }
    .status-badge { font-size: 0.85rem; font-weight: bold; padding: 4px 12px; border-radius: 15px; margin-bottom: 5px; display: inline-block; }
    .badge-new { background-color: #f1c40f; color: black; }
    .badge-review { background-color: #3498db; color: white; }
    .dual-gauge-container { display: flex; flex-direction: column; align-items: center; margin-bottom: 25px; width: 100%; }
    .gauge-row { font-size: 1.8rem; font-family: 'Courier New', monospace; display: flex; align-items: center; justify-content: center; white-space: nowrap; overflow: hidden; width: 100%; }
    .wrong-side { color: #e74c3c; text-align: right; width: 450px; letter-spacing: 1px; }
    .correct-side { color: #9b59b6; text-align: left; width: 450px; letter-spacing: 1px; }
    .center-line { color: #555; font-weight: bold; font-size: 2.2rem; margin: 0 15px; }
    .question-text { font-size: 2.8rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 15px 0; line-height: 1.2; }
    .answer-text { font-size: 3.0rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 15px 0; line-height: 1.2; }
    div.stButton > button { width: 100% !important; height: 75px !important; font-size: 1.1rem !important; font-weight: bold !important; border-radius: 20px !important; color: white !important; background-color: #34495e !important; border: 2px solid #555 !important; }
    .progress-container { width: 100%; background-color: #222; border-radius: 10px; margin-top: 80px; display: flex; height: 16px; overflow: hidden; border: 1px solid #444; }
    @media (max-width: 600px) {
        .question-text { font-size: 1.6rem !important; margin: 10px 0 !important; }
        .answer-text { font-size: 1.8rem !important; margin: 10px 0 !important; }
        .wrong-side, .correct-side { width: 42vw !important; font-size: 1.1rem !important; }
        div.stButton > button { height: 50px !important; font-size: 0.95rem !important; border-radius: 12px !important; }
        .progress-container { margin-top: 30px !important; }
    }
    .bar-mastered { background-color: #2ecc71; } .bar-review { background-color: #e74c3c; } .bar-new { background-color: #3498db; }
</style>
""", unsafe_allow_html=True)

# 4. [핵심 변경] 데이터 로드 로직 (GViz API 사용) - 훨씬 안정적임
@st.cache_data(ttl=60)
def get_sheet_id():
    try:
        url = st.secrets["gsheets_url"].strip()
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        return match.group(1) if match else None
    except: return None

@st.cache_data(ttl=300)
def get_all_sheet_names():
    # openpyxl이 설치되어 있어야 작동함
    sheet_id = get_sheet_id()
    if not sheet_id: return []
    try:
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        resp = requests.get(export_url, timeout=10)
        resp.raise_for_status()
        xls = pd.ExcelFile(resp.content)
        return xls.sheet_names
    except: return []

@st.cache_data(ttl=1)
def load_data(sheet_name):
    sheet_id = get_sheet_id()
    if not sheet_id: return None
    try:
        # 한글 시트 이름을 URL 인코딩하여 직접 CSV로 요청 (가장 확실한 방법)
        encoded_name = quote(sheet_name)
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_name}"
        
        df = pd.read_csv(csv_url)
        # 컬럼 매핑 (혹시 모를 공백 제거)
        df.columns = [c.strip() for c in df.columns]
        # 필수 컬럼만 선택 (인덱스로 접근하여 이름 불일치 방지)
        df = df.iloc[:, :7]
        df.columns = ['질문', '정답', '정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']
        
        df = df.dropna(subset=['질문']).reset_index(drop=True)
        for col in ['정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']:
            df[col] = pd.to_numeric(df[col]).fillna(0).astype(int)
        return df
    except Exception as e:
        return None

# [상단 접이식 메뉴] 시트 선택
sheet_list = get_all_sheet_names()

with st.expander("⚙️ 학습 시트 변경 (클릭)", expanded=False):
    if sheet_list:
        if st.session_state.sheet_name not in sheet_list:
            st.session_state.sheet_name = sheet_list[0]
        selected = st.radio("시트 목록:", sheet_list, index=sheet_list.index(st.session_state.sheet_name), horizontal=True)
    else:
        st.warning("자동 목록 로드 실패 (requirements.txt에 openpyxl 확인)")
        selected = st.text_input("시트 이름 직접 입력:", value=st.session_state.sheet_name or "시트18")
    
    if st.button("🚀 선택한 시트로 학습 시작"):
        st.cache_data.clear()
        st.session_state.sheet_name = selected
        st.session_state.df = load_data(selected)
        st.session_state.current_index = None; st.session_state.state = "IDLE"; st.session_state.solve_count = 0
        st.session_state.q_levels = {}; st.session_state.schedules = {}
        st.session_state.last_msg = f"'{selected}' 로드 완료!"
        st.rerun()

# 초기 로드
if 'df' not in st.session_state or st.session_state.df is None:
    # 기본값 설정
    initial_sheet = st.session_state.sheet_name if st.session_state.sheet_name else (sheet_list[0] if sheet_list else "시트18")
    st.session_state.sheet_name = initial_sheet
    st.session_state.df = load_data(initial_sheet)

df = st.session_state.df

# 5. 출제 로직 (유지)
def get_next_question(dataframe):
    if dataframe is None or len(dataframe) == 0: return None
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
if df is not None and not df.empty:
    t_col1, t_col2, t_col3 = st.columns([5, 2.5, 2.5])
    with t_col2:
        if st.button("🔄 동기화"):
            st.cache_data.clear(); st.session_state.df = load_data(st.session_state.sheet_name); st.rerun()
    with t_col3:
        diff_df = df[df['어려움횟수'] > 0].sort_values(by='어려움횟수', ascending=False)
        if not diff_df.empty:
            csv = diff_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 오답노트", data=csv, file_name=f'{st.session_state.sheet_name}_오답.csv', mime='text/csv')

    if isinstance(st.session_state.current_index, int) and st.session_state.current_index >= len(df):
        st.session_state.current_index = get_next_question(df)

    _, col, _ = st.columns([1, 10, 1])
    with col:
        st.markdown(f'<p class="feedback-text">{st.session_state.last_msg}</p>', unsafe_allow_html=True)
        if st.session_state.current_index == "GRADUATED":
            st.markdown(f'<p class="question-text">🎊 {st.session_state.sheet_name} 완료! 🎊</p>', unsafe_allow_html=True)
            if st.button("다시 시작"):
                st.session_state.q_levels = {}; st.session_state.solve_count = 0; st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()
        elif st.session_state.state == "IDLE":
            st.markdown(f'<p class="question-text">[{st.session_state.sheet_name}] 준비 완료</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 (Space)"):
                st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            c_lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            st.markdown(f'<div style="text-align:center;"><span class="status-badge badge-new">🆕 신규</span></div>' if c_lv == 0 else f'<div style="text-align:center;"><span class="status-badge badge-review">🔥 복습 Lv.{c_lv}</span></div>', unsafe_allow_html=True)
            w_bars = "█" * min(st.session_state.q_wrong_levels.get(st.session_state.current_index, 0), 15); w_empty = "░" * (15 - len(w_bars))
            c_bars = "█" * min(c_lv, 15); c_empty = "░" * (15 - len(c_bars))
            st.markdown(f'<div class="dual-gauge-container"><div class="gauge-row"><span class="wrong-side">{w_empty}{w_bars}</span><span class="center-line">|</span><span class="correct-side">{c_bars}{c_empty}</span></div></div>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인 (Space)"): st.session_state.state = "ANSWER"; st.rerun()
        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]; q_idx = st.session_state.current_index
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("어려움 (1)"):
                    st.session_state.q_wrong_levels[q_idx] = st.session_state.q_wrong_levels.get(q_idx, 0) + 1; st.session_state.q_levels[q_idx] = 1; df.at[q_idx, '오답횟수'] += 1
                    # gviz 방식은 쓰기 불가능하므로, 오답 기록은 세션에만 유지되거나 별도 처리가 필요함. 
                    # *중요*: 현재 방식(공개 시트)에서는 시트에 '쓰기'가 안 됩니다. 
                    # 공부하는 동안 세션(RAM)에는 기록되지만 새로고침하면 날아갑니다.
                    # 만약 시트에 '저장'까지 하고 싶다면 반드시 서비스 계정 인증(secrets.toml 파일 교체)을 해야 합니다.
                    # 일단 공부 흐름을 위해 세션 진행은 되도록 뒀습니다.
                    st.session_state.schedules.setdefault(st.session_state.solve_count + 5, []).append(q_idx); st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("정상 (2)"):
                    new_lv = st.session_state.q_levels.get(q_idx, 0) + 1; df.at[q_idx, '정상횟수'] += 1
                    if new_lv > 7: df.at[q_idx, '정답횟수'] = 5; del st.session_state.q_levels[q_idx]
                    else: st.session_state.q_levels[q_idx] = new_lv; st.session_state.schedules.setdefault(st.session_state.solve_count + FIBO_GAP[new_lv], []).append(q_idx)
                    st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()
            with c3:
                if st.button("너무 쉬움 (3)"):
                    df.at[q_idx, '정답횟수'] = 5; df.at[q_idx, '쉬움횟수'] += 1
                    st.session_state.solve_count += 1; st.session_state.current_index = get_next_question(df); st.session_state.state = "QUESTION"; st.rerun()

        tot = len(df); m_q = len(df[df['정답횟수'] >= 5]); r_q = len(st.session_state.q_levels); n_q = tot - m_q - r_q
        st.markdown(f'<div class="progress-container"><div class="bar-mastered" style="width:{(m_q/tot)*100}%"></div><div class="bar-review" style="width:{(r_q/tot)*100}%"></div><div class="bar-new" style="width:{(n_q/tot)*100}%"></div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; justify-content:space-between; padding:5px; font-size:0.8rem;"><p>✅{m_q}</p><p>🔥{r_q}</p><p>🆕{n_q}</p></div>', unsafe_allow_html=True)
else:
    st.error(f"⚠️ '{st.session_state.sheet_name}' 시트를 불러오지 못했습니다.")
    st.info("1. requirements.txt에 openpyxl이 있는지 확인하세요.\n2. 구글 시트 공유가 '뷰어'로 되어 있는지 확인하세요.\n3. 시트 이름에 오타가 없는지 확인하세요.")

components.html("""<script>const doc = window.parent.document;doc.addEventListener('keydown', function(e) {if (e.code === 'Space') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('확인') || el.innerText.includes('시작')); if (btn) btn.click(); }else if (e.key === '1') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('어려움')); if (btn) btn.click(); }else if (e.key === '2') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('정상')); if (btn) btn.click(); }else if (e.key === '3') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('쉬움')); if (btn) btn.click(); }});</script>""", height=0)
