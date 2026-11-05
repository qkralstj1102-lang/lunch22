
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from itertools import combinations
from collections import Counter
from urllib.request import urlopen
from io import BytesIO

# ---------------------------------------
# 1. 기본 설정
# ---------------------------------------

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.write(
    "송탄고등학교의 급식 데이터를 분석하여 "
    "어떤 메뉴들이 함께 등장하고, 어떤 메뉴들은 "
    "서로 한 번도 만나지 않았는지 알아봅니다."
)

CSV_URL = (
    "https://raw.githubusercontent.com/"
    "it-teacher-go/data-share-/main/"
    "songtan_meals_184.csv"
)


# ---------------------------------------
# 2. CSV 데이터 불러오기
# ---------------------------------------

@st.cache_data
def load_data():

    response = urlopen(CSV_URL, timeout=20)

    df = pd.read_csv(
        BytesIO(response.read()),
        encoding="utf-8"
    )

    required_columns = ["날짜", "식사", "메뉴"]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(
                f"'{col}' 열을 찾을 수 없습니다."
            )

    df = df.dropna(subset=["메뉴"]).copy()

    return df


# ---------------------------------------
# 3. 메뉴 이름 정리
# ---------------------------------------

def clean_menu(menu):

    # 괄호와 괄호 안의 내용 제거
    menu = re.sub(r"\([^)]*\)", "", str(menu))

    # 앞뒤 공백 제거
    menu = menu.strip()

    return menu


# ---------------------------------------
# 4. 장바구니 데이터 만들기
# ---------------------------------------

def make_baskets(df):

    baskets = []

    for menu_text in df["메뉴"]:

        menus = str(menu_text).split("|")

        cleaned_menus = []

        for menu in menus:

            menu = clean_menu(menu)

            if menu and menu not in cleaned_menus:
                cleaned_menus.append(menu)

        baskets.append(set(cleaned_menus))

    return baskets


# ---------------------------------------
# 5. 연관 규칙 분석
# ---------------------------------------

