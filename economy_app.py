import streamlit as st
import pandas as pd
import random

# 1. 경제학 핵심 문제 데이터 (빈출 및 출제 예상 내용)
def load_economy_data():
    data = [
        {
            "difficulty": "중",
            "question": "IS 곡선이 우하향할 때, 확장적 재정정책은 IS 곡선을 어느 방향으로 이동시키는가?",
            "answer": "오른쪽(우측)으로 이동시킵니다. 정부지출 증가나 조세 감면은 모든 이자율 수준에서 총수요를 증가시키기 때문입니다."
        },
        {
            "difficulty": "상",
            "question": "투자가 이자율 변화에 전혀 반응하지 않는 경우(투자 탄력성=0), IS 곡선의 형태와 정책 효과는?",
            "answer": "IS 곡선은 **수직선**이 됩니다. 이 경우 재정정책의 효과는 극대화되지만, 통화정책은 효과가 없습니다."
        },
        {
            "difficulty": "중",
            "question": "LM 곡선이 우상향할 때, 중앙은행의 국공채 매입은 LM 곡선을 어느 방향으로 이동시키는가?",
            "answer": "오른쪽(하방)으로 이동시킵니다. 통화량 공급이 늘어나면 화폐시장의 균형 이자율이 하락하기 때문입니다."
        },
        {
            "difficulty": "최상",
            "question": "유동성 함정(Liquidity Trap) 구간에서 LM 곡선의 형태와 통화정책의 유효성은?",
            "answer": "LM 곡선은 **수평선**이 됩니다. 이 구간에서는 통화량을 아무리 늘려도 이자율이 더 이상 떨어지지 않아 통화정책이 무력해집니다."
        },
        {
            "difficulty": "하",
            "question": "고전학파의 '세이의 법칙(Say's Law)'을 한 문장으로 정의하면?",
            "answer": "'공급은 스스로 수요를 창출한다'는 원리로, 생산물 시장의 초과공급이 발생하지 않는다고 봅니다."
        }
    ]
    return pd.DataFrame(data)

# 2. 세션 상태 초기화 (문제 섞기 및 인덱스 관리)
if 'db' not in st.session_state:
    st.session_state.db = load_economy_data()
if 'idx' not in st.session_state:
    st.session_state.idx = random.randint(0, len(st.session_state.db) - 1)

# 3. 화면 UI 구성 (타이틀 제거 및 플래시카드 방식)
df = st.session_state.db
current_item = df.iloc[st.session_state.idx]

# --- 문제 표시 영역 ---
st.write(f"**[난이도: {current_item['difficulty']}]**") # 난이도 표시

# 질문을 클릭하면 정답이 보이는 Expander 구조
with st.expander(f"Q. {current_item['question']}", expanded=False):
    st.write("---")
    st.success(f"**A. {current_item['answer']}**")

st.write("") # 간격 조절

# 4. 다음 문제 버튼
if st.button("다음 문제 보기 ➡️"):
    st.session_state.idx = random.randint(0, len(df) - 1)
    st.rerun()

# 5. 하단 고정 정보
st.divider()
st.caption("감정평가사 1차 경제학 핵심 개념 훈련 모드")
