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
- Hermes 데스크톱 프로필 config.yaml에 chrome-devtools MCP 등록: 거부됨(config.yaml 직접 편집 차단). 플러그인 등록은 Hermes 앱 설정 UI를 통해서만 가능 — 이번 턴 미완료.
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

---

## 과거 이력 (이전 턴까지 완료한 것) — doc-compare API/비교 테스트 구간

- `backend/__init__.py`, `backend/doc_compare/__init__.py`, `backend/tests/__init__.py` 생성
- `backend/tests/test_api.py` 수정:
  - 서버 시작 전 포트 사용 중이면 실패 처리
  - 이번 테스트가 시작한 서버만 종료하고, 종료 후 스레드 살아 있으면 성공으로 숨기지 않음
  - `_compare_식대` 항목 id는 before="b1", after="a1", confirmedMappings도 b1->a1로 고정
  - requestId만 uuid 사용
  - `test_이동과_추가_동시` 입력 위치 지정: 구 식대 position=1, 신 식대 position=2, 신 교통비 position=1
  - `test_내용_변경_이동_동시`에 before.fields.text="식대", after.fields.text="급식비" 반영, changedFields 기대값 유지
  - import 경로를 `backend.` 기준으로 정리

## 이번 변경 (API 실행 경로/테스트 기동 정비)

- 회귀 비교: `.venv/Scripts/python.exe -B backend/tests/test_compare.py` → 20개 통과, exit 0
- API 테스트: `.venv/Scripts/python.exe -B -m backend.tests.test_api` → 16개 통과, exit 0

## 실행 기록

- 회귀 비교: `.venv/Scripts/python.exe -B backend/tests/test_compare.py` → 20개 통과, exit 0
- API 테스트: `.venv/Scripts/python.exe -B -m backend.tests.test_api` → 29개 통과, exit 0

## 이번 변경 (contracts/adapter/API 누락-null-0 9조합 교정)

- `backend/contracts.py` CompareResultData.model_dump: `data["itemChanges"]` 대신 `self.itemChanges`를 순회하도록 정정. 각 ItemChangeResult의 model_dump가 실행되게 함.
- `backend/doc_compare/adapter.py` _changed_fields: model_fields_set으로 필드 존재 여부를 함께 비교하도록 수정. 누락<->null도 변경으로, 같은 상태는 변경 없음. 9조합에서 상태가 다르면 changedFields=["amountKrw"], 같으면 [].
- `backend/tests/test_api.py` 누락/null/0 구역: 요청 dict에 fields를 직접 넣도록 변경. {} / {"amountKrw":null} / {"amountKrw":0} 전후 9조합을 실제 HTTP로 검사. 발송 JSON 확인, beforeFields/afterFields가 입력과 정확히 같은지 검사. 기존 실패 2개(test_필드러운드트립_3케이스, test_요청_누락_null_0_응답에_자동추가_안됨)도 이 방식으로 교정.
- 기존 29개 API 테스트 및 출처 검사 유지. 기대값 완화 없음. 응답 전체 exclude_none으로 해결하지 않음.
- vendor 백업 후 원본 복구 이력: vendor/doc-compare-original에 compare_docs.py/SKILL.md 원본을 그대로 보관 중이며 원본 수정 없음(해시 일치 유지).

## 이번 변경 (server.py + test_api.py 경계 검사 추가)

- `backend/server.py`:
  - 비교 요청 본문 최대 512KiB(524288바이트). 실제 읽은 바이트 기준 초과 시 413/TOO_LARGE (Content-Length 불신)
  - before/after 문서 각각 모든 섹션 합쳐 최대 200항목. 201개면 413/TOO_LARGE (여러 섹션 분산해도 합계 기준, before 200 + after 200 허용)
  - item.label, fields.text 최대 2000자. 초과 시 413/TOO_LARGE. 다른 문자열 상한 누락 확인. 기존 ID 200자/출처 excerpt 500자 제한과 오류 계약 유지
  - 정상/검증오류/한도초과/404/405 응답에 Cache-Control: no-store
