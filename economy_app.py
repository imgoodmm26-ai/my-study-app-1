import streamlit as st
import pandas as pd
import random

# 1. 초기 설정 및 데이터 (나중에 CSV 파일로 분리 가능)
def load_data():
    # 굿잡님이 공부하시는 주요 과목 데이터 예시
    data = [
        {
            "subject": "경제학",
            "difficulty": "중",
            "question": "IS 곡선이 우하향할 때, 확장적 재정정책은 IS 곡선을 어느 방향으로 이동시키는가?",
            "answer": "오른쪽(우측)으로 이동시킨다. (정부지출 증가 또는 조세 감면은 총수요를 늘리기 때문)"
        },
        {
            "subject": "경제학",
            "difficulty": "상",
            "question": "투자가 이자율 변화에 전혀 반응하지 않을 때(이자율 탄력성=0), IS 곡선의 형태는?",
            "answer": "수직선의 형태를 띤다."
        },
        {
            "subject": "경제학",
            "difficulty": "중",
            "question": "중앙은행의 공개시장 채권 매입은 LM 곡선을 어느 방향으로 이동시키는가?",
            "answer": "오른쪽(하방)으로 이동시킨다. (통화량 공급 증가에 따른 이자율 하락)"
        },
        {
            "subject": "민법",
            "difficulty": "하",
            "question": "민법상 성년후견개시의 심판을 받은 자를 무엇이라 하는가?",
            "answer": "피성년후견인"
        }
    ]
    return pd.DataFrame(data)

# 2. 세션 상태 초기화
if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'show_answer' not in st.session_state:
    st.session_state.show_answer = False

# 3. 앱 화면 구성
st.title("📚 굿잡님의 감평사 합격 훈련소")
st.sidebar.header("설정")
subject_filter = st.sidebar.multiselect("과목 선택", options=st.session_state.df['subject'].unique(), default=["경제학", "민법"])

# 필터링된 데이터
filtered_df = st.session_state.df[st.session_state.df['subject'].isin(subject_filter)]

# --- 에러 방지 로직 (문제의 ValueError 해결) ---
if filtered_df.empty:
    st.warning("선택한 과목에 문제가 없습니다. 사이드바에서 과목을 선택해주세요!")
else:
    # 문제 섞기 함수
    def next_question():
        st.session_state.current_index = random.randint(0, len(filtered_df) - 1)
        st.session_state.show_answer = False

    # 현재 문제 가져오기
    current_q = filtered_df.iloc[st.session_state.current_index]

    # --- 인터랙티브 카드 레이아웃 ---
    st.divider()
    
    # 앞면 (질문)
    st.subheader(f"[{current_q['subject']}] 문제")
    st.info(f"**난이도: {current_q['difficulty']}**")
    st.markdown(f"### Q. {current_q['question']}")

    # 뒷면 (정답) - 버튼 클릭 시 노출
    if st.button("💡 정답 보기"):
        st.session_state.show_answer = True

    if st.session_state.show_answer:
        st.success(f"**A. {current_q['answer']}**")
    
    st.divider()

    # 다음 문제 버튼
    if st.button("다음 문제 넘어가기 ➡️"):
        next_question()
        st.rerun()

# 하단 정보
st.caption("1월 말까지 민법, 감관법, 부동산학원론 이론 완주를 응원합니다!")
