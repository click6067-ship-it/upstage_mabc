# doc-compare 회귀 테스트 증거

## 원본 보관 확인

- 원본 경로: `C:\Users\click\Desktop\doc-compare-extracted\compare_docs.py`, `SKILL.md`
- 보관 경로: `C:\Users\click\upstage_mabc\vendor\doc-compare-original\compare_docs.py`, `SKILL.md`
- 원본 수정 없음: 보관본 생성 후 원본 파일 읽기 재시도 결과 변경 없음
- compare_docs.py SHA-256: 원본 `9a1c4fbf5d86a37d814aaecba17faa24bcb8407a027bc7faa5d170cd7b2cc63a`, 보관본 `9a1c4fbf5d86a37d814aaecba17faa24bcb8407a027bc7faa5d170cd7b2cc63a` → 일치
- SKILL.md SHA-256: 원본 `5791458c0401b3e346264238ae3de36b0359a0a84c717a95630d893ec5d4c09f`, 보관본 `5791458c0401b3e346264238ae3de36b0359a0a84c717a95630d893ec5d4c09f` → 일치

## 원본 실제 동작 (반례 4종) 및 개선 결과

### 원본 실제 실행 (vendor, 원본 수정 없음)

- 원본 스크립트: `vendor/doc-compare-original/compare_docs.py`
- 아래 4종 반례를 원본 대상으로 이번 턴에 실제 실행한 결과(이전 턴의 "11개 전부 실패" 기록은 compare_docs.py 부재 시 실행 결과와 섞여 있었음):
  - a) 급여 이동(1↔2) + 지급일 문장 변경:
    - 원본 출력: 순서 변경 2건 + 본문 변경 1건(섹션 변경), "실제 변경 건수 (순서 변경 제외): 1건"
    - 원본 동작: 이동과 본문 변경을 둘 다 보고함 (정상)
  - c) 답변 기록 보관 7일 → 14일:
    - 원본 출력: "14일 이내 회신 의무 신설" 문구 포함, 실제 변경 1건
    - 원본 동작: "14일"만으로 회신 의무를 추정함 (문제)
  - d) 오전수당 이동(1→2) + 현장수당 삭제:
    - 원본 출력: 순서 변경 1건 + 삭제 1건(오전수당) + 변경 1건(현장→오전), "실제 변경 건수 (순서 변경 제외): 2건"
    - 원본 동작: 동일 신항목(오전수당)을 이동과 변경에 중복 매칭함 (문제)

### 원본의 실제 문제 3가지

1. 순서 변경 표기가 구→신으로 일관되지 않음
2. "14일"만으로 회신 의무를 추정함 (c 케이스)
3. 동일 신항목을 삭제와 변경에 중복 매칭함 (d 케이스)
- 원본은 이동 + 일반 문단 변경이 함께 있을 때 둘 다 보고하는 동작은 정상임

### 개선 결과 (backend)

- a) 이동+본문: 순서 변경 2건 + 본문 변경 1건, 실제 변경 1건 (원본과 동일)
- c) 회신: 변경 1건, 의무 추정 문구 없음 (개선)
- d) 중복: 순서 변경 1건 + 삭제 1건, 실제 변경 1건 (중복 제거, 개선)
- 변경(신청인 확인 → 신청인 확인 및 서명): 변경 1건만 (삼중 계산 제거, 개선)

## 최소 수정 내용

### backend/doc_compare/compare_docs.py

- match_numbered_items:
  - 추가/삭제/변경을 번호·텍스트 기준으로 판정하도록 수정
  - 공통 번호에서 구텍스트가 사라지고 신텍스트가 이동 도착이면 삭제로, 신텍스트가 원탕이면 변경으로 분류
  - 기존 added/deleted를 번호 집합 기준으로만 계산하던 방식에서, 텍스트 소멸 여부를 함께 반영해 중복 보고 방지
- compare_sections:
  - 본문 변경을 섹션 변경으로 올리는 조건을 원본처럼 복원 (순서 변경 있어도 본문 변경 보고)
- analyze_change_note:
  - "14일" 기반 회신 의무 추정 문구 완전 제거 (원문 차이만 표시)
- build_report:
  - 순서 변경 표기 방향을 구번호 → 신번호로 통일
  - 순서 변경 블록에 구/신 텍스트를 함께 출력해 원문 정보 유지

