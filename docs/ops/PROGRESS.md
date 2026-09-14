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

## 이번 변경 (데이터모델 검수·수정)

- DATA-MODEL.md 검수(A/B) 결과를 실제 파일과 대조한 뒤, 유효한 문제만 수정함. 자식이 기준4 묶음에 넣은 14번·20번 금지 조합은 지급/배분과 직접 무관하여 문서 오류로 보지 않고 수정하지 않음. 자식이 3.6 표에 "반영된 문장 없음"이라고 지적한 부분은 실제 482행과 불일치하여 수정 범위에서 제외함.
- 수정 절: 3.3.3(text sha256 별도 계산·별도 필드 관리 명시), 3.6 표(periodAdopted가 adopted 종속 필드 경계 명확화), 3.6.1(채택본 교체가 정정의 한 종류이며 5.1/5.2 적용 연결), 3.8.3(순회 표현 "함께 갱신"을 "재계산 때문에 역수정하지 않음, 수동 덮어쓰기 금지"로 정리), 3.9(ratePerHourWon 범위 밖 값 저장 가능 + 정상 계산 미사용 + 16번 금지 조합 참조), 3.10(동일 지급 중복 판단 기준을 7장 규칙 8번 actualPaymentId+입금일+금액+채널로 명확화, 파일 해시/새 ID만으로 단정 금지), 20번 금지 조합(노출 금지 대상을 photo/pdf 식별 조합과 text sourceValue 원문 전체로 분리, 원본 blob 경로 표현을 원본 저장 키로 통일).
- 문서 검산: 항목 순서 변경에도 출처 유지(3.5 targetId/targetItemId/fieldName), 수정본 채택 전후 상태(3.6.1/5.1/5.2), 22시~다음날06시 휴게60분=420분(DOMAIN.md 22.1), 같은 입금 중복 등록(DOMAIN.md 19.3 + DATA-MODEL.md 3.10/7장 규칙 8번) 검토 완료. 충돌 없음 확인.
- 기존 tests/verify_wage_cases.py 실행: 정상 exit 0, --negative-test/-c3-override/-empty-list/-missing-f/-dup-a/-short-b-expected/-mutate-b-expected 각각 exit 1. 총 8개 종료코드(정상 1, 비정상 7). 이전 기록과 일치.

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
- doc-compare 원본 보관: `vendor/doc-compare-original/compare_docs.py`, `vendor/doc-compare-original/SKILL.md`에 원본 그대로 보관. 원본 수정 없음.
- doc-compare 원본/보관본 해시: compare_docs.py 원본·보관본 모두 `9a1c4fbf5d86a37d814aaecba17faa24bcb8407a027bc7faa5d170cd7b2cc63a`, SKILL.md 둘 다 `5791458c0401b3e346264238ae3de36b0359a0a84c717a95630d893ec5d4c09f` → 일치.
- doc-compare 원본 실제 실행 반례 결과(이번 턴 재확인, 원본 수정 없음):
  - a) 급여 이동(1↔2) + 지급일 문장 변경: 원본은 순서 변경 2건 + 본문 변경 1건(섹션 변경) 둘 다 보고, "실제 변경 건수 (순서 변경 제외): 1건"
  - c) 답변 기록 보관 7일 → 14일: 원본은 "14일"만으로 "14일 이내 회신 의무 신설"을 붙임 (의무 추정 있음)
  - d) 구1 오전수당/구2 현장수당 → 신2 오전수당: 원본은 순서 변경 1건(1→2) + 삭제 1건(오전수당) + 변경 1건(현장→오전)으로 보고하고 "실제 변경 건수 (순서 변경 제외): 2건" — 동일 신항목을 이동과 변경에 중복 매칭 (문제)
- doc-compare 개선: `backend/doc_compare/compare_docs.py` 업데이트
  - 파싱 시 번호 항목 줄을 본문(body_lines)에서 분리해 순수 이동만으로는 본문 변경으로 잡히지 않게 수정
  - 번호 항목 매칭을 이동(정규화 텍스트 동일) 먼저 소비한 뒤, 남은 동일 번호만 변경으로, 최종 남은 구/신 항목만 삭제/추가로 분류하도록 수정 (같은 항목을 두 번 사용하지 않음)
  - 항목 변경 유무와 무관하게 일반 문단 본문 변경은 섹션 변경으로 항상 보고하도록 수정
- doc-compare 테스트 확장: `backend/tests/test_compare.py` (20사례)
  - 기존 13개 유지 + 신규 7개 추가: 구1 식대→신2 식대(항목 변경 0, 본문 변경 0), 구1 식대→신1 교통비/신2 식대(이동1+추가1), 식대 금액+지급일 문단 동시 변경(항목1+본문1), 순수 이동 전부 0건 확인, 번호 항목과 본문 비교 독립성 확인 등
  - tempfile/subprocess로 통일, 셸 임시파일/head/tail 없음
- doc-compare 테스트 실행: `python -B backend/tests/test_compare.py` → exit 0, 20개 전부 통과
- 미흡했던 3사례 반영 확인:
  - ① 구1 식대 → 신2 식대만 바뀌면 이동 1건, 항목/본문 변경 0건 (test_move_only_same_item_different_number, test_pure_move_all_zero)
  - ② 구1 식대 → 신1 교통비/신2 식대면 이동 1건 + 추가 1건(교통비), 삭제/변경 없음 (test_move_and_add, test_move_with_new_item_in_place)
  - ③ 식대 5만원→6만원과 일반 문단 지급일 10일→20일이 같이 바뀌면 항목 변경 1건 + 본문 변경 1건 둘 다 보고 (test_item_change_and_body_change)
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
