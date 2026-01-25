import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="감평 하이브리드 AI 인출기", layout="wide")

# 2. AI 설정 (보내주신 API 키)
API_KEY = "AIzaSyB0ukeS7Wzt0K5YoPmgl6OQg1HnoaXAJ1w"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. 기기 감지
is_mobile = any(x in st.context.headers.get("User-Agent", "").lower() for x in ["iphone", "ipad", "android", "mobile"])
is_pc = not is_mobile

# 4. 세션 상태 초기화
if 'session_scores' not in st.session_state: st.session_state.session_scores = {} 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'ai_explanation' not in st.session_state: st.session_state.ai_explanation = ""

# 5. 디자인 설정 (따옴표 에러 방지를 위해 정밀하게 재구성)
st.markdown("""
<style>
    .stApp { background-color: black; color: white; }
    .device-tag { color: #2ecc71; font-size: 1.1rem; font-weight: bold; text-align: right; }
    .question-text { font-size: 4.0rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 30px 0; }
    .answer-text { font-size: 4.0rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 30px 0; }
    .ai-box { background-color: #1e1e2e; border-left: 8px solid #8e44ad; padding: 25px; border-radius: 20px; margin: 25px 0; }
    .ai-content { font-size: 1.5rem; line-height: 1.6; color: #e0e0e0; }
    div.stButton > button { width: 100%; height: 130px !important; font-size: 2.5rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; }
</style>
""", unsafe_allow_html=True)

# 6. 데이터 로드 및 로직
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=2)
def load_data():
    try:
        url = st.secrets["gsheets_url"].strip()
        df = conn.read(spreadsheet=url, worksheet=0, usecols=[0,1,2,3])
        df.columns = ['질문', '정답', '맞음', '틀림']
        df['맞음'] = pd.to_numeric(df['맞음']).fillna(0).astype(int)
        df['틀림'] = pd.to_numeric(df['틀림']).fillna(0).astype(int)
        return df
    except: return None

df = load_data()

def get_next_question_index(dataframe):
    if dataframe is None: return None
    available = [idx for idx in range(len(dataframe)) if (int(dataframe.iloc[idx]['맞음']) + st.session_state.session_scores.get(str(dataframe.iloc[idx]['질문']), [0, 0])[0]) < 5]
    return random.choice(available) if available else "GRADUATED"

def ask_ai_mentor(question, answer):
    prompt = f"질문: {question}, 정답: {answer}. 감정평가사 비전공자 학생에게 일상 비유로 1문장 설명해줘."
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "잠시 후 다시 시도해주세요."

# 7. 화면 구성
if df is not None:
    st.markdown(f'<p class="device-tag">{"💻 PC" if is_pc else "📱 모바일"} 모드</p>', unsafe_allow_html=True)
    
    # 중앙 정렬을 위한 컬럼 구성
    _, col, _ = st.columns([1, 10, 1])
    
    with col:
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 훈련 종료! 모든 문제를 정복했습니다! 🎊</p>', unsafe_allow_html=True)
            if st.button("처음부터 다시 하기"):
                st.session_state.session_scores = {}; st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">AI 멘토 인출 훈련</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", type="primary"):
                st.session_state.current_index = get_next_question_index(df)
                st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            
            if st.session_state.ai_explanation:
                st.markdown(f'<div class="ai-box"><div class="ai-content">🧠 {st.session_state.ai_explanation}</div></div>', unsafe_allow_html=True)
                if st.button("이해 완료! 다음 문제 ➔"):
                    st.session_state.ai_explanation = ""; st.session_state.current_index = get_next_question_index(df); st.session_state.state = "QUESTION"; st.rerun()
            else:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("맞음 (O)", type="primary"):
                        q = str(row['질문'])
                        if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                        st.session_state.session_scores[q][0] += 1
                        if is_pc:
                            try:
                                df.iloc[st.session_state.current_index, 2] += 1
                                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                            except: pass
                        st.session_state.current_index = get_next_question_index(df); st.session_state.state = "QUESTION"; st.rerun()
                with c2:
                    if st.button("틀림 (X)"):
                        q = str(row['질문'])
                        if q not in st.session_state.session_scores: st.session_state.session_scores[q] = [0, 0]
                        st.session_state.session_scores[q][1] += 1
                        if is_pc:
                            try:
                                df.iloc[st.session_state.current_index, 3] += 1
                                conn.update(spreadsheet=st.secrets["gsheets_url"], data=df)
                            except: pass
                        with st.spinner("AI 비유 생성 중..."):
                            st.session_state.ai_explanation = ask_ai_mentor(row['질문'], row['정답'])
                        st.rerun()
