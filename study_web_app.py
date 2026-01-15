import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
from urllib.parse import quote # 한글 에러 방지를 위한 부품

# 1. 페이지 설정
st.set_page_config(page_title="인출 훈련기", layout="wide")

# 2. 세션 상태 초기화 (에러 방지용)
if 'session_scores' not in st.session_state:
    st.session_state.session_scores = {}
if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
if 'current_index' not in st.session_state:
    st.session_state.current_index = None

# 3. 디자인 설정 (글씨 크기 2포인트 축소 및 중앙 정렬 최적화)
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    
    /* 중앙 정렬을 위한 여백 설정 */
    .stMainContainer {
        display: flex;
        justify-content: center;
    }
    
    .info-text { font-size: 1.8rem !important; color: #aaaaaa; font-weight: bold; text-align: center; }
    .session-text { font-size: 1.5rem !important; color: #3498db; font-weight: bold; margin-bottom: 20px; text-align: center; }
    
    /* 질문/정답 텍스트 (4.3rem - 이전보다 2포인트 작게) */
    .question-text { font-size: 4.3rem !important; font-weight: bold; color: #f1c40f; line-height: 1.4; text-align: center; margin: 40px 0; word-break: keep-all; }
    .answer-text { font-size: 4.3rem !important; font-weight: bold; color: #2ecc71; line-height: 1.4; text-align: center; margin: 40px 0; word-break: keep-all; }
    
    /* 버튼 스타일 (2.8rem) */
    div.stButton > button { 
        width: 100%; 
        height: 140px !important; 
        font-size: 2.8rem !important; 
        font-weight: bold !important; 
        border-radius: 40px !important; 
        background-color: #34495e; 
        color: white; 
        border: 3px solid #555;
    }
    div.stButton > button[kind="primary"] { background-color: #27ae60; border: none; }
    
    footer {display: none;}
    </style>
    """, unsafe_allow_html=True)

# 4. 데이터 로드 (한글 에러 방지 처리)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        # 1. 시트 주소 가져오기
        url = st.secrets["gsheets_url"]
        
        # 2. 탭 이름 '회계학'을 컴퓨터용 코드로 안전하게 변환
        safe_worksheet_name = "회계학"
        
        # 3. 데이터 읽기 (에러 방지용 시트 ID 추출 로직 포함 가능하나 일단 단순하게 읽기 시도)
        df = conn.read(spreadsheet=url, worksheet=safe_worksheet_name, usecols=[0,1])
        df.columns = ['질문', '정답']
        return df
    except Exception as e:
        # 에러 발생 시 사용자에게 친절하게 표시
        st.error(f"⚠️ 데이터 로드 중 문제가 발생했습니다. (에러내용: {e})")
        return None

df = load_data()

# --- 5. 화면 구성 (에러 없는 순정 정렬 방식) ---

if df is not None:
    # 상단 여백 (중앙 배치를 위해 빈 공간 추가)
    for _ in range(4): st.write("")

    # 가로 중앙 정렬 (가운데 col2만 사용)
    _, col2, _ = st.columns([1, 10, 1])

    with col2:
        # [준비 화면]
        if st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">인출 훈련 준비 완료</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", kind="primary"):
                st.session_state.current_index = random.randint(0, len(df)-1)
                st.session_state.state = "QUESTION"
                st.rerun()

        # [질문 화면]
        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            q_text = str(row['질문'])
            score = st.session_state.session_scores.get(q_text, [0, 0])
            
            st.markdown('<p class="info-text">인출 훈련 중</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="session-text">📈 이번 세션 성적 - 맞음: {score[0]} / 틀림: {score[1]}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {q_text}</p>', unsafe_allow_html=True)
            
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"
                st.rerun()

        # [정답 화면]
        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {str(row["정답"])}</p>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("맞음 (O)", kind="primary"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][0] += 1
                    st.session_state.current_index = random.randint(0, len(df)-1)
                    st.session_state.state = "QUESTION"
                    st.rerun()
            with c2:
                if st.button("틀림 (X)"):
                    q = str(row['질문'])
                    if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                    st.session_state.session_scores[q][1] += 1
                    st.session_state.current_index = random.randint(0, len(df)-1)
                    st.session_state.state = "QUESTION"
                    st.rerun()

    # 하단 분석표는 아주 멀리 배치 (공부 방해 금지)
    for _ in range(15): st.write("") 
    st.write("---")
    st.subheader("⚠️ 이번 세션 취약 문제 (많이 틀린 순)")
    if st.session_state.session_scores:
        summary_df = pd.DataFrame([{'질문': q, '틀림': s[1]} for q, s in st.session_state.session_scores.items() if s[1] > 0])
        if not summary_df.empty:
            st.table(summary_df.sort_values(by='틀림', ascending=False).head(5))
        else:
            st.write("아직 틀린 문제가 없네요! 좋습니다.")
    else:
        st.write("데이터가 쌓이면 여기에 표시됩니다.")

else:
    st.warning("위의 에러 메시지를 확인하여 시트 설정을 점검해 주세요.")
