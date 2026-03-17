# 전주시 가로등 정보 대시보드

공공데이터포털 OpenAPI를 이용한 Streamlit 수업용 예제

## 준비

1. 공공데이터포털에서 `전북특별자치도 전주시_가로등 정보 서비스` 검색
2. 활용신청 후 인증키 발급
3. 가상환경 생성과 패키지 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 실행

환경변수 기반 실행 방식

```bash
export JEONJU_API_KEY="발급받은_인증키"
streamlit run app.py
```

환경변수 미설정 시 사이드바 직접 입력 방식

## 수업 포인트

- 공공데이터포털 문서 읽기
- `requests`로 OpenAPI 호출하기
- XML 응답을 `pandas.DataFrame`으로 바꾸기
- `Streamlit`으로 검색, 지도, 테이블, 다운로드 기능 붙이기

## 참고

- 예제 API: 공공데이터포털 `전북특별자치도 전주시_가로등 정보 서비스`
- 엔드포인트: `http://openapi.jeonju.go.kr/rest/streetlamp/getStreetlamp`
- 주요 파라미터: `authApiKey`, `startPage`, `pageSize`, `boxNm`