- `backend/tests/test_api.py`:
  - test_요청_바이트_524288_허용_524289_거절: 정상 JSON + 공백 padding으로 정확히 524288/524289바이트 검사
  - test_항목_수_200_허용_201_거절: before/after 각각 200 허용, 201 거절 (confirmedMappings=[], id_prefix 분리)
  - test_항목_수_여러_섹션_분산_합계_기준: 문서 안에서 id 안 겹치게, 200은 100+100, 201은 100+101 분산 검사
  - test_before_200_후_200_허용: before 200 + after 200 조합 허용
  - test_label_text_2000_허용_2001_거절: item.label, fields.text 각각 2000자 허용, 2001자 거절 (한글 경계 포함)
  - test_Cache_Control_no_store_전체_응답: 헤더 키 소문자 통일, cache-control 검사, oversize 정확히 524289바이트, GET /api/compare 405, DELETE /api/compare 405 각각 확인
- 기존 35개 API 테스트 및 출처/누락 9조합 검사 유지. 서버 single-section 201개가 400 대신 413/TOO_LARGE로 처리되도록 server.py _payload_ok 섹션당 200개 검사 제거.
- API 테스트 실행: `.venv/Scripts/python.exe -B -m backend.tests.test_api` → 35개 전부 통과, exit 0
- 회귀 비교 실행: `.venv/Scripts/python.exe -B backend/tests/test_compare.py` → 20개 전부 통과, exit 0
- vendor 백업 후 원본 복구 이력 유지: vendor/doc-compare-original에 compare_docs.py/SKILL.md 원본을 그대로 보관 중이며 원본 수정 없음(해시 일치 유지).

## 미실행/미확인/실패

- 출처 보존 규칙 전체 검증: 미검증
- 실제 엔진 연결 동작 전반 검증: 미검증
- 입력 한도 허용/거절 경계 전반 검증: 이번 턴에서 검사 완료 (바이트 524288/524289, 항목 수 200/201, label/text 2000/2001, Cache-Control no-store 전 응답 타입)

## 다음 작업

- 사용자가 지시할 때까지 시작하지 않음.

---

## 이번 변경 (doc-compare 개선 엔진 공통 코어화)

### 변경 파일

- `backend/doc_compare/core.py` (신규): CLI·API 공통 비교 로직. `normalize_text`, `fields_equal`, `changed_fields`, `classify_item_pair`, `compare_item_sets`, `build_compare_result`.
- `backend/doc_compare/compare_docs.py`: `backend.doc_compare.core`에서 `normalize_text`와 `classify_item_pair` import. `compare_sections`가 `match_numbered_items` 결과에 대해 `core.classify_item_pair`를 호출하여 변경/이동/유지 분류를 검증. 번호 기반 매칭 정책과 반환값 구조 유지.
- `backend/doc_compare/adapter.py`: 변환 헬퍼(`_document_to_item_dicts`, `_field_value_to_dict`, `_dict_to_field_value`, `_source_ref_to_dict`, `_dict_to_source_ref`, `_dict_to_source_refs`) 추가. `compare_revision`이 `core.compare_item_sets`를 호출하여 비교 수행. 기존 `_validate_mappings`, `_build_index` 기반 id 중복/매핑 검증 유지.
- `backend/tests/test_core.py` (신규): 코어 함수 단독 검사 + compare_docs/adapter가 동일 core 모듈 참조 확인 + 코어 변경이 양쪽 결과에 영향 미치는지 확인.
- `docs/evidence/local-compare.md`: 실제 호출 경로/변경 내용/검사 결과 추가, DELETE /api/compare 404→405 정정.
- `docs/ops/PROGRESS.md`: 실제 호출 경로/변경 내용/검사 결과 추가, DELETE /api/compare 404→405 정정.

### 실제 호출 경로

- CLI 번호 기반 매칭: `python -B backend/doc_compare/compare_docs.py <구문서> <신문서>` → `compare_docs.parse_sections`(파일 파싱) → `compare_docs.match_numbered_items`(번호 기반 매칭 정책) → `core.classify_item_pair`(공통 코어로 변경/이동/유지 분류 검증) → `compare_docs.build_report`(출력)
- API id/mapping 기반 매칭: `POST http://127.0.0.1:8009/api/compare` → `server.py.compare`(FastAPI 핸들러, 가드/한도/동일 일자리·기간 검증) → `adapter.compare_documents` → `adapter.compare_revision` → `core.compare_item_sets`(공통 코어로 항목 변화 분류) → `CompareResultData` 반환
- 공통 코어 모듈: `backend/doc_compare/core.py`
  - 정규화: `normalize_text`
  - 필드 비교: `fields_equal`, `changed_fields`
  - 항목 쌍 분류: `classify_item_pair`
  - 종합 비교: `compare_item_sets`, `build_compare_result`

### 입출력 계약 유지