### backend/tests/test_compare.py

- parse_order_moves:
  - 실제 출력 형식("섹션명: 구번호항 → 신번호항 위치로 이동")에 맞는 정규식으로 수정
- 반례 4개 추가:
  - test_reply_obligation_must_not_be_inferred: 회신 의무 추정 금지
  - test_order_change_and_body_change_both_reported: 이동+본문 변경 동시 보고
  - test_ambiguous_case_preserves_original_info: 오전수당 이동+현장수당 삭제, 중복 매칭 방지
  - test_same_new_item_not_matched_to_both_move_and_change: 동일 신항목 중복 매칭 금지
- 기존 테스트 방향/분류 기대 수정:
  - test_order_change_not_counted_as_change: 구→신 방향 expectation
  - test_same_content_different_numbers_is_order_not_add_delete: 구→신 방향 expectation
- 구/신 번호와 변경 분류까지 검사하도록 보강

## 개선 후 테스트 결과

- 실행 명령: `python -B backend/tests/test_compare.py`
- 종료코드: 0
- 결과: 20개 전부 통과 (기존 13개 + 신규 7개)
  - 기존 13개: test_order_change_not_counted_as_change, test_same_content_different_numbers_is_order_not_add_delete, test_reply_obligation_must_not_be_inferred, test_order_change_and_body_change_both_reported, test_identical_documents_no_change, test_added_item, test_deleted_item, test_changed_item, test_amount_change_is_detected, test_similar_names_not_merged, test_same_amount_different_items_not_merged, test_ambiguous_case_preserves_original_info, test_same_new_item_not_matched_to_both_move_and_change
  - 신규 7개(순수 이동/이동+추가/항목변경+본문변경/이동만+본문 미검출/이동+신항목 삽입/항목변경+본문 미검출): test_move_only_same_item_different_number, test_move_and_add, test_item_change_and_body_change, test_pure_move_all_zero, test_move_only_items_not_detected_as_body_change, test_move_with_new_item_in_place, test_item_change_without_ignoring_body
- 미흡했던 3사례 반영:
  1. 구1 식대 → 신2 식대만 바뀌면 이동 1건, 항목 변경 0건, 본문 변경 0건 (순수 이동)
  2. 구1 식대 → 신1 교통비/신2 식대면 이동 1건 + 추가 1건(교통비), 삭제/변경 없음
  3. 식대 5만원→6만원과 일반 문단 지급일 10일→20일이 같이 바뀌면 항목 변경 1건 + 본문 변경 1건, 둘 다 보고
  4. 순수 이동(항목 이동만) 시 항목/섹션/전체 실질 변경 모두 0건 확인: test_pure_move_all_zero 통과
- 테스트 실행 환경: Python 표준 라이브러리만 사용, tempfile/subprocess로 통일, 셸 임시파일/head/tail 없음

## 파일 해시 (이번 턴 기준)

- backend/doc_compare/compare_docs.py: `3e854f00faf59097009a57105abeeed2ad0340704c0e872935e2875b8608c169`
- backend/tests/test_compare.py: `a31de475b4c7f920c1d3d03c292b152bbfafc86e6b5b63781914ed960c7a96d0`
- vendor/doc-compare-original/compare_docs.py: `9a1c4fbf5d86a37d814aaecba17faa24bcb8407a027bc7faa5d170cd7b2cc63a`
- vendor/doc-compare-original/SKILL.md: `5791458c0401b3e346264238ae3de36b0359a0a84c717a95630d893ec5d4c09f`
- 원본 compare_docs.py: `9a1c4fbf5d86a37d814aaecba17faa24bcb8407a027bc7faa5d170cd7b2cc63a`
- 원본 SKILL.md: `5791458c0401b3e346264238ae3de36b0359a0a84c717a95630d893ec5d4c09f`

## 미완료 항목

- T03 원문 보관/텍스트 해시/중복 지급 계약: 미완료 유지

## 관련 파일

- `backend/doc_compare/compare_docs.py`
- `backend/tests/test_compare.py`
- `vendor/doc-compare-original/compare_docs.py`
- `vendor/doc-compare-original/SKILL.md`
- `docs/evidence/doc-compare-regression.md`
- `docs/ops/PROGRESS.md`
