import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

st.set_page_config(page_title="인출 훈련기", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    .block-container { padding-top: 1rem !important; }
    section[data-testid="stSidebar"] { background-color: #111111; width: 320px !important; }
    .info-text { font-size: 2rem !important; color: #aaaaaa; text-align: center; margin-bottom: 20px; font-weight: bold; }
    .question-text { font-size: 5rem !important; font-weight: bold; color: #f1c40f; text-align: center; margin: 80px 0; line-height: 1.4; word-break: keep-all; }
    .answer-text { font-size: 5rem !important; font-weight: bold; color: #2ecc71; text-align: center; margin: 80px 0; line-height: 1.4; word-break: keep-all; }
    div.stButton > button { width: 100%; height: 160px !important; font-size: 3.5rem !important; font-weight: bold !important; border-radius: 40px !important; background-color: #34495e; color: white; border: 3px solid #555; }
    div.stButton > button[kind="primary"] { background-color: #27ae60; border: none; }
    footer {display: none;}
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

if 'state' not in st.session_state:
    st.session_state.state = "IDLE"
    st.session_state.current_index = None
    st.session_state.target_round = 10

@st.cache_data(ttl=5)
def load_all_data(selected_list):
    all_data = []
    for sub in selected_list:
        try:
            # 탭 이름을 1, 2, 3, 4, 5로 인식하여 읽어옴
            tmp_df = conn.read(spreadsheet=st.secrets["gsheets_url"], worksheet=str(sub), usecols=[0,1,2,3])
            if not tmp_df.empty:
                tmp_df.columns = ['질문', '정답', '정답횟수', '오답횟수']
                tmp_df['과목명'] = str(sub)
                all_data.append(tmp_df)
        except:
            continue
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        return combined
    return pd.DataFrame()

# --- 사이드바: 탭 번호로 선택 ---
st.sidebar.markdown("# 📚 과목 선택")
subjects = ["1", "2", "3", "4", "5"]
selected_subs = st.sidebar.multiselect("학습할 시트 번호를 선택하세요", options=subjects, default=subjects)

full_df = load_all_data(selected_subs)

def get_next_question():
    if full_df.empty: return None
    total_counts = full_df['정답횟수'] + full_df['오답횟수']
    pending_indices = full_df[total_counts < st.session_state.target_round].index.tolist()
    if not pending_indices:
        st.session_state.target_round += 10
        pending_indices = full_df.index.tolist()
    
    subset = full_df.loc[pending_indices]
    weights = [(fail * 3) + 1 for fail in subset['오답횟수']]
    return random.choices(pending_indices, weights=weights, k=1)[0]

if full_df.empty:
    st.warning("⚠️ 시트 1, 2, 3, 4, 5에서 데이터를 찾을 수 없습니다. 주소 오타를 다시 확인해주세요.")
else:
    if st.session_state.state == "IDLE":
        st.markdown('<p class="question-text">인출 준비 완료!</p>', unsafe_allow_html=True)
        if st.button("훈련 시작 하기"):
            st.session_state.current_index = get_next_question()
            st.session_state.state = "QUESTION"
            st.rerun()

    elif st.session_state.state == "QUESTION":
        item = full_df.iloc[st.session_state.current_index]
        st.markdown(f'<p class="info-text">[{item["과목명"]}번 시트] 학습 중</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="question-text">Q. {item["질문"]}</p>', unsafe_allow_html=True)
        if st.button("정답 확인하기"):
            st.session_state.state = "ANSWER"
            st.rerun()

    elif st.session_state.state == "ANSWER":
        item = full_df.iloc[st.session_state.current_index]
        st.markdown(f'<p class="answer-text">A. {item["정답"]}</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("맞음 (O)"):
                sub_df = conn.read(spreadsheet=st.secrets["gsheets_url"], worksheet=item["과목명"])
                row_idx = sub_df[sub_df.iloc[:, 0] == item["질문"]].index[0]
                sub_df.iloc[row_idx, 2] = int(sub_df.iloc[row_idx, 2]) + 1
                conn.update(spreadsheet=st.secrets["gsheets_url"], worksheet=item["과목명"], data=sub_df)
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.cache_data.clear()
                st.rerun()
        with col2:
            if st.button("틀림 (X)"):
                sub_df = conn.read(spreadsheet=st.secrets["gsheets_url"], worksheet=item["과목명"])
                row_idx = sub_df[sub_df.iloc[:, 0] == item["질문"]].index[0]
                sub_df.iloc[row_idx, 3] = int(sub_df.iloc[row_idx, 3]) + 1
                conn.update(spreadsheet=st.secrets["gsheets_url"], worksheet=item["과목명"], data=sub_df)
                st.session_state.current_index = get_next_question()
                st.session_state.state = "QUESTION"
                st.cache_data.clear()
                st.rerun()
