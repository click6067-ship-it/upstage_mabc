# PROGRESS.md

## 과거 이력 (이전 턴까지 완료한 것)

- 작업 폴더 확인: `C:\Users\click\upstage_mabc`
- Git 상태 확인: `main` 브랜치, 마지막 커밋 `819f5fe`
- Node.js/npm 버전 확인: `v22.23.2`, `10.9.8`, `10.9.8`
- Python 환경 확인: Hermes venv 기준 `Python 3.11.16`
- pip 목록 조회 실패 확인: pip 파일이 없어 패키지 목록을 확인하지 못함
- doc-compare 원본 파일 위치 확인: `C:\Users\click\Desktop\doc-compare-extracted\`에 `SKILL.md`, `compare_docs.py` 존재
- Hermes 스킬 목록 확인: `doc-compare`는 현재 목록에 없음(파일 존재와 등록은 별개)
- 브라우저 도구 존재 확인: `drive_preview`, `desktop_preview` 확인됨(실작동 미확인)
- BASELINE.md 저장: `C:\Users\click\upstage_mabc\docs\ops\BASELINE.md`
- BASELINE.md 변경: `BRAINSTOOM.md` → `BRAINSTORM.md` 오타 정정, Node/npm 실행 경로 "확인됨" → "미확인" 정정, Node/npm 실제 실행 파일 경로 미확인, Git 상태를 "생성 전 clean, 미추적 3개"로 정정
- PROGRESS.md 1차 변경: Node/npm 실제 실행 파일 경로 미확인 항목 추가, PRD.md 생성 이력 추가
- PRD.md 1차 버전 생성: 루트 `PRD.md` 작성 후 재열람 성공. 이주노동자 일·월급 웹앱 PRD 초안.
- AGENTS.md 관련(이전 턴):
  - 루트 `C:\Users\click\upstage_mabc\AGENTS.md` 생성을 시도했으나 Hermes 승인 프롬프트 시간초과로 실패함.
  - 이후 사용자가 직접 저장함(이전 Hermes 승인 시간초과 실패 → 사용자 직접 저장). 내가 생성하지 않음.
  - 거절로 단정하지 않음. 시간초과 실패와 사용자 측 저장은 별개 사건이다.
- 직전 턴(검산): DOMAIN.md 11.1 기타·공제·명세서 합계 항목 복구, B1/B2 지급 차이 계산가능·기본급 참고 산술 보류 명시. 검산 8회 실행(정상 1회, 고의 실패 7회) 확인.
- 이번 턴(지급·달력): DOMAIN.md 19~24절 지급 배분·입금일/급여기간 구분·달력 상태·야간/휴게·시급 규칙 보완, 용어 정정(현금 수령, 근무기록 작성/정정일, 휴게가 전체 경과시간보다 길 때 보류). 검산 1회 정상 실행(exit 0).
- 이번 턴(정정 버전): DOMAIN.md 25절 정정 버전 규칙 추가(원문/추출 후보/사용자 확인값 분리, 수정본 적용은 사용자 확인 후, 확인값 변경과 새 결과 버전 저장 함께 성공, 늦은 OCR/AI 응답 덮어쓰기 금지, 정정 시 같은 버전 갱신, 내려받은 PDF 소급 수정 불가). 검산 재실행 exit 0 확인.

## 최신 SHA-256

- `tests/fixtures/wage-cases.json`: `470ed5acb90fb174bedd9c51e95a907bc3ce229bfa06ee9868fa31eb20acdf34`
- `tests/verify_wage_cases.py`: `95f02a19bae17f429ab732141b85d92d53fbb4f0f0461eac5fad1f4295e58d16`

## 이번 변경 (검산 스크립트 고정 + DOMAIN/JSON 수정 + INDEX/PROGRESS 갱신 + 정정 버전 규칙)

- DOMAIN.md 11.1: 기타 384,000원·공제 208,000원·명세서 기본급·명세서 합계 항목 복구. B1/B2 문단에서 지급 차이 계산 가능 및 기본급 참고 산술 보류를 명시.
- 검산 스크립트: 정상 실행(exit 0) 및 --negative-test, --c3-override, --empty-list, --missing-f, --dup-a, --short-b-expected, --mutate-b-expected 각각 exit 1 확인.
- 종료코드: 정상=0, 나머지 7개=1.
- SHA-256: wage-cases.json `470ed5acb90fb174bedd9c51e95a907bc3ce229bfa06ee9868fa31eb20acdf34`, verify_wage_cases.py `95f02a19bae17f429ab732141b85d92d53fbb4f0f0461eac5fad1f4295e58d16`.
- INDEX/PROGRESS: 실행 명령 8개, 실제 종료코드 8개, 실제 결과, 최신 SHA-256, 미검증 항목 유지.
  - 표준라이브러리만 사용. 설치 없음. `-B`로 바이트코드 캐시 미작성.
  - 정상 실행(`python -B tests/verify_wage_cases.py`) → exit 0.
  - `--negative-test`: F의 기대 `rounded_won`을 메모리에서만 166으로 바꿔서 exit 1.
  - `--c3-override`: C3 수령액만 120001로 메모리에서 바꿔서 exit 1.
  - 원본 JSON은 변조하지 않고, 3가지 모드를 각각 별도 프로세스 실행으로 확인.
  - C2/C3는 input에서 계산한 숫자/보류 상태를 expected와 대조. 답을 직접 적어두지 않음.
  - B: 수정본 적용 여부와 산술별 확인/보류를 실제 입력으로 검사. 단계별 `(지급 차이, 기본급 참고 산술 차이)` = `(20000,null), (0,null), (0,96000), (0,72000), (72000,0)`.
  - C1(실제 수령 null)과 C4(확인된 0원 수령)를 별도 사례로 분리.
  - 시급은 시간당 원 유지. 분당 시급 필드와 `hourly_rate // 60` 규칙 제거.
  - D/E/F: 합산분자의 `(n + 30) // 60`으로 계산. 500/168/167원 유지.
