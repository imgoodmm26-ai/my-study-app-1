import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="감평 하이브리드 AI 인출기", layout="wide")

# 2. AI 설정 (보내주신 API 키를 직접 적용했습니다)
# 보안을 위해 실제 배포시에는 Secrets에 넣는 것을 권장하지만, 우선 바로 작동하도록 세팅합니다.
API_KEY = "AIzaSyB0ukeS7Wzt0K5YoPmgl6OQg1HnoaXAJ1w"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. 기기 감지 (노트북 vs 모바일)
is_mobile = False
try:
    ua = st.context.headers.get("User-Agent", "").lower()
    if any(x in ua for x in ["iphone", "ipad", "android", "mobile"]):
        is_mobile = True
except:
    pass
is_pc = not is_mobile

# 4. 세션 상태 초기화
if 'session_scores' not in st.session_state: st.session_state.session_scores = {} 
if 'state' not in st.session_state: st.session_state.state = "IDLE"
if 'current_index' not in st.session_state: st.session_state.current_index = None
if 'ai_explanation' not in st.session_state: st.session_state.ai_explanation = ""

# 5. 디자인 설정
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .device-tag { color: #2ecc71; font-size: 1.1rem; font-weight: bold; text-align: right; }
    .info-text { font-size: 1.6rem !important; color: #aaaaaa; font-weight: bold; text-align: center; }
    .question-text { font-size: 4.0rem !important; font-weight: bold; color: #f1c40f; line-height: 1.3; text-align: center; margin: 30px 0; word-break: keep-all; }
    .answer-text { font-size: 4.0rem !important; font-weight: bold; color: #2ecc71; line-height: 1.3; text-align: center; margin: 30px 0; word-break: keep-all; }
    
    /* AI 멘토 박스 디자인 */
    .ai-box { background-color: #1e1e2e; border-left: 8px solid #8e44ad; padding: 25px; border-radius: 20px; margin: 25px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
    .ai-title { color: #bb86fc; font-weight: bold; font-size: 1.8rem; margin-bottom: 12px; display: flex; align-items: center; }
    .ai-content { font-size: 1.6rem; line-height: 1.6; color: #e0e0e0; font-weight: 500; }

    div.stButton > button { width: 100%; height: 130px !important; font-size: 2.5rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
    footer {display: none;}
    </style>
    """, unsafe_allow_html=True)

# 6. 데이터 로드 (질문, 정답, 맞음, 틀림)
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

# 5회 성공 시 제외 로직
def get_next_question_index(dataframe):
    if dataframe is None: return None
    available = [idx for idx in range(len(dataframe)) if (int(dataframe.iloc[idx]['맞음']) + st.session_state.session_scores.get(str(dataframe.iloc[idx]['질문']), [0, 0])[0]) < 5]
    return random.choice(available) if available else "GRADUATED"

# AI에게 비유 요청하는 함수
def ask_ai_mentor(question, answer):
    prompt = f"질문: {question}, 정답: {answer}. 감정평가사 시험을 준비하는 비전공자 직장인 수험생에게 이 개념을 아주 쉽고 친근한 일상생활의 비유를 들어서 딱 1~2문장으로만 설명해줘."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"멘토가 잠시 자리를 비웠어요. ({e}) 하지만 포기하지 마세요!"

# --- 7. 화면 구성 ---
if df is not None:
    st.markdown(f'<p class="device-tag">{"💻 PC" if is_pc else "📱 모바일"} 모드</p>', unsafe_allow_html=True)
    for _ in range(4): st.write("")
    _, col2, _ = st.columns([1, 10, 1])

    with col2:
        if st.session_state.current_index == "GRADUATED":
            st.markdown('<p class="question-text">🎊 축하합니다! 모든 문제를 정복하셨습니다! 🎊</p>', unsafe_allow_html=True)
            if st.button("처음부터 다시 시작하기", type="primary"):
                st.session_state.session_scores = {}; st.session_state.state = "IDLE"; st.session_state.current_index = None; st.rerun()

        elif st.session_state.state == "IDLE":
            st.markdown('<p class="question-text">AI 멘토 인출 훈련 준비 완료</p>', unsafe_allow_html=True)
            if st.button("훈련 시작 하기", type="primary"):
                st.session_state.current_index = get_next_question_index(df)
                st.session_state.state = "QUESTION"; st.rerun()

        elif st.session_state.state == "QUESTION":
            row = df.iloc[st.session_state.current_index]
            total_correct = int(row['맞음']) + st.session_state.session_scores.get(str(row['질문']), [0, 0])[0]
            st.markdown(f'<p class="info-text">누적 정답: {total_correct}/5 (5회 달성 시 졸업)</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="question-text">Q. {row["질문"]}</p>', unsafe_allow_html=True)
            if st.button("정답 확인하기"):
                st.session_state.state = "ANSWER"; st.rerun()

        elif st.session_state.state == "ANSWER":
            row = df.iloc[st.session_state.current_index]
            st.markdown(f'<p class="answer-text">A. {row["정답"]}</p>', unsafe_allow_html=True)
            
            # AI 설명 박스 (틀렸을 때 생성된 설명이 있으면 표시)
            if st.session_state.ai_explanation:
                st.markdown(f"""
                <div class="ai-box">
                    <div class="ai-title">🧠 AI 멘토의 비유</div>
                    <div class="ai-content">{st.session_state.ai_explanation}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("이해 완료! 다음 문제로 ➔"):
                    st.session_state.ai_explanation = ""
                    st.session_state.current_index = get_next_question_index(df)
                    st.session_state.state = "QUESTION"; st.rerun()
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
                        st.session_state.current_index = get_next_question_index(df)
                        st.session_state.state = "QUESTION"; st.rerun()
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
                        # AI 설명 생성 모드로 전환
                        with st.spinner("AI 멘토가 비전공자용 비유를 생성 중..."):
                            st.session_state.ai_explanation = ask_ai_mentor(row['질문'], row['정답'])
                        st.rerun()

    # 하단 취약 문제 현황
    for _ in range(12): st.write("") 
    st.write("---")
    st.subheader("⚠️ 이번 세션 취약 문제 Top 5")
    err_df = pd.DataFrame([{'질문': q, '틀림': s[1]} for q, s in st.session_state.session_scores.items() if s[1] > 0])
    if not err_df.empty: st.table(err_df.sort_values(by='틀림', ascending=False).head(5))
