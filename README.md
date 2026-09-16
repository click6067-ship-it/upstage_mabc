# Paychecker

언어 장벽을 겪는 외국인 노동자의 월급 확인부터 회사 문의 준비까지 돕는 AI

월급 문제를 스스로 설명하고 필요한 확인을 이어가기 어려운 사람을 돕는 것이 목표다.
첫 적용 대상은 한국어 명세서가 낯선 외국인 노동자의 월급 문제다.

- 공개 URL: <https://paychecker-gray.vercel.app/>

---

## 지금 가능한 기능

- PDF 2장(정정 전/후 명세서) 업로드와 항목·금액·원문 정보 추출
- 추출 초안에서 원문과 추출값 확인
- 같은 급여기간의 정정 전/후 비교
- Solar 설명과 회사에 확인할 질문 생성
- 질문 복사
- 정정 후 값 수정 후 재비교

---

## 간단 사용 예시

정정 전/후 예시 명세서를 사용해 식대 항목을 비교하고, 이후 식대를 다시 수정해 재비교한다.

1. 시작 화면에서 `명세서 PDF 비교`를 선택한다.
2. 정정 전/후 예시 명세서를 사용한다.
3. 식대 항목을 선택해 적용에 넣는다.
4. 같은 2026년 8월 기간과 사업장을 확인한다.
5. 식대끼리 연결한다.
6. 50000 / 70000을 비교한다.
7. Solar 질문을 복사한다.
8. 식대를 80000으로 수정한 뒤 다시 비교한다.

- [PRD (./PRD.md)](./PRD.md)

---

## 향후 계획

- 월별 근무시간 기록 보관과 급여 추적
- 개인화 챗봇
- 회사 답변 관리
- 앱 안의 다국어 표현 검색

현재는 EPS 외국어 표현 안내 공식 사이트 연결만 제공한다.

---

## 외국어 표현 찾아보기

회사와 대화할 때 참고할 수 있는 외국어 표현 안내다.

- 버튼: 외국어 표현 찾아보기 (새 탭)
- 링크: <https://eps.hrdkorea.or.kr/e9/user/language/language.do?method=languageGuide>
- 새 탭으로 열고, 사용자 자료는 전달하지 않는다.
- DB 수집이나 번역 기능 구현은 포함하지 않는다.

---

## 실행 방법

저장소 루트에서 백엔드를 먼저 실행한 뒤, 별도 터미널에서 프론트엔드를 실행한다.

### 백엔드

```bash
cd <저장소 루트>
pip install -r requirements.txt
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000
```

### 프론트엔드

별도 터미널에서 `frontend` 디렉터리로 이동해 실행한다.

```bash
cd frontend
npm install
npm run dev
```

---

## 환경변수

이름만 적는다. 실제 값은 넣지 않는다.

- `UPSTAGE_API_KEY`
  - PDF 파싱과 Solar 호출에 사용한다.
- `PAID_FEATURES_ENABLED`
  - 설명 기능 사용 여부를 켜는 플래그다.
  - 코드 기본값은 꺼져 있다.
  - 설명 기능을 쓰려면 `PAID_FEATURES_ENABLED=1`로 설정한다.

---

## API 엔드포인트

- `GET /api/health`
- `POST /api/parse-upload`
- `POST /api/compare`
- `POST /api/explain`

---

## 기술 스택

- 프론트엔드: React / TypeScript / Vite / CSS
- 백엔드: Python / FastAPI
- 문서 처리: Upstage Document Parse / Solar Pro 4
- 배포: Vercel

---

## doc-compare에서 서비스로 이관된 역할

예선 doc-compare에서 다룬 항목 대응 개념과 변경/추가/삭제/이동 구분을 현재 서비스 흐름으로 옮겼다.
단순히 두 문서를 비교하는 데서 끝나지 않고, 사용자가 항목 대응을 확인·조정하고 그 결과를 바탕으로 비교·설명까지 이어지도록 구성했다.

---

## 문서

- `PRD.md` — 제품 요구사항
- `README.md` — 이 파일

---

## 팀 정보

- 서비스명: Paychecker
- 팀번호: 4
- 팀명·발표자: 김용하
- 팀 유형: 개인팀