- DOMAIN.md 19~24절: 지급 배분·입금일/급여기간 구분·달력 상태·야간/휴게·시급 규칙 보완 및 용어 정정.
  - 19.4: "현금 출금" → "현금 수령".
  - 21.1: "명세서 작성/정정일" → "근무기록 작성/정정일".
  - 22.4: 휴게가 근무시간보다 길 때 → 휴게가 전체 경과시간보다 길 때 보류.
  - 각 절에 입력 예시와 계산 가능/보류 결과 추가.
- DOMAIN.md 25절(정정 버전 규칙) 추가.
  - 원문/추출 후보/사용자 확인값 분리, 새 파일 업로드로 기존 값 자동 교체 금지.
  - 수정본 적용은 사용자 확인 후, 이전 원문/이력 보존.
  - 확인값 변경과 새 결과 버전 저장은 함께 성공, 늦은 OCR/AI 응답이 최신 확인값을 덮지 않음.
  - 정정 시 비교/계산/질문/설명/한국어+선택언어/출력까지 같은 버전으로 갱신, 무관한 다른 달 변경 금지.
  - 내려받은 PDF는 소급 수정 불가, 앱에서 구버전 표시 + 새 파일 생성 규칙.
  - 정상 흐름과 예외(늦은 응답, 출력 재생성) 예시 포함.
- INDEX.md: 이번 검산 실행 기록(명령, exit 0, 두 SHA-256) 추가.
- PROGRESS.md: 과거 이력 목록형으로 정리, 직전 턴(검산 8회: 정상 1/고의 실패 7)과 이번 턴(지급·달력 1회 정상, 정정 버전 추가) 구분.
- T02 전체 완료는 아직 표시하지 않음.
  - B: `hourly_rate_per_hour=12000`만 남기고 `hourly_rate_per_minute` 제거.
  - C 계열에 C4(명세서 150,000원, 확인된 실제 수령 0원) 추가.
  - 기존 A/B/C1/C2/C3/D/E/F 구조 유지, expected 수치 그대로.
- `docs/evidence/INDEX.md` 수정
  - 실행 명령, 실제 종료코드(정상 0 / --negative-test 1 / --c3-override 1), 파일 SHA-256, 미검증 항목 기록.
  - 검산 코드 복사 대신 명령과 결과만 남김.
- `docs/ops/PROGRESS.md` 재작성
  - 과거 이력·직전 턴 변경 유지, 이번 변경을 위 내용대로 반영.
  - T02 전체 완료는 아직 표시하지 않음.

## 미실행/미확인/실패

- Node/npm 실제 실행 파일 경로: 미확인
- Node.js/npm 최신 버전 여부: 미확인
- 제품용 별도 Python 환경: 미확인
- pip 패키지 목록: 실패 (pip 파일 없음, 조회하지 못함)
- Vercel CLI 명령: 찾지 못함 (토큰 존재 여부는 이 결과만으로 판단하지 않음)
- doc-compare 스크립트 실제 실행: 미실행
- doc-compare Hermes 등록 상태: 목록 기준 미확인
- 브라우저 도구 실제 동작: 미확인
- 실제 사용자 검토: 미실행
- 번역 검토: 미실행
- 앱 코드 실행·설치·설정·화면 테스트: 미실행 (문서·합성 검산과 구분)
- 정정 버전 저장/비교 범위: 미확인
- 늦은 OCR/AI 응답 처리 방식: 미확인
- 내려받은 PDF 구버전 표시·새 파일 생성 규칙: 미확인
- T02 전체 완료 표시: 아직 하지 않음

## 다음 작업

- 사용자가 지시할 때까지 시작하지 않음.
- 현재 수정·검증 완료된 파일: `docs/specs/DOMAIN.md`, `tests/fixtures/wage-cases.json`, `docs/evidence/INDEX.md`, `docs/ops/PROGRESS.md`, `tests/verify_wage_cases.py`.