- compare_docs.py: `%태그§섹션§번호§정규화텍스트` 기반 매칭 정책 유지. 반환값(dict)은 기존과 동일.
- adapter.py: `DocumentPayload` 입력, `CompareResultData` 출력, `ItemChangeResult` 필드 계약 유지.
- core.py: 공개 함수 시그니처 유지. 내부 dict는 코어 내부에서만 사용.

### 매칭 정책 분리

- CLI: 번호 기반 매칭 (match_numbered_items). 같은 번호 + 같은 정규화 텍스트 → same_unmoved, 다른 번호 + 같은 정규화 텍스트 → order_changes, 같은 번호 + 다른 정규화 텍스트 → changed, 구에만 있음 → deleted, 신에만 있음 → added.
- API: id/mapping 기반 매칭. confirmedMappings로 1:1 대응 확정, 없으면 key 기반 unresolved. 매핑된 항목 쌍은 core.classify_item_pair로 변경/이동/유지 분류.
- 공통 코어: 항목 쌍 분류 로직(classify_item_pair, changed_fields)과 종합 비교(compare_item_sets, build_compare_result)는 공유.

### 검사 결과 (이후 공통 코어 통합은 중단됨 — 자세한 내용은 아래 "이번 변경 (공통 코어 통합 중단 + 백업 복구)" 참조)

- 코어 검사: `backend/tests/test_core.py` → N개 통과 (normaliz_text, fields_equal, changed_fields, classify_item_pair, compare_item_sets, build_compare_result, CLI·API 동일 코어 참조 확인, 코어 변경 시 양쪽 영향 확인)
- 회귀 비교: 20개 전부 통과, exit 0
- API 테스트: 35개 전부 통과, exit 0
- DELETE /api/compare: FastAPI 기본 405 Method Not Allowed 반환 (기존 404 표기 정정)
- test_api.py test_Cache_Control_no_store_전체_응답: DELETE /api/compare 405 허용 확인, no-store 헤더 확인

> 위 통과 기록은 공통 코어 통합을 시도했던 시점의 결과다. 이후 공통 코어 통합은 중단했고, `backend/doc_compare/core.py`와 `backend/tests/test_core.py`는 제거했으며, `compare_docs.py`와 `adapter.py`는 백업본으로 복구했다. 따라서 위 통과 결과는 현재 코드 상태의 통과 결과로 쓰지 않는다. 실제 복구 후 재실행 결과는 아래 "이번 변경 (공통 코어 통합 중단 + 백업 복구)"에 있다.

### 미검증/보류

- 문서 비교 엔진의 실제 사용자 검토: 미실행
- 대규모 문서에서의 성능: 미검증

---

## 이번 변경 (공통 코어 통합 중단 + 백업 복구)

### 상황

- 이전 턴까지 `backend/doc_compare/core.py`(신규)와 `backend/tests/test_core.py`(신규)를 추가하고, `compare_docs.py`/`adapter.py`가 같은 core 모듈을 import하도록 변경한 상태였다.
- API 테스트가 24개, 비교 테스트가 20개 실패한 상태로 기록된 작업 구간이 있었고, 이번 요청은 공통 코어 통합을 중단하고 정상 백업만 복구하는 것이었다.
- 핵심 역할을 서비스 코드로 옮기는 방향이면 되고, 원본 파일 호출/코드 공유 자체가 필수는 아니라고 정리했다.

### 작업 내용

- 현재 파일 4개를 새 증거 폴더 `docs/evidence/failed-core-integration-2026-09-15T200500`에 보관:
  - `backend/doc_compare/compare_docs.py`
  - `backend/doc_compare/adapter.py`
  - `backend/doc_compare/core.py`
  - `backend/tests/test_core.py`
- 보관본 SHA256 확인 완료:
  - compare_docs.py: `d7ea4580157a54ea25841df845b5111f7cc0c9b227fe43b354a81e702c4ab32c`
  - adapter.py: `6d9554d3fed5899ab790b03402d2cba1c3cc8a459e70dd435af5d88b8bcf575f`
  - core.py: `55691ab071d8223294177266168ee45de42d5162bc279d5266168ee45de42d5162bc27`
  - test_core.py: `64fb97a4b6d4b6ec7828db0bcf35f55fc09e089ab1bceb0a2b6d783617a70cc8`
- `docs/evidence/backup-2026-09-15T192041/compare_docs.py`와 `adapter.py` 두 개를 `backend/doc_compare/`의 같은 이름 파일로 복구:
  - 복구 후 compare_docs.py SHA256: `4d419e1c697c52daef4dac1f332a6b798216d724b54c029e68ac5cd9fdf855fd`
  - 복구 후 adapter.py SHA256: `fb2311c0d9fe5fe6780b7a22969bd193ffdc16a49a1e40947b1a82d81fc899c9`
