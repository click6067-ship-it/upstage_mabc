# INDEX.md — 문서·합성 검산 증거

## 개요

이 디렉터리는 `docs/specs/DOMAIN.md`와 `tests/fixtures/wage-cases.json`에 정의된 계산·기록 규칙을 **문서·합성 수준에서 검산한 결과**를 기록한다.

## 범위 구분

- **문서·합성 검산**: 이 디렉터리의 내용. JSON 파싱, 규칙 대조, 산술 명령 실행으로 기대값과 대조.
- **앱 테스트 미실행**: 앱 코드 실행·설치·설정·화면 테스트는 이 단계에서 **실행하지 않음**. 둘은 구분해서 기록한다.

## 입력 및 검산 파일

- `tests/fixtures/wage-cases.json`
- `tests/verify_wage_cases.py`
- SHA-256 (wage-cases.json): `470ed5acb90fb174bedd9c51e95a907bc3ce229bfa06ee9868fa31eb20acdf34`
- SHA-256 (verify_wage_cases.py): `95f02a19bae17f429ab732141b85d92d53fbb4f0f0461eac5fad1f4295e58d16`

## 실행 명령

- 계수상정: `python -B tests/verify_wage_cases.py`
- 음수 테스트: `python -B tests/verify_wage_cases.py --negative-test`
- C3 수령액 오버라이드: `python -B tests/verify_wage_cases.py --c3-override`
- 빈 목록: `python -B tests/verify_wage_cases.py --empty-list`
- F 누락: `python -B tests/verify_wage_cases.py --missing-f`
- A 중복: `python -B tests/verify_wage_cases.py --dup-a`
- B expected 축소: `python -B tests/verify_wage_cases.py --short-b-expected`
- B expected 변조: `python -B tests/verify_wage_cases.py --mutate-b-expected`
- 환경: 표준 라이브러리만 사용. 외부 패키지 설치 없음. `-B`로 바이트코드 캐시 작성 안 함.

## 실제 종료코드

- 정상 실행: exit 0 (A, B, C1~C4, D, E, F 전부 OK)
- --negative-test: exit 1 (F 기대 rounded_won 166 → 실제 167로 불일치)
- --c3-override: exit 1 (C3 실제 수령 120001 → 기대 120000과 불일치)
- --empty-list: exit 1 (STRUCTURE: cases is empty)
- --missing-f: exit 1 (STRUCTURE: missing case id: F)
- --dup-a: exit 1 (STRUCTURE: duplicate case id: A)
- --short-b-expected: exit 1 (B expected stages count should be 5, got 4)
- --mutate-b-expected: exit 1 (B corrected_statement_minus_actual: got 11111, expected 72000)
- 총 8개 종료코드: 정상 1개(exit 0) + 비정상 7개(exit 1)

## 이번 검산 실행 기록

- 실행 명령: `python -B tests/verify_wage_cases.py`
- 실행 시점 결과: exit 0 (A~F 전부 OK)
- fixture_sha256: `470ed5acb90fb174bedd9c51e95a907bc3ce229bfa06ee9868fa31eb20acdf34`
- script_sha256: `95f02a19bae17f429ab732141b85d92d53fbb4f0f0461eac5fad1f4295e58d16`
- 비고: 이번 실행은 DOMAIN.md 수정(9절 의문 상태 전이 표, 19절 용어, 25.4 저장 시점 규칙, 26절 입력 경계 추가) 후 재확인 목적. 앱 테스트 통과와는 별개. 정산 스크립트·JSON은 변경 없음.

## 실제 결과

- 정상 실행 결과는 모든 사례가 input 기반 계산값과 expected를 통과.
- B: 수정본 적용 여부와 산술별 확인/보류를 입력에서 계산한 값으로 검사. 단계별 `(지급 차이, 기본급 참고 산술 차이)` = `(20000,null), (0,null), (0,96000), (0,72000), (72000,0)`.
- B1/B2: 지급 차이는 각각 20000원, 0원으로 계산 가능, 기본급 참고 산술은 둘 다 null(보류).
- C1/C4: null 수령과 확인된 0원 수령을 별도 사례로 구분.
- C2: 내부 합계 검증 보류 상태만 boolean으로 확인, 숫자 답은 fixed value로 넣지 않음.
- C3: 지급 차이 -20000만 대조하고, "왜 더 받았는지" 같은 판단은 넣지 않음.
- D: 1분×10,001원 3개 → 500원 (반례: 개별 환산 후 합산 501원과 다름).
- E: 1분×10,050원 1개 → 168원.
- F: 1분×9,990원 1개 → 167원 (반례: Python round(166.5)=166과 다름).
- B는 시급을 시간당 원(12,000)으로 유지하고, 명세서 기본급은 `(minutes * hourly_rate_per_hour + 30) // 60`으로 계산.

## 판정

- 검산은 사례별로 별도로 대조한다.
- "여러 사례가 통과했으므로 전체 규칙이 증명됐다" 같은 표기는 하지 않는다.
- 기대값을 메모리에서만 바꾼 실패 케이스(--negative-test, --c3-override)도 함께 기록한다.
- 원본 JSON은 변조하지 않고, 검산 시점의 해시만 남긴다.

## 미검증 항목

- doc-compare 실제 실행: 미실행
- 앱 코드 실행·설치·설정·화면 테스트: 미실행
- 실제 사용자 검토: 미실행
- 번역 검토: 미실행
- 정정 버전 저장/비교 범위 확인: 미실행
- 늦은 OCR/AI 응답 처리 방식 검증: 미실행
- 내려받은 PDF 구버전 표시·새 파일 생성 규칙 검증: 미실행
- T02 전체 완료 표시: 아직 하지 않음

## 관련 문서

- `docs/specs/DOMAIN.md` — 영역 규칙·분리 항목·흐름·미확인/확인됨 구분
- `tests/fixtures/wage-cases.json` — 합성 사례
- `docs/ops/PROGRESS.md` — 진행 이력
