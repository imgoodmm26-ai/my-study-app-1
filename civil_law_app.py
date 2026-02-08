import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import streamlit.components.v1 as components
import traceback
import sys

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
if 'debug_mode' not in st.session_state: st.session_state.debug_mode = False
if 'error_log' not in st.session_state: st.session_state.error_log = []

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

# 4. 유틸리티 함수
def log_error(error_msg, full_traceback=None):
    """에러 로그 기록"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_entry = {
        'timestamp': timestamp,
        'message': error_msg,
        'traceback': full_traceback
    }
    st.session_state.error_log.append(error_entry)
    # 최대 10개만 유지
    if len(st.session_state.error_log) > 10:
        st.session_state.error_log = st.session_state.error_log[-10:]

# 5. 데이터 로드 함수들
conn = st.connection("gsheets", type=GSheetsConnection)

# Secrets에서 워크시트 설정 가져오기
def get_worksheet_config():
    """워크시트 설정 가져오기 (이름과 인덱스)"""
    try:
        config = {}
        
        # 워크시트 이름 목록
        if "worksheet_names" in st.secrets:
            ws_names = st.secrets["worksheet_names"]
            if isinstance(ws_names, str):
                config['names'] = [name.strip() for name in ws_names.split(",")]
            else:
                config['names'] = list(ws_names)
        else:
            config['names'] = ["평강", "중급", "고급"]
        
        # 워크시트 인덱스 목록 (한글 인코딩 문제 해결용)
        if "worksheet_indices" in st.secrets:
            ws_indices = st.secrets["worksheet_indices"]
            if isinstance(ws_indices, str):
                config['indices'] = [int(idx.strip()) for idx in ws_indices.split(",")]
            else:
                config['indices'] = [int(idx) for idx in ws_indices]
        else:
            # 인덱스가 없으면 0부터 순서대로
            config['indices'] = list(range(len(config['names'])))
        
        # 이름-인덱스 매핑
        config['mapping'] = dict(zip(config['names'], config['indices']))
        
        return config
    
    except Exception as e:
        error_msg = f"워크시트 설정을 불러오는 중 오류: {str(e)}"
        log_error(error_msg, traceback.format_exc())
        st.error(error_msg)
        return {
            'names': ["평강", "중급", "고급"],
            'indices': [0, 1, 2],
            'mapping': {"평강": 0, "중급": 1, "고급": 2}
        }

@st.cache_data(ttl=1)
def load_data(worksheet_name, worksheet_index):
    """데이터 로드 - 인덱스 우선, 실패 시 이름 사용"""
    try:
        url = st.secrets["gsheets_url"].strip()
        
        # 먼저 인덱스로 시도 (한글 인코딩 문제 회피)
        try:
            df_raw = conn.read(spreadsheet=url, worksheet=worksheet_index)
        except Exception as e1:
            # 인덱스 실패 시 이름으로 시도
            log_error(f"인덱스 {worksheet_index}로 로드 실패, 이름으로 재시도: {str(e1)}", traceback.format_exc())
            try:
                df_raw = conn.read(spreadsheet=url, worksheet=worksheet_name)
            except Exception as e2:
                raise Exception(f"인덱스와 이름 모두 실패. 인덱스 오류: {str(e1)}, 이름 오류: {str(e2)}")
        
        # 데이터 처리
        df = df_raw.iloc[:, :7]
        df.columns = ['질문', '정답', '정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']
        df = df.dropna(subset=['질문']).reset_index(drop=True)
        
        for col in ['정답횟수', '오답횟수', '어려움횟수', '정상횟수', '쉬움횟수']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        return df
    
    except Exception as e:
        error_msg = f"데이터 로드 중 오류 발생 (시트: {worksheet_name}, 인덱스: {worksheet_index})"
        full_trace = traceback.format_exc()
        log_error(error_msg + f"\n상세: {str(e)}", full_trace)
        
        # 에러 정보를 사용자에게 표시
        st.error(f"❌ {error_msg}")
        with st.expander("🔍 상세 오류 정보 보기"):
            st.code(f"오류 메시지: {str(e)}\n\n파이썬 버전: {sys.version}\n\n전체 Traceback:\n{full_trace}")
            st.info(f"""