- 기존 테스트/server/contracts는 그대로 유지. 백업 덮어쓰기/설치/설정/vendor/새 기능/커밋/push/자식 없음.
- 새 core.py와 test_core.py는 보관 확인 후 원래 실행/테스트 폴더에서 제거:
  - `backend/doc_compare/core.py` 제거
  - `backend/tests/test_core.py` 제거
- 이번 작업은 실패 실험 단계로 기록. 통과로 표시하지 않음.

### 결과

- 복구 후 실행:
  - API 테스트: `.venv/Scripts/python.exe -B -m backend.tests.test_api` → 35개 전부 통과, exit 0
  - 회귀 비교: `.venv/Scripts/python.exe -B backend/tests/test_compare.py` → 20개 전부 통과, exit 0

### 이전 통과 기록 정정

- 이전 PROGRESS에서 "doc-compare 개선 엔진 공통 코어화" 구간/검사 결과에 적힌 코어 검사 통과, 공통 코어 참조 통과 등은 이번 중단/복구 이전 상태의 기록이다.
- 이번 복구로 core.py, test_core.py는 backend 실행 경로에서 제거되었으므로, 해당 통과 기록은 더 이상 현재 코드 상태의 결과로 쓰지 않는다.
- 이전 턴까지 전부 통과라고 적힌 부분은 이번 중단/복구 이후 기준으로 정정했고, 이전 이력은 남겼다.

### 변경 파일 (이번 턴)

- `backend/doc_compare/compare_docs.py`: 백업본으로 복구
- `backend/doc_compare/adapter.py`: 백업본으로 복구
- `backend/doc_compare/core.py`: 제거 (보관 완료)
- `backend/tests/test_core.py`: 제거 (보관 완료)
- `docs/evidence/failed-core-integration-2026-09-15T200500/`: core 통합 중단 시점의 파일 4개 보관 폴더 (신규)
- `docs/evidence/local-compare.md`: 시도 실패/중단/복구 결과 반영, 이전 통과 표기 정정
- `docs/ops/PROGRESS.md`: 시도 실패/중단/복구 결과 반영, 이전 통과 표기 정정

### 실제 호출 경로 (복구 후)

- CLI 번호 기반 매칭: `python -B backend/doc_compare/compare_docs.py <구문서> <신문서>` → `compare_docs.parse_sections`(파일 파싱) → `compare_docs.match_numbered_items`(번호 기반 매칭 정책) → `compare_docs.build_report`(출력)
- API id/mapping 기반 매칭: `POST http://127.0.0.1:8009/api/compare` → `server.py.compare`(FastAPI 핸들러, 가드/한도/동일 일자리·기간 검증) → `adapter.compare_documents` → `adapter.compare_revision` → `adapter` 내부 분류 → `CompareResultData` 반환

### 이번 턴 미검증/보류/실패

- 공통 코어 통합: 중단 (실패 실험 단계로 기록, 통과로 표시하지 않음)
- 문서 비교 엔진의 실제 사용자 검토: 미실행
- 대규모 문서에서의 성능: 미검증
- 원본 대비 변경 설명: 이번 턴 대상 아님 (복구만 수행)
- SP4 실제 연결: 이후 작업 대상 (이번 턴 미실행)

### 이번 턴 결과 (2026-09-15, 공통 코어 통합 중단 + 백업 복구)

- API 테스트: 35개 전부 통과, exit 0
- 회귀 비교: 20개 전부 통과, exit 0
- 공통 코어 통합: 중단 (core.py, test_core.py 제거, 백업 compare_docs/adapter 복구)
- 변경 파일: `backend/doc_compare/compare_docs.py`, `backend/doc_compare/adapter.py`, `backend/doc_compare/core.py`(제거), `backend/tests/test_core.py`(제거), `docs/evidence/failed-core-integration-2026-09-15T200500/`(신규), `docs/evidence/local-compare.md`, `docs/ops/PROGRESS.md`

## 다음 작업

- 사용자가 지시할 때까지 시작하지 않음.

---

## 이번 변경 (frontend 빌드/행ID/매핑 오류 수정 — 2026-09-16)

### 변경 파일

