import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="감평 하이브리드 인출기", layout="wide")

# 2. 기기 감지 로직 (노트북 vs 모바일)
is_mobile = False
try:
    ua = st.context.headers.get("User-Agent", "").lower()
    if any(x in ua for x in ["iphone", "ipad", "android", "mobile"]):
        is_mobile = True
except:
    pass
is_pc = not is_mobile

# 3. 세션 상태 초기화
if 'session_scores' not in st.session_state:
    st.session_state.session_scores = {} # {질문: [이번세션_맞음, 이번세션_틀림]}
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
if 'current_index' not in st.session_state:
    st.session_state.current_index = None

# 4. 디자인 설정 (글씨 4.0rem / 버튼 2.5rem 최적화)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .device-tag { color: #2ecc71; font-size: 1.1rem; font-weight: bold; text-align: right; margin-bottom: 10px; }
    .info-text { font-size: 1.6rem !important; color: #aaaaaa; font-weight: bold; text-align: center; }
    .question-text { font-size: 4.0rem !important; font-weight: bold; color: #f1c40f; line-height: 1.3; text-align: center; margin: 30px 0; word-break: keep-all; }
    .answer-text { font-size: 4.0rem !important; font-weight: bold; color: #2ecc71; line-height: 1.3; text-align: center; margin: 30px 0; word-break: keep-all; }
    div.stButton > button { width: 100%; height: 130px !important; font-size: 2.5rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
    footer {display: none;}
    </style>
    """, unsafe_allow_html=True)

# 5. 데이터 로드 (4개 열 모두 로드)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=2)
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        df = conn.read(spreadsheet=url, worksheet=0, usecols=[0,1,2,3])
        df.columns = ['질문', '정답', '맞음', '틀림']
        # 숫자 데이터 에러 방지 처리
        df['맞음'] = pd.to_numeric(df['맞음']).fillna(0).astype(int)
        df['틀림'] = pd.to_numeric(df['틀림']).fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None

df = load_data()

# [핵심 로직] 시트 점수 + 세션 점수 합산하여 5회 미만인 문제 추출
def get_next_question_index(dataframe):
    if dataframe is None: return None
    available_indices = []
    for idx in range(len(dataframe)):
        q_text = str(dataframe.iloc[idx]['질문'])
        sheet_correct = dataframe.iloc[idx]['맞음']
        session_correct = st.session_state.session_scores.get(q_text, [0, 0])[0]
        
        # 누적 5번 미만이면 리스트에 추가
        if (sheet_correct + session_correct) < 5:
            available_indices.append(idx)
            
    if not available_indices: return "GRADUATED"
    return random.choice(available_indices)

# --- 6. 화면 구성 ---
if df is not None:
    # 기기 모드 표시
    mode_msg = "💻 PC 모드: 구글 시트 실시간 저장 중" if is_pc else "📱 모바일 모드: 에러 방지 세션 저장 중"
    st.markdown(f'<p class="device-tag">{mode_msg}</p>', unsafe_allow_html=True)

    for _ in range(4): st.write("")
    _, col2, _ = st.columns([1, 10, 1])

    with col2:
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 모든 문제를 정복하셨습니다! 🎊</p>', unsafe_allow_html=True)
            if st.button("처음부터 다시 시작하기", type="primary"):
                st.session_state.session_scores = {}; st.session_state.state = "IDLE"
                st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">인출 훈련 준비 완료</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", type="primary"):
                st.session_state.current_index = get_next_question_index(df)
                st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            q_text = str(row['질문'])
            sheet_correct = row['맞음']
            session_correct = st.session_state.session_scores.get(q_text, [0, 0])[0]
            total_correct = sheet_correct + session_correct
            
            st.markdown(f'<p class="info-text">누적 정답: {total_correct}/5 (5회 달성 시 졸업)</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {q_text}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("맞음 (O)", type="primary"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][0] += 1 # 세션 점수 업
                    
                    if is_pc: # 노트북이면 시트 업데이트
                        df.iloc[st.session_state.current_index, 2] += 1
                        conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                    
                    st.session_state.current_index = get_next_question_index(df)
                    st.session_state.state = "QUESTION"; st.rerun()
            with c2:
                if st.button("틀림 (X)"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][1] += 1 # 세션 점수 업
                    
                    if is_pc: # 노트북이면 시트 업데이트
                        df.iloc[st.session_state.current_index, 3] += 1
                        conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                        
                    st.session_state.current_index = get_next_question_index(df)
                    st.session_state.state = "QUESTION"; st.rerun()

    # 7. 하단 현황판
    for _ in range(15): st.write("") 
    st.write("---")
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("⚠️ 이번 세션 오답 리스트")
        err_df = pd.DataFrame([{'질문': q, '틀림': s[1]} for q, s in st.session_state.session_scores.items() if s[1] > 0])
        if not err_df.empty: st.table(err_df.sort_values(by='틀림', ascending=False).head(5))
    with col_r:
        st.subheader("🎓 정복 완료 (졸업)")
        grad_count = len([q for q, s in st.session_state.session_scores.items() if s[0] >= 5])
        st.write(f"이번 공부 시간에만 **{grad_count}**문제를 졸업시켰습니다!")

else:
    st.warning("시트에 [질문, 정답, 맞음, 틀림] 열 제목이 있는지 확인해주세요.")