**문제 해결 방법:**
1. 구글 시트의 탭 이름이 '{worksheet_name}'인지 확인
2. worksheet_indices가 올바르게 설정되었는지 확인 (현재 인덱스: {worksheet_index})
3. 구글 시트 URL이 정확한지 확인
4. 구글 시트가 "링크가 있는 모든 사용자" 공개로 설정되어 있는지 확인
""")
        
        return None

# 워크시트 설정 가져오기
worksheet_config = get_worksheet_config()
worksheet_names = worksheet_config['names']
worksheet_mapping = worksheet_config['mapping']

# 초기 워크시트 설정
if st.session_state.selected_worksheet is None and worksheet_names:
    st.session_state.selected_worksheet = worksheet_names[0]

# 초기 데이터 로드
if 'df' not in st.session_state and st.session_state.selected_worksheet:
    worksheet_idx = worksheet_mapping.get(st.session_state.selected_worksheet, 0)
    st.session_state.df = load_data(st.session_state.selected_worksheet, worksheet_idx)

df = st.session_state.df

# 6. 출제 로직 (50% 신규 보장 유지)
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

# --- 7. 메인 화면 ---
# 디버그 모드 토글 (사이드바)
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    st.session_state.debug_mode = st.checkbox("🐛 디버그 모드", value=st.session_state.debug_mode)
    
    if st.session_state.debug_mode:
        st.markdown("---")
        st.markdown("### 📊 디버그 정보")
        st.json({
            "워크시트 설정": worksheet_config,
            "현재 선택된 시트": st.session_state.selected_worksheet,
            "데이터 로드 상태": "성공" if df is not None else "실패",
            "총 문제 수": len(df) if df is not None else 0,
            "Python 버전": sys.version
        })
        
        if st.session_state.error_log:
            st.markdown("---")
            st.markdown("### 🚨 오류 로그")
            for i, error in enumerate(reversed(st.session_state.error_log)):
                with st.expander(f"오류 {len(st.session_state.error_log) - i}: {error['timestamp']}"):
                    st.text(error['message'])
                    if error['traceback']:
                        st.code(error['traceback'])
        
        if st.button("🗑️ 오류 로그 초기화"):
            st.session_state.error_log = []
            st.rerun()

if df is not None:
    # 워크시트 선택 UI (최상단)
    st.markdown("### 📚 학습 시트 선택")
    
    col_ws1, col_ws2 = st.columns([8, 2])
    
    with col_ws1:
        selected = st.selectbox(
            "시트 선택:",
            worksheet_names,
            index=worksheet_names.index(st.session_state.selected_worksheet) if st.session_state.selected_worksheet in worksheet_names else 0,
            key="worksheet_selector",
            label_visibility="collapsed"
        )
    
    with col_ws2:
        if st.button("🔄 새로고침", key="refresh_worksheets"):
            st.cache_data.clear()
            st.rerun()
    
    # 디버그 모드에서 현재 시트 정보 표시
    if st.session_state.debug_mode:
        st.info(f"📍 현재 시트: {selected} (인덱스: {worksheet_mapping.get(selected, '?')})")
    
    # 워크시트가 변경되면 데이터 다시 로드 및 학습 상태 초기화
    if selected != st.session_state.selected_worksheet:
        st.session_state.selected_worksheet = selected
        st.cache_data.clear()
        
        worksheet_idx = worksheet_mapping.get(selected, 0)
        st.session_state.df = load_data(selected, worksheet_idx)
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
            worksheet_idx = worksheet_mapping.get(st.session_state.selected_worksheet, 0)
            st.session_state.df = load_data(st.session_state.selected_worksheet, worksheet_idx)
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
                        worksheet_idx = worksheet_mapping.get(st.session_state.selected_worksheet, 0)
                        conn.update(spreadsheet=st.secrets["gsheets_url"], worksheet=worksheet_idx, data=df)
                    except Exception as e:
                        log_error(f"데이터 업데이트 실패: {str(e)}", traceback.format_exc())
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
                        worksheet_idx = worksheet_mapping.get(st.session_state.selected_worksheet, 0)
                        conn.update(spreadsheet=st.secrets["gsheets_url"], worksheet=worksheet_idx, data=df)
                    except Exception as e:
                        log_error(f"데이터 업데이트 실패: {str(e)}", traceback.format_exc())
                    st.session_state.solve_count += 1
                    st.session_state.current_index = get_next_question(df)
                    st.session_state.state = "QUESTION"
                    st.rerun()
            with c3:
                if st.button("너무 쉬움 (3)"):
                    df.at[q_idx, '정답횟수'] = 5
                    df.at[q_idx, '쉬움횟수'] += 1
                    try:
                        worksheet_idx = worksheet_mapping.get(st.session_state.selected_worksheet, 0)
                        conn.update(spreadsheet=st.secrets["gsheets_url"], worksheet=worksheet_idx, data=df)
                    except Exception as e:
                        log_error(f"데이터 업데이트 실패: {str(e)}", traceback.format_exc())
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
    st.error("❌ 데이터를 불러올 수 없습니다.")
    st.markdown("""
    ### 문제 해결 체크리스트:
    
    1. ✅ **구글 시트 URL 확인**
       - Secrets에 `gsheets_url`이 올바르게 설정되어 있나요?
    
    2. ✅ **구글 시트 공개 설정**
       - 구글 시트가 "링크가 있는 모든 사용자" 공개로 설정되어 있나요?
    
    3. ✅ **워크시트 이름 확인**
       - `worksheet_names`에 설정된 이름이 실제 시트 탭 이름과 일치하나요?
    
    4. ✅ **워크시트 인덱스 확인**
       - `worksheet_indices`가 올바르게 설정되어 있나요? (0부터 시작)
    
    5. 🔍 **오류 로그 확인**
       - 왼쪽 사이드바에서 "디버그 모드"를 켜서 상세한 오류 정보를 확인하세요
    """)

# 8. 단축키 엔진
components.html("""<script>const doc = window.parent.document;doc.addEventListener('keydown', function(e) {if (e.code === 'Space') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('확인') || el.innerText.includes('시작')); if (btn) btn.click(); }else if (e.key === 'Control' || e.key === '1') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('어려움')); if (btn) btn.click(); }else if (e.key === 'Alt' || e.key === '2') { e.preventDefault(); const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('정상')); if (btn) btn.click(); }else if (e.key === '3') { const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('쉬움')); if (btn) btn.click(); }});</script>""", height=0)
