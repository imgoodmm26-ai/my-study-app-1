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
if 'selected_worksheet' not in st.session_state: st.session_state.selected_worksheet = None
if 'worksheet_names' not in st.session_state: st.session_state.worksheet_names = []

# 3. 디자인 설정 (PC 2/3, 모바일 1/2 사이즈 최적화)
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
    
    /* PC 버튼: 약 2/3 사이즈 축소 */
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
        /* 모바일 버튼: 약 1/2 사이즈 축소 */
        div.stButton > button { height: 50px !important; font-size: 0.95rem !important; border-radius: 12px !important; }
        .progress-container { margin-top: 30px !important; }
    }
    .bar-mastered { background-color: #2ecc71; } .bar-review { background-color: #e74c3c; } .bar-new { background-color: #3498db; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드 함수들
conn = st.connection("gsheets", type=GSheetsConnection)

# 워크시트 목록 가져오기
@st.cache_data(ttl=60)
def get_worksheet_names():
    try:
        url = st.secrets["gsheets_url"].strip()
        # GSheetsConnection의 내부 클라이언트 사용
        # connection 객체를 통해 워크시트 목록 가져오기
        import gspread
        from google.oauth2.service_account import Credentials
        
        # streamlit secrets에서 인증 정보 가져오기
        if "gcp_service_account" in st.secrets:
            # Service Account 사용
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            credentials = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], 
                scopes=scopes
            )
            client = gspread.authorize(credentials)
        else:
            # 공개 시트 접근 방법 - 하지만 gspread는 기본적으로 인증 필요
            # 대신 streamlit-gsheets의 connection을 활용
            # 모든 시트를 순회하면서 존재하는 시트 찾기
            worksheet_names = []
            for i in range(20):  # 최대 20개 시트까지 시도
                try:
                    test_df = conn.read(spreadsheet=url, worksheet=i, ttl=0, usecols=[0], nrows=1)
                    if test_df is not None:
                        # 시트 번호를 이름으로 저장 (실제 이름을 못 가져오므로)
                        worksheet_names.append(f"시트 {i}")
                except:
                    break
            return worksheet_names if worksheet_names else ["시트 0"]
        
        spreadsheet = client.open_by_url(url)
        return [ws.title for ws in spreadsheet.worksheets()]
    
    except Exception as e:
        # 오류 발생 시 기본 시트 이름들 반환
        st.warning(f"워크시트 목록을 가져올 수 없습니다. 시트 번호로 접근합니다: {str(e)}")
        # 최소 5개 시트 옵션 제공
        return [f"시트 {i}" for i in range(5)]

@st.cache_data(ttl=1)
def load_data(worksheet_identifier):
    try:
        url = st.secrets["gsheets_url"].strip()
        df_raw = conn.read(spreadsheet=url, worksheet=worksheet_identifier)
        df = df_raw.iloc[:, :7]
        df.columns = ['질문', '정답', '정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']
        df = df.dropna(subset=['질문']).reset_index(drop=True)
        for col in ['정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']:
            df[col] = pd.to_numeric(df[col]).fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None

# 초기 워크시트 목록 로드
if not st.session_state.worksheet_names:
    st.session_state.worksheet_names = get_worksheet_names()

# 초기 워크시트 설정
if st.session_state.selected_worksheet is None and st.session_state.worksheet_names:
    st.session_state.selected_worksheet = st.session_state.worksheet_names[0]

