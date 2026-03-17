import os
import xml.etree.ElementTree as ET
from typing import Any

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="전주시 가로등 정보 대시보드",
    page_icon="💡",
    layout="wide",
)

API_URL = "http://openapi.jeonju.go.kr/rest/streetlamp/getStreetlamp"
EXPECTED_FIELDS = [
    "seq",
    "boxNm",
    "lampCnt",
    "poleNum",
    "posx",
    "posy",
    "baseDate",
]


def xml_to_records(xml_text: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    root = ET.fromstring(xml_text)
    meta = {
        "resultCode": root.findtext(".//resultCode", default=""),
        "resultMsg": root.findtext(".//resultMsg", default=""),
        "totalCount": root.findtext(".//totalCount", default=""),
        "startPage": root.findtext(".//startPage", default=""),
    }

    candidate_paths = [
        ".//item",
        ".//items/item",
        ".//list",
        ".//row",
    ]

    records: list[dict[str, Any]] = []
    for path in candidate_paths:
        nodes = root.findall(path)
        parsed = []
        for node in nodes:
            record = {child.tag: (child.text or "").strip() for child in list(node) if list(node)}
            if record:
                parsed.append(record)
        if parsed:
            records = parsed
            break

    if not records:
        for node in root.iter():
            child_tags = {child.tag for child in list(node)}
            if {"boxNm", "poleNum"} & child_tags:
                record = {child.tag: (child.text or "").strip() for child in list(node)}
                if record:
                    records.append(record)

    return records, meta


@st.cache_data(show_spinner=False, ttl=600)
def fetch_streetlamps(
    api_key: str,
    start_page: int,
    page_size: int,
    box_name: str | None,
) -> tuple[pd.DataFrame, dict[str, str], str]:
    params = {
        "authApiKey": api_key,
        "startPage": start_page,
        "pageSize": page_size,
    }
    if box_name:
        params["boxNm"] = box_name

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()

    records, meta = xml_to_records(response.text)
    result_code = meta.get("resultCode", "")
    if result_code and result_code != "00":
        raise RuntimeError(f'{result_code}: {meta.get("resultMsg", "Unknown API error")}')

    df = pd.DataFrame(records)
    if df.empty:
        return df, meta, response.text

    for col in ["lampCnt", "posx", "posy", "seq"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df, meta, response.text


st.title("전주시 가로등 정보 대시보드")
st.caption("공공데이터포털 전북특별자치도 전주시 가로등 정보 서비스 기반 Streamlit 예제")

with st.sidebar:
    st.header("API 설정")
    env_key = os.getenv("JEONJU_API_KEY", "")
    api_key = st.text_input(
        "전주시 OpenAPI 인증키",
        value=env_key,
        type="password",
        help="환경변수 JEONJU_API_KEY 로도 설정 가능",
    )
    start_page = st.number_input("시작 페이지", min_value=1, value=1, step=1)
    page_size = st.select_slider("페이지 크기", options=[10, 20, 50, 100], value=50)
    box_name = st.text_input("분전함명 검색", placeholder="예: 흑석로01")
    fetch_button = st.button("데이터 불러오기", type="primary", use_container_width=True)

if not api_key:
    st.info("왼쪽 사이드바에 전주시 OpenAPI 인증키 입력 후 실습 진행")
    st.stop()

if fetch_button or "loaded_once" not in st.session_state:
    st.session_state["loaded_once"] = True
    try:
        with st.spinner("전주시 가로등 정보를 불러오는 중..."):
            df, meta, raw_xml = fetch_streetlamps(
                api_key=api_key,
                start_page=int(start_page),
                page_size=int(page_size),
                box_name=box_name.strip() or None,
            )
        st.session_state["df"] = df
        st.session_state["meta"] = meta
        st.session_state["raw_xml"] = raw_xml
    except Exception as exc:
        st.error(f"데이터 조회 실패: {exc}")
        st.stop()

df = st.session_state.get("df", pd.DataFrame())
meta = st.session_state.get("meta", {})
raw_xml = st.session_state.get("raw_xml", "")

if df.empty:
    st.warning("조회 결과 없음")
    st.stop()

metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("조회 건수", f"{len(df):,}")
metric2.metric("총 등 개수", f'{int(df["lampCnt"].fillna(0).sum()):,}' if "lampCnt" in df.columns else "0")
metric3.metric("분전함 수", f'{df["boxNm"].nunique():,}' if "boxNm" in df.columns else "0")
metric4.metric("결과 코드", meta.get("resultCode", ""))

st.subheader("기본 정보")
info1, info2, info3 = st.columns(3)
info1.write(f'결과 메시지: {meta.get("resultMsg", "")}')
info2.write(f'총 건수: {meta.get("totalCount", "")}')
info3.write(f'시작 페이지: {meta.get("startPage", "")}')

left, right = st.columns([1.2, 0.8])

with left:
    st.subheader("지도")
    if {"posx", "posy"} <= set(df.columns):
        map_df = df.dropna(subset=["posx", "posy"]).rename(columns={"posy": "lat", "posx": "lon"})
        if map_df.empty:
            st.info("지도 표시 가능 좌표 없음")
        else:
            st.map(map_df[["lat", "lon"]], use_container_width=True)
    else:
        st.info("좌표 컬럼 없음")

with right:
    st.subheader("분전함별 가로등 수")
    if {"boxNm", "lampCnt"} <= set(df.columns):
        chart_df = (
            df[["boxNm", "lampCnt"]]
            .dropna()
            .groupby("boxNm", as_index=False)["lampCnt"]
            .sum()
            .sort_values("lampCnt", ascending=False)
            .head(15)
        )
        st.bar_chart(chart_df.set_index("boxNm"))
    else:
        st.info("집계 가능 컬럼 없음")

st.subheader("상세 테이블")
ordered_columns = [col for col in EXPECTED_FIELDS if col in df.columns]
extra_columns = [col for col in df.columns if col not in ordered_columns]
st.dataframe(df[ordered_columns + extra_columns], use_container_width=True)

csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="CSV 다운로드",
    data=csv_bytes,
    file_name="jeonju_streetlamp.csv",
    mime="text/csv",
)

with st.expander("원본 XML 응답 확인"):
    st.code(raw_xml, language="xml")

st.markdown(
    """
    ---
    수업 확장 방향
    1. 다른 전주 공공데이터 서비스로 주제 변경
    2. 지도 라이브러리 확장
    3. 여러 공공데이터 결합 기반 도시 안전 서비스 설계
    """
)