def analyze_rules(baskets):

    total_days = len(baskets)

    menu_count = Counter()
    pair_count = Counter()

    for basket in baskets:

        for menu in basket:
            menu_count[menu] += 1

        for pair in combinations(sorted(basket), 2):
            pair_count[pair] += 1

    rules = []

    for (menu_a, menu_b), together in pair_count.items():

        # A -> B
        support_pair = together / total_days

        confidence_ab = (
            together / menu_count[menu_a]
        )

        support_b = (
            menu_count[menu_b] / total_days
        )

        lift_ab = confidence_ab / support_b

        rules.append({
            "조건": menu_a,
            "결과": menu_b,
            "동시": together,
            "지지도": support_pair,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B -> A
        confidence_ba = (
            together / menu_count[menu_b]
        )

        support_a = (
            menu_count[menu_a] / total_days
        )

        lift_ba = confidence_ba / support_a

        rules.append({
            "조건": menu_b,
            "결과": menu_a,
            "동시": together,
            "지지도": support_pair,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    rules_df = pd.DataFrame(rules)

    return menu_count, pair_count, rules_df


# ---------------------------------------
# 6. 데이터 불러오기
# ---------------------------------------

try:

    df = load_data()

    baskets = make_baskets(df)

    menu_count, pair_count, rules_df = analyze_rules(
        baskets
    )

except Exception as e:

    st.error(
        f"데이터를 불러오는 중 오류가 발생했습니다: {e}"
    )

    st.stop()


# ---------------------------------------
# 7. 상단 통계
# ---------------------------------------

total_days = len(baskets)
total_menus = len(menu_count)
total_pairs = len(pair_count)

st.subheader("📊 전체 급식 데이터")

col1, col2, col3 = st.columns(3)

col1.metric(
    "급식 일수",
    f"{total_days:,}일"
)

col2.metric(
    "메뉴 종류 수",
    f"{total_menus:,}개"
)

col3.metric(
    "함께 나온 메뉴 쌍",
    f"{total_pairs:,}쌍"
)

st.divider()


# ---------------------------------------
# 8. 메뉴 선택 필터
# ---------------------------------------

st.subheader("🔎 메뉴별 규칙 검색")

menu_options = [
    "전체 메뉴"
] + sorted(menu_count.keys())

selected_menu = st.selectbox(
    "좁혀 보기 - 분석할 메뉴 선택",
    menu_options,
    key="rule_menu_selector"
)

if selected_menu == "전체 메뉴":

    filtered_df = rules_df.copy()

else:

    filtered_df = rules_df[
        (rules_df["조건"] == selected_menu) |
        (rules_df["결과"] == selected_menu)
    ].copy()


# ---------------------------------------
# 9. 최소 동시 일수 슬라이더
# ---------------------------------------

st.subheader("⚙️ 분석 조건 설정")

min_together = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수 이상 함께 나온 규칙만 표시합니다."
)

# 선택한 동시 일수보다 적은 규칙 제거
filtered_df = filtered_df[
    filtered_df["동시"] >= min_together
].copy()


# ---------------------------------------
# 10. 정렬 방식 선택
# ---------------------------------------

st.subheader("📋 연관 규칙 분석 결과")

sort_option = st.radio(
    "정렬 기준",
    ["향상도 순", "신뢰도 순", "동시 순"],
    horizontal=True
)

sort_columns = {
    "향상도 순": ["향상도", "신뢰도", "동시"],
    "신뢰도 순": ["신뢰도", "향상도", "동시"],
    "동시 순": ["동시", "향상도", "신뢰도"]
}

sort_by = sort_columns[sort_option]

filtered_df = filtered_df.sort_values(
    by=sort_by,
    ascending=[False, False, False]
).reset_index(drop=True)


# ---------------------------------------
# 11. 남은 규칙 개수 표시
# ---------------------------------------

st.markdown(
    f"**현재 조건에 맞는 규칙: {len(filtered_df):,}개**"
)

st.caption(
    f"최소 동시 일수: {min_together}일 이상"
)


# ---------------------------------------
# 12. 결과 표 출력
# ---------------------------------------

if filtered_df.empty:

    st.warning(
        "현재 조건에 해당하는 규칙이 없습니다. "
        "최소 동시 일수를 낮춰 보세요."
    )

else:

    display_df = filtered_df.copy()

    display_df["지지도"] = display_df["지지도"].map(
        lambda x: f"{x:.4f}"
    )

    display_df["신뢰도"] = display_df["신뢰도"].map(
        lambda x: f"{x:.4f}"
    )

    display_df["향상도"] = display_df["향상도"].map(
        lambda x: f"{x:.4f}"
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500
    )


# ---------------------------------------
# 13. 향상도 TOP 10 그래프
# ---------------------------------------

st.divider()

st.subheader("📈 향상도 TOP 10")

st.write(
    "현재 선택한 메뉴와 최소 동시 일수 조건을 "
    "적용한 향상도 상위 10개 규칙입니다."
)

if filtered_df.empty:

    st.info(
        "그래프로 나타낼 데이터가 없습니다."
    )

else:

    top10 = filtered_df.sort_values(
        by=["향상도", "신뢰도", "동시"],
        ascending=[False, False, False]
    ).head(10).copy()

    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    top10 = top10.sort_values(
        "향상도",
        ascending=True
    )

    fig = px.bar(
        top10,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        hover_data={
            "조건": True,
            "결과": True,
            "동시": True,
            "지지도": ":.4f",
            "신뢰도": ":.4f",
            "향상도": ":.4f",
            "규칙": False
        },
        labels={
            "향상도": "향상도",
            "규칙": "메뉴 규칙"
        },
        title="향상도가 높은 메뉴 조합 TOP 10"
    )

    fig.update_traces(
        texttemplate="%{text:.3f}",
        textposition="outside"
    )

    fig.update_layout(
        xaxis_title="향상도",
        yaxis_title="메뉴 규칙",
        height=500,
        margin=dict(
            l=20,
            r=70,
            t=70,
            b=40
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ---------------------------------------
# 14. 함께 나온 적 없는 짝
# ---------------------------------------

st.divider()

st.subheader("🚫 함께 나온 적 없는 짝")

st.write(
    "선택한 메뉴와 한 번도 같은 날 나오지 않았지만, "
    "각각 10일 이상 등장한 메뉴를 찾아봅니다."
)

# 위의 좁혀 보기와 완전히 별개인 메뉴 선택창
independent_menu = st.selectbox(
    "함께 나온 적 없는 짝 찾기 - 기준 메뉴 선택",
    sorted(menu_count.keys()),
    key="never_together_menu_selector"
)

# 기준 메뉴가 등장한 날짜 수
selected_menu_days = menu_count[independent_menu]

# 기준 메뉴가 등장한 날의 메뉴들을 모두 모음
coexisting_menus = set()

for basket in baskets:

    if independent_menu in basket:

        coexisting_menus.update(
            basket - {independent_menu}
        )

# 기준 메뉴와 한 번도 함께 나오지 않은 메뉴 찾기
never_together = []

for menu, count in menu_count.items():

    # 자기 자신 제외
    if menu == independent_menu:
        continue

    # 10일 이상 등장하고 기준 메뉴와 동시 등장한 적이 없는 경우
    if count >= 10 and menu not in coexisting_menus:

        never_together.append({
            "메뉴": menu,
            "나온 날": count
        })

never_df = pd.DataFrame(
    never_together,
    columns=["메뉴", "나온 날"]
)

if not never_df.empty:

    never_df = never_df.sort_values(
        by="나온 날",
        ascending=False
    ).reset_index(drop=True)

# 기준 메뉴의 등장 횟수 표시
st.markdown(
    f"**선택한 메뉴: {independent_menu}**"
)

col1, col2 = st.columns(2)

col1.metric(
    "기준 메뉴가 나온 날",
    f"{selected_menu_days}일"
)

col2.metric(
    "함께 나온 적 없는 메뉴",
    f"{len(never_df)}개"
)

if never_df.empty:

    st.info(
        "조건에 맞는 메뉴가 없습니다. "
        "다른 메뉴를 선택해 보세요."
    )

else:

    st.caption(
        "기준 메뉴와 동시 등장 0회, "
        "개별 등장 10일 이상인 메뉴 목록"
    )

    st.dataframe(
        never_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )


# ---------------------------------------
# 15. 분석 지표 설명
# ---------------------------------------

st.divider()

st.subheader("💡 분석 지표 알아보기")

with st.expander("지지도, 신뢰도, 향상도란?"):

    st.markdown("""
    **1. 지지도 (Support)**

    전체 급식 중 두 메뉴가 함께 나온 비율입니다.

    **2. 신뢰도 (Confidence)**

    조건 메뉴가 나온 날에 결과 메뉴도 함께 나온 비율입니다.

    **3. 향상도 (Lift)**

    두 메뉴가 독립적으로 등장한다고 가정했을 때보다
    실제로 얼마나 자주 함께 등장하는지 나타냅니다.

    - 향상도 > 1 : 함께 등장하는 경향이 있음
    - 향상도 = 1 : 서로 독립적으로 등장
    - 향상도 < 1 : 함께 등장하는 경향이 상대적으로 적음

    **4. 함께 나온 적 없는 짝**

    기준 메뉴와 같은 날 등장한 기록이 한 번도 없으면서
    개별적으로는 10일 이상 등장한 메뉴입니다.

    **주의:** 함께 등장하는 횟수만으로 메뉴 사이의
    인과관계를 판단할 수는 없습니다.
    """)