# 초기 데이터 로드
if 'df' not in st.session_state and st.session_state.selected_worksheet:
    # 시트 이름에서 번호 추출 (만약 "시트 0" 형식이면)
    if st.session_state.selected_worksheet.startswith("시트 "):
        sheet_id = int(st.session_state.selected_worksheet.split()[1])
        st.session_state.df = load_data(sheet_id)
    else:
        st.session_state.df = load_data(st.session_state.selected_worksheet)

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
    # 워크시트 선택 UI (최상단)
    st.markdown("### 📚 학습 시트 선택")
    
    col_ws1, col_ws2 = st.columns([8, 2])
    
    with col_ws1:
        selected = st.selectbox(
            "시트 선택:",
            st.session_state.worksheet_names,
            index=st.session_state.worksheet_names.index(st.session_state.selected_worksheet) if st.session_state.selected_worksheet in st.session_state.worksheet_names else 0,
            key="worksheet_selector",
            label_visibility="collapsed"
        )
    
    with col_ws2:
        if st.button("🔄 새로고침", key="refresh_worksheets"):
            st.cache_data.clear()
            st.session_state.worksheet_names = get_worksheet_names()
            st.rerun()
    
    # 워크시트가 변경되면 데이터 다시 로드 및 학습 상태 초기화
    if selected != st.session_state.selected_worksheet:
        st.session_state.selected_worksheet = selected
        st.cache_data.clear()
        
        # 시트 이름에서 번호 추출 (만약 "시트 0" 형식이면)
        if selected.startswith("시트 "):
            sheet_id = int(selected.split()[1])
            st.session_state.df = load_data(sheet_id)
        else:
            st.session_state.df = load_data(selected)
        
        df = st.session_state.df
        
        # 학습 상태 초기화
        st.session_state.q_levels = {}
        st.session_state.q_wrong_levels = {}
        st.session_state.schedules = {}
        st.session_state.solve_count = 0
        st.session_state.state = "IDLE"
        st.session_state.current_index = None
        st.session_state.last_msg = f"'{selected}' 시트로 전환되었습니다."
        st.rerun()
    
    st.markdown("---")  # 구분선
    
    # 상단 버튼 레이아웃 (동기화 + 오답노트 다운로드)
    t_col1, t_col2, t_col3 = st.columns([5, 2.5, 2.5])
    with t_col2:
        if st.button("🔄 동기화", key="sync_btn"):
            st.cache_data.clear()
            # 시트 이름에서 번호 추출
            if st.session_state.selected_worksheet.startswith("시트 "):
                sheet_id = int(st.session_state.selected_worksheet.split()[1])
                st.session_state.df = load_data(sheet_id)
            else:
                st.session_state.df = load_data(st.session_state.selected_worksheet)
            st.rerun()
    with t_col3:
        # [핵심] 오답노트 추출 로직
        diff_df = df[df['어려움횟수'] > 0].sort_values(by='어려움횟수', ascending=False)
        if not diff_df.empty:
            csv_data = diff_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 오답노트 받기", 
                data=csv_data, 
                file_name=f'{st.session_state.selected_worksheet}_오답노트.csv', 
                mime='text/csv'
            )
        else:
            st.button("📥 오답 없음", disabled=True)

    if isinstance(st.session_state.current_index, int) and st.session_state.current_index >= len(df):
        st.session_state.current_index = get_next_question(df)

    _, col, _ = st.columns([1, 10, 1])
    with col:
        st.markdown(f'<p class="feedback-text">{st.session_state.last_msg}</p>', unsafe_allow_html=True)
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 모든 문항 정복 완료! 🎊</p>', unsafe_allow_html=True)
            if st.button("처음부터 다시 시작하기"):
                st.session_state.q_levels = {}
                st.session_state.q_wrong_levels = {}
                st.session_state.schedules = {}
                st.session_state.solve_count = 0
                st.session_state.state = "IDLE"
                st.session_state.current_index = None
                st.rerun()
        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">인출 시스템</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기 (Space)"):
                st.session_state.current_index = get_next_question(df)
                st.session_state.state = "QUESTION"
                st.rerun()
        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            c_lv = st.session_state.q_levels.get(st.session_state.current_index, 0)
            w_lv = st.session_state.q_wrong_levels.get(st.session_state.current_index, 0)
            label = f'<div style="text-align:center;"><span class="status-badge badge-new">🆕 신규</span></div>' if c_lv == 0 else f'<div style="text-align:center;"><span class="status-badge badge-review">🔥 Lv.{c_lv}</span></div>'
            st.markdown(label, unsafe_allow_html=True)
            w_bars = "█" * min(w_lv, 15)
            w_empty = "░" * (15 - len(w_bars))
            c_bars = "█" * min(c_lv, 15)
            c_empty = "░" * (15 - len(c_bars))
            st.markdown(f'<div class="dual-gauge-container"><div class="gauge-row"><span class="wrong-side">{w_empty}{w_bars}</span><span class="center-line">|</span><span class="correct-side">{c_bars}{c_empty}</span></div></div>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기 (Space)"):
                st.session_state.state = "ANSWER"
                st.rerun()
        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            q_idx = st.session_state.current_index
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("어려움 (1/Ctrl)"):
                    st.session_state.q_wrong_levels[q_idx] = st.session_state.q_wrong_levels.get(q_idx, 0) + 1
                    st.session_state.q_levels[q_idx] = 1
                    df.at[q_idx, '오답횟수'] += 1
                    df.at[q_idx, '어려움횟수'] += 1
                    try:
                        # 시트 식별자 결정
                        sheet_id = st.session_state.selected_worksheet
                        if sheet_id.startswith("시트 "):
                            sheet_id = int(sheet_id.split()[1])
                        conn.update(spreadsheet=st.secrets["gsheets_url"], worksheet=sheet_id, data=df)
                    except:
                        pass
                    target = st.session_state.solve_count + 5
                    st.session_state.schedules.setdefault(target, []).append(q_idx)
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df)
                    st.session_state.state = "QUESTION"
                    st.rerun()
            with c2:
                if st.button("정상 (2/Alt)"):
                    new_lv = st.session_state.q_levels.get(q_idx, 0) + 1
                    df.at[q_idx, '정상횟수'] += 1
                    if new_lv > 7:
                        df.at[q_idx, '정답횟수'] = 5
                        del st.session_state.q_levels[q_idx]
                    else:
                        st.session_state.q_levels[q_idx] = new_lv
                        st.session_state.schedules.setdefault(st.session_state.solve_count + FIBO_GAP[new_lv], []).append(q_idx)
                    try:
                        sheet_id = st.session_state.selected_worksheet
                        if sheet_id.startswith("시트 "):
                            sheet_id = int(sheet_id.split()[1])
                        conn.update(spreadsheet=st.secrets["gsheets_url"], worksheet=sheet_id, data=df)
                    except:
                        pass
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df)
                    st.session_state.state = "QUESTION"
                    st.rerun()
            with c3:
                if st.button("너무 쉬움 (3)"):
                    df.at[q_idx, '정답횟수'] = 5
                    df.at[q_idx, '쉬움횟수'] += 1
                    try:
                        sheet_id = st.session_state.selected_worksheet
                        if sheet_id.startswith("시트 "):
                            sheet_id = int(sheet_id.split()[1])
                        conn.update(spreadsheet=st.secrets["gsheets_url"], worksheet=sheet_id, data=df)
                    except:
                        pass
                    if q_idx in st.session_state.q_levels:
                        del st.session_state.q_levels[q_idx]
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df)
                    st.session_state.state = "QUESTION"
                    st.rerun()

        tot = len(df)
        m_q = len(df[df['정답횟수'] >= 5])
        r_q = len(st.session_state.q_levels)
        n_q = tot - m_q - r_q
        st.markdown(f'<div class="progress-container"><div class="bar-mastered" style="width:{(m_q/tot)*100}%"></div><div class="bar-review" style="width:{(r_q/tot)*100}%"></div><div class="bar-new" style="width:{(n_q/tot)*100}%"></div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; justify-content:space-between; padding:5px; font-size:0.8rem;"><p>✅{m_q}</p><p>🔥{r_q}</p><p>🆕{n_q}</p></div>', unsafe_allow_html=True)

else:
    st.error("데이터를 불러올 수 없습니다. 구글 시트 연결을 확인해주세요.")

# 7. 단축키 엔진
components.html("""<script>const doc = window.parent.document;doc.addEventListener('keydown', function(e) {if (e.code === 'Space') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('확인') || el.innerText.includes('시작')); if (btn) btn.click(); }else if (e.key === 'Control' || e.key === '1') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('어려움')); if (btn) btn.click(); }else if (e.key === 'Alt' || e.key === '2') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('정상')); if (btn) btn.click(); }else if (e.key === '3') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('쉬움')); if (btn) btn.click(); }});</script>""", height=0)