- `frontend/src/actions.ts`: `createEmptyRow`가 `crypto.randomUUID()`로 id 생성. `applyRowPatch`, `addRowToList`, `removeRowFromList`, `addMapping`, `removeMappingsForRow`, `splitMappings` 추가. App과 테스트가 공용으로 사용.
- `frontend/src/api/compare.ts`: `import type { RowInput } from '../store/types'` 추가.
- `frontend/src/App.tsx`:
  - 자체 `uuid()` 제거, `crypto.randomUUID()` 직접 사용.
  - `setMapping`: 빈 `afterId`면 기존 짝 제거. 존재하는 `afterId`가 이미 다른 매핑에 쓰였으면 추가 거부(1:1만 허용).
  - `runCompare`: `splitMappings`로 유효한 매핑만 전송. 무효 매핑이 있으면 입력 유지 상태로 오류 표시(`setError`)하고 결과 화면으로 전환하지 않음(`return`).
  - `onBack`: 결과 화면 → 입력 화면(진행/입력 유지), 입력 화면/시작 화면 → 시작 화면.
- `frontend/src/example.test.ts`:
  - 불완전 입력 2건(소스Id 없음, 숫자 파싱)을 `createEmptyRow` + `applyRowPatch`로 id/필수 필드 갖춘 행으로 대체.
  - `itemFromInput`의 `row.id`/`position` 전달은 이미 정정되어 있어 유지.
  - 신규 검증 8건: 한글2항목 id 구분, 이름 수정 후 id 유지, 가운데 삭제 후 추가 중복 없음, 짝 해제/삭제/1:1 매핑, 잘못된 매핑 오류 보고 시 입력 유지, `splitMappings` 1:1 필터링.
  - 별도 구현 복사 없이 `actions.ts` 함수 사용.

### 실제 실행 명령/종료코드/결과

- 빌드: `cd frontend && npm run build` → exit 0. `tsc --noEmit && vite build` 통과, 36모듈 변환, dist 생성.
- 테스트: `cd frontend && npm test` → exit 0. vitest run, 11개 전부 통과.
- 재검사: 마지막 수정(`mappingFromPair` import 경로 `./api/compare`로 정정) 후 `npm test` → 11개 통과, exit 0. `npm run build` → exit 0.

### 미검증/보류

- 실제 HTTP 백엔드 연결: 미검증 (로컬 UI/모델 수준)
- 브라우저 렌더링/후기 응답/모름값/출처 왕복: 미검증 유지
- 백엔드/설치/설정/다른 소스/커밋/push/자식 작업: 범위 밖

### 다음 작업

- 사용자가 지시할 때까지 시작하지 않음.
- 현재 수정·검증 완료된 파일: `frontend/src/actions.ts`, `frontend/src/api/compare.ts`, `frontend/src/App.tsx`, `frontend/src/example.test.ts`.



## 2026-09-16 17:32 로컬 검수/최소 복구
- 사용자 직접수정 승인 범위에서 frontend/src/root.css의 모바일 전후 비교2열을1열로 보완. 다른제품소스 수정 없음. 기존작성본 보존.
- TypeScript검사와Vite빌드 통과. 실제Chrome390/1440 가로넘침없음/모바일1열·PC2열, 식대50000->70000 비교와80000수정후재비교200/pageerror0 확인.
- 별도OCR작업폴더 upload_api.py의import/오류응답을복구한뒤 합성PDF2장 DocumentParse+SolarPro4 실호출200, 항목수/금액/합계일치. 제품API에아직통합하지않음.
- 제품 .env의키가실행환경에준비됐다고보장하지않음. 업로드화면연결/공개배포/실질문복사 잔여. 커밋/push/배포 실행없음.
- Vercel 배포 준비(2026-09-16): `vercel login` 완료(click6067-ship-it / scope yos-projects-330f356b), `paychecker` 프로젝트 생성·연결, `.vercel/project.json` 생성.
- `vercel.json` routes: `/api/(.*)` → `/app.py`, `/assets/(.+)`, `/samples/(.+)`를 실제 정적 파일로 응답하도록 추가, 그 외는 기존처럼 `index.html`로 폴백.
- `.venv` Python으로 `app.py` import 및 `GET /api/health` 200 확인 완료 (별도 서버 구동 없음, `backend.server` 재사용).
- 프론트 수정·빌드·커밋·push·배포는 design 세션 종료 전 실행하지 않음. 현재 `frontend/dist` 산출물은 이미 존재(`.vercel/static` 포함 대상).
- 환경변수 입력 설정 URL: https://vercel.com/yos-projects-330f356b/paychecker/settings/environment-variables
