# DATA-MODEL.md — 임금·명세서 대조를 위한 데이터 구조 설계

> 범위: 이번 작업은 데이터 구조 설계만. 코드/설치/기존 파일 수정/커밋은 하지 않는다.  
> 저장 모드: 사용자 기기 IndexedDB + 이번 세션 메모리 모드. 서버 계정·영구DB·자동 동기화는 포함하지 않는다.  
> 근거: `AGENTS.md`, `PRD.md`, `docs/specs/DOMAIN.md` (이 세 파일만 읽고 작성).

---

## 1. 설계 원칙 (데이터에 그대로 반영)

1. **돈은 정수 원, 시간은 정수 분.** 중간 곱·합도 정수 범위를 확인한다.
2. **미확인(null)과 확인된 0은 다른 상태.** 0으로 채우지 않는다.
3. **원문 / 추출 후보 / 사용자 확인값은 별도 필드·별도 객체.** 새 업로드가 기존 확인값을 자동 교체하지 않는다.
4. **값·확인 상태·출처를 항상 함께 남긴다.** 출처 없이는 확인값을 믿지 않는다.
5. **한 지급의 배분 합은 입금액 이하.** 초과 배분은 적용 불가로 본다. 미배분은 월별 합산에서 제외한다.
6. **같은 급여기간의 active 미수령 확인과 confirmed 배분만 공존을 금지한다.** 실제 지급 기록과 다른 기간의 배분은 허용한다. 월별 수령 합계는 금액/수령 방식이 확인된 지급의 해당 기간 confirmed 배분만 합산한다. 미수령/0원 수령 확인과 미배분 금액은 월 합계에 넣지 않는다.
7. **일부 지급 확인을 전체 수령 확인으로 바꾸지 않는다.**
8. **전월/당월 수정본은 구분한다.** 새 업로드로 기존 명세서를 자동 교체하지 않는다.
9. **근거 정정이 어떤 계산·설명·출력 버전을 오래된 것으로 만드는지 관계로 연결**한다.
10. **정정 전 원문·이력은 보존한다.** 확인값 변경과 새 결과 버전 저장은 함께 성공해야 한다.

---

## 2. 공통 필드 (모든 객체)

Workspace 이외의 독립 저장 객체는 아래 공통 필드를 가진다. Workspace 자체의 필드는 2.5에 정의한다.

| 필드 | 타입 | 설명 |
|---|---|---|
| id | 문자열(UUID) | 해당 객체의 고유 ID. Workspace의 ID와는 별개다. |
| workspaceId | 문자열 | 이 객체가 속한 Workspace.id를 참조한다. |
| revision | 정수(1 이상) | 확인값 변경/정정 등 의미 있는 변경마다 증가한다. |
| createdAt | 날짜시간(ISO 8601, 오프셋 포함) | 최초 생성 시각. |
| updatedAt | 날짜시간(ISO 8601, 오프셋 포함) | 최종 수정 시각. |

공통 규칙은 아래처럼 적용한다.

- id는 생성 시 부여하고 유지한다. 단순 보기/편집 취소로 revision을 올리지 않는다.
- 객체의 workspaceId는 소속 참조다. 활성 Workspace를 바꿔도 기존 객체의 소속을 변경하지 않는다.
- 생성/수정할 객체와 그 참조 대상은 같은 Workspace에 속해야 한다. 다른 Workspace끼리 연결하지 않는다.
- 생성/수정 시각은 클라이언트 시계 기준이다. 시계 오차 상세 정책은 다음 저장 설계에서 다룬다.

## 2.5 Workspace (작업 공간)

내 기기 저장에서 기록을 묶는 단위. 세션이 바뀌어도 같은 Workspace를 다시 열어 기존 기록을 이어서 본다. Workspace는 별도 객체이며, 아래 객체들의 `workspaceId`를 관리한다.

### 2.5.1 객체 표

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| id | 문자열(UUID) | 예 | Workspace 자체의 고유 ID. 재접속해도 유지한다. |
| mode | 문자열 | 예 | persistent 또는 temporary. |
| revision | 정수(1 이상) | 예 | Workspace 설정의 의미 있는 변경 버전. |
| createdAt | 날짜시간 | 예 | 최초 생성 시각. |
| updatedAt | 날짜시간 | 예 | 최종 수정 시각. |

### 2.5.2 활성 선택과 저장모드

- Workspace 객체 안에는 activeWorkspaceId 필드를 두지 않는다.
- 저장 설정의 activeWorkspaceId는 현재 선택된 Workspace.id를 참조한다. 이는 설정 포인터이지 별도의 Workspace ID가 아니다.
- persistent: Workspace와 활성 포인터를 IndexedDB에 저장한다. 재접속하면 포인터로 기존 Workspace를 찾아 기록을 이어서 연다.
- temporary: Workspace/활성 포인터/기록은 메모리에만 둔다. 새로고침/종료 시 사라지며 저장됐다고 표시하지 않는다.
- 저장된 Workspace가 없는 첫 진입에서만 새 ID를 만든다. 기존 기록을 새 ID로 덮어쓰거나 다른 Workspace로 옮기지 않는다.
- 각 객체의 workspaceId는 소속 Workspace.id를 가리킨다. 다른 Workspace의 객체와 교차 참조하지 않는다.
- 모드 전환/삭제/복원과 저장 실패 상세 절차는 다음 작업에서 다룬다.


---

## 3. 객체 표와 필드 타입

### 3.1 일자리 (Job)

한 사용자의 한 일자리 기준 기록을 묶는 최상위 단위. 여러 급여기간이 하나의 일자리에 연결된다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | 위 공통 필드 |
| `workspaceId` | 문자열 | 예 | 소속 Workspace.id 참조. |
| `revision` | 정수 | 예 | 위 공통 필드 |
| `createdAt` | 날짜시간 | 예 | 위 공통 필드 |
| `updatedAt` | 날짜시간 | 예 | 위 공통 필드 |
| `name` | 문자열 또는 null | 예 | 일자리 표시명. 미확인이면 null. 빈 문자열과 null을 구분한다. |
| `employerName` | 문자열 또는 null | 예 | 사용자 확인 사업장명. 미확인이면 null. |
| `employerNote` | 문자열 또는 null | 예 | 사업장 관련 메모·확인 필요 사항. |
| `contactNote` | 문자열 또는 null | 예 | 문의에 쓸 연락처·사항 메모(사용자 확인 전 초안 가능). |
| `currency` | 문자열 | 예 | 기본 화폐 단위. 이번 작업은 `"KRW"` 고정. 외화 입력은 별도 필드로 남긴다(3.11 참고). |
| `language` | 문자열 | 예 | 사용자 선택 언어. `"ko" | "en" | "vi" | "ne" | "km"` 중 하나. |

- `name`, `employerName`은 **사용자 확인값**이다. 미확인이면 null. "모름"을 빈 문자열로 두지 않는다.

### 3.2 급여기간 (PayPeriod)

급여 계산·비교의 기준 기간. 시작·종료, 입금일을 분리한다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `jobId` | 문자열(외래) | 예 | 연결된 일자리 id. |
| `label` | 문자열 또는 null | 예 | 사용자 표시용 기간명(예: "2024년 3월"). 미확인이면 null. |
| `periodStart` | 날짜 또는 null | 예 | 급여기간 시작일. 미확인이면 null. |
| `periodEnd` | 날짜 또는 null | 예 | 급여기간 종료일. 미확인이면 null. |
| `depositDateExpected` | 날짜 또는 null | 예 | 예정 입금일. 실제 확인 전 상태. |
| `depositDateActual` | 날짜 또는 null | 예 | 실제 입금 확인일. 예정과 구분한다. |
| `receiptStatus` | 문자열(열거) | 예 | 해당 급여기간의 수령 확인 상태. 아래 표 참고. |
| `status` | 문자열(열거) | 예 | 기간 처리 상태. 아래 표 참고. |

`receiptStatus` 값:

| 값 | 의미 |
|---|---|
| `unknown` | 수령 여부 자체를 아직 모름 |
| `partial` | 일부만 확인됨. 전체 수령으로 보지 않음 |
| `complete` | 사용자가 등록 여부와 관계없이 해당 급여기간의 수령 내역을 빠짐없이 확인했다고 명시함. 등록된 지급만 확인한 상태와 구분하며, 명세서 금액을 전부 받았다는 뜻은 아님. |

`status` 값:

| 값 | 의미 |
|---|---|
| `draft` | 입력 중, 확정 전 |
| `ready` | 기간 확정, 비교·계산 준비 가능 |
| `comparing` | 대조·비교 진행 중 |
| `closed` | 사용자가 이유와 함께 종결 |

- `periodStart`·`periodEnd`는 **사용자 확인값**이다. 미확인이면 null. 이 경우 월별 비교·전월 대비는 보류한다(3.2.1 참고).
- `periodStart`·`periodEnd`가 null이면 급여기간 시작·끝을 모르므로, 지급 귀속 확정과 전월/당월 비교는 보류한다.
- `depositDateActual`은 실제 입금 확인 후에만 채운다. null이면 아직 실제 입금 확인 없음.
- 일부 입금이나 등록된 지급만 확인했다고 `receiptStatus = "complete"`로 바꾸지 않는다. 사용자가 등록하지 않은 다른 지급까지 포함해 해당 급여기간의 수령 내역을 빠짐없이 확인했다고 명시해야 complete다. 확인된 수령액과 명세서 금액의 차이는 별도로 남긴다.

#### 3.2.1 기간 미확인 임시 저장

- `periodStart`·`periodEnd` null이어도 입금·기록은 임시 저장 가능하다.
- 단, 전월/당월 비교열에는 넣지 않는다. 월별 비교는 **보류**로 표시한다.
- 기간이 나중에 확인되면 그때 비교 대상에 포함한다.
- 기간 미확인 상태에서는 **지급의 월 귀속도 확정하지 않는다.** 귀속은 `PaymentAllocation-payPeriodId`로만 판단하며, 급여기간이 확인되기 전에는 귀속을 단정하지 않는다.

### 3.3 원문 (SourceDocument)

사용자가 올린 파일·원문 자체. OCR 결과·추출 후보와 분리한다. 사진·PDF는 원본 blob을 참조하고, 텍스트는 원문 문자열을 그대로 저장한다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `payPeriodId` | 문자열(외래) 또는 null | 예 | 연결된 급여기간. 기간 미확인이면 null(임시 저장). |
| `jobId` | 문자열(외래) | 예 | 일자리. |
| `sourceType` | 문자열(열거) | 예 | `"photo" | "pdf" | "text" | "other"` |
| `fileName` | 문자열 또는 null | 예 | 사용자 기기 기준 파일명(노출 제어 대상, 아래 참고). |
| `sourceValue` | 문자열 또는 null | 예 | **텍스트 원문.** sourceType이 `"text"`일 때 원문 전체. `photo`/`pdf`/`other`에서는 null. **노출 제어 대상(아래 8장 참고).** |
| `originalBlobRef` | 문자열 또는 null | 예 | **사진·PDF 원본을 찾는 저장 키.** sourceType이 `"photo"` 또는 `"pdf"`일 때 필수. blob 자체가 아니라 원본을 찾을 수 있는 키이며, 화면용 object URL(URL.createObjectURL 등)이 아니다. persistent 모드에서는 같은 Workspace의 IndexedDB에 저장된 원본을 이 키로 다시 연다(재방문 시 같은 원본 열기). temporary 모드에서는 메모리 원본만 이 키로 참조하며, 새로고침/종료 후 원본을 못 찾으면 누락으로 표시하고 다른 파일로 대체하지 않는다. `text`/`other`에서는 null. |
| `sha256` | 문자열 또는 null | 예 | **원문 SHA-256.** `photo`/`pdf`일 때 원본 파일 전체 해시로 필수. `text`일 때 이 필드는 원문 해시를 담지 않는다(필요 시 sourceValue 해시는 별도 계산·별도 관리). `other`은 선택. |
| `mimeType` | 문자열 또는 null | 예 | **MIME 타입.** `photo`/`pdf`일 때 필수(예: `"image/jpeg"`, `"image/png"`, `"application/pdf"`). `text`/`other`은 null. |
| `byteSize` | 정수 또는 null | 예 | **원문 바이트 크기.** `photo`/`pdf`일 때 원본 파일 크기로 필수. `text`/`other`은 null. |
| `thumbnailNote` | 문자열 또는 null | 예 | 썸네일·미리보기 관련 메모(값 자체 아님). |
| `confidence` | 객체 또는 null | 예 | 업로드·OCR 호출 수준 confidence. 확인값과 별개. |
| `status` | 문자열(열거) | 예 | `"uploaded" | "processing" | "extracted" | "confirmed" | "superseded"` |
| `supersedesId` | 문자열 또는 null | 예 | 사용자가 직접 지정한 이전 원문 id(정확한 교체 의도가 있을 때만). 자동 교체 아님. |
| `languageHint` | 문자열 또는 null | 예 | 원문 언어 추정. `"ko" | "en" | "vi" | "ne" | "km" | null` |

**타입별 원문 보관 방식:**

- **`photo` / `pdf`**: 원본 파일은 별도 blob으로 저장하고 `originalBlobRef`로 원본을 찾는다. `originalBlobRef`는 blob 자체가 아니라 저장 키이며, 화면용 object URL을 영구 저장 키로 쓰지 않는다. `sourceValue`는 null. `sha256`는 원본 파일 전체 해시, `mimeType`과 `byteSize`는 원본 메타데이터. OCR 결과·추출 후보·전송용 가공본은 이 필드를 덮어쓰지 않는다(3.3.4 참고).
- **`text`**: 사용자가 직접 입력한 텍스트가 원문. `sourceValue`에 원문 전체를 저장하고, `originalBlobRef`·`mimeType`·`byteSize`는 null이다. photo/PDF와 달리 별도 파일 blob이 없으며, 가짜 저장 키·가짜 파일을 만들지 않는다.
- **`other`**: 위 두 방식에 해당하지 않는 원문. **파일형** 또는 **텍스트형** 중 하나로 저장한다.
  - 파일형으로 저장하면 `originalBlobRef`(저장 키) + `sha256` + `mimeType` + `byteSize`로 관리하고, `sourceValue`는 null.
  - 텍스트형으로 저장하면 `sourceValue`에 원문 전체를 저장하고, `originalBlobRef`·`mimeType`·`byteSize`는 null.
  - 세부 방식은 구현에서 정하되, 어느 방식이든 **가짜 파일·가짜 저장 키·가짜 MIME·가짜 바이트 크기를 만들지 않는다.**
  - 텍스트형 원문의 해시는 **원문 UTF-8 바이트 기준** SHA-256 등 별도 계산으로 관리하며, 이 앱 설계의 `SourceDocument.sha256` 필드(photo/pdf용 원본 파일 해시)와는 분리한다.

- `sourceValue`(text) 또는 `originalBlobRef`(photo/pdf)는 **원문**으로 보존한다. 추출 후보·확인값과 분리한다.
- 새 파일 업로드가 기존 원문의 `originalBlobRef`·`sha256`·`mimeType`·`byteSize`·`sourceValue`를 자동 교체하지 않는다. 동일 기간 원문이 여러 개일 수 있다(버전 관리). `supersedesId`는 사용자가 명시적으로 지정한 경우만 연결한다.
- `status = "superseded"`는 원문 자체가 오래된 버전으로 표시된다는 뜻이며, 데이터는 삭제하지 않는다.
- OCR 결과나 전송용 가공본은 **원문 원본·해시를 덮지 않는다.** OCR 결과는 `ExtractionCandidate`로, 전송용 가공본은 필요 시 별도 객체로 관리한다.

#### 3.3.1 노출 제어 대상과 허용 열람 구분

- 원문·원본 메타데이터 중 **로그·콘솔·자동 생성된 요약 텍스트에 그대로 쓰면 안 되는 것**과 **사용자가 직접 열어보는 원문 화면에서 허용해도 되는 것**을 구분한다.
- 아래 항목은 로그·콘솔·자동 요약에 원문 전체 또는 내부 저장 경로를 그대로 노출하지 않는다.
  - `fileName`
  - `sourceValue`(텍스트 원문 전체)
  - `originalBlobRef`(사진·PDF blob 참조 경로)
  - `sha256`, `mimeType`, `byteSize`의 원문 식별 조합
- 사용자가 직접 열어보는 **원문 열람 화면**에서는 photo/PDF/텍스트 원문 전체 열람과 원본 다운로드를 허용한다. 이 화면은 로그·콘솔·자동 요약이 아니며, 사용자가 등록한 원문을 보기 위한 화면이다.
- 이번 데이터 모델상 **존재와 메타 정보는 남기되**, 원문 전체·blob 경로는 로그·콘솔·자동 요약에 그대로 노출하지 않고, 열람 화면에서만 보인다. 상세 절차는 다음 작업(백업 암호화/삭제/멀티탭)으로 미룬다.

#### 3.3.2 photo/pdf 필수·null 조건

- `sourceType`이 `"photo"` 또는 `"pdf"`일 때:
  - `originalBlobRef` **필수**, null 금지.
  - `sha256` **필수**, null 금지(원본 파일 전체 SHA-256).
  - `mimeType` **필수**, null 금지. 허용 예: `"image/jpeg"`, `"image/png"`, `"image/heic"`, `"application/pdf"`.
  - `byteSize` **필수**, null 금지(원본 파일 바이트 크기, 1 이상).
  - `sourceValue` **null**, 텍스트 원문 없음.
  - 썸네일·추출 후보·OCR 결과는 blob과 분리해 저장하며 원본 해시·바이트 크기·이 MIME을 변경하지 않는다.

#### 3.3.3 text 필수·null 조건

- `sourceType`이 `"text"`일 때:
  - `sourceValue` **필수**, null 금지(원문 전체 텍스트).
  - `originalBlobRef` **null**, `mimeType` **null**, `byteSize` **null**. 별도 파일 blob 없음. 가짜 파일을 만들지 않는다.
  - `sha256` **null**로 둔다. 텍스트 원문의 별도 해시가 필요하면 `sourceValue` 해시를 별도 필드로 관리한다(이번 모델에서는 `SourceDocument`에 넣지 않는다).

#### 3.3.4 사진 등록 후 OCR 재실행 케이스

1. 사용자가 photo 원문을 업로드한다.
   - `SourceDocument` 생성: `sourceType = "photo"`, `originalBlobRef`, `sha256`, `mimeType`, `byteSize` 채운 뒤 저장. `status = "uploaded"`.
2. OCR을 재실행한다.
   - OCR 결과는 **새 `ExtractionCandidate` 객체로만** 기록한다. 동일 사진의 `originalBlobRef`, `sha256`, `byteSize`, `mimeType`을 갱신하지 않는다.
   - OCR 호출 timestamp/설정은 `confidence` 객체나 별도 메모로 남길 수 있으나 원문 원본 필드와 섞지 않는다.
3. 원문 등록·해시 기준은 변함없다.
   - 사진 원문의 정체성은 blob 해시·바이트 크기·이 MIME으로 판단한다. OCR 재실행으로 원문이 달라지지 않았으므로 동일 문서로 본다.
   - 재업로드 경고(동일 blob 해시 감지)는 아래 3.3.5 규칙으로 처리한다.

#### 3.3.5 같은 PDF 재업로드 케이스

1. 이미 등록된 PDF와 **blob 해시(sha256)가 동일한** 새 PDF를 업로드한다.
   - 동일 원문으로 판단되면 **재업로드 경고를 표시**한다. 기존 원문을 자동 삭제·교체하지 않는다.
   - 새 업로드가 **동일 입금(동일 지급)이라고 단정하지 않는다.** 원문이 같다고 지급까지 같다고 보지 않는다. 지급 식별(입금일·금액·채널·사용자 확인)은 별도 객체/확인으로 판단한다.
   - 사용자가 명확히 다른 문서라고 확인하면 새 `SourceDocument`로 별도 저장한다. 동일 기간 내 여러 원문 허용.
2. 해시가 다르지만 유사해 보이는 경우:
   - 자동 중복 판정하지 않는다. 재업로드 경고는 해시 일치 기준으로만 표시한다.
   - 지급 중복 의심은 7장 검증 규칙(14)의 조합으로 별도 표시하며, 원문 단계에서 자동 합산하지 않는다.

#### 3.3.6 텍스트만 입력하는 케이스

1. 사용자가 텍스트 원문을 직접 입력한다.
   - `SourceDocument` 생성: `sourceType = "text"`, `sourceValue`에 원문 전체 저장, `originalBlobRef`/`mimeType`/`byteSize`/`sha256` **null**.
   - 사진/PDF 전용 필드(blob 참조, 해시, MIME, 바이트 크기)는 텍스트 원문 저장에 사용하지 않는다. 가짜 파일을 만들지 않는다.
2. 텍스트 원문도 원문이므로 추출 후보·확인값과 분리한다.
   - `sourceValue`는 텍스트 원문 그 자체이며, 추출 후보는 `ExtractionCandidate`로, 사용자 확인값은 `ConfirmedValue`로 따로 저장한다.

#### 3.3.7 타입별 필수/선택 요약

| sourceType | sourceValue | originalBlobRef | sha256 | mimeType | byteSize | 비고 |
|---|---|---|---|---|---|---|
| photo | null | 필수 | 필수 | 필수 | 필수 | 원본 저장 키 참조, OCR은 후보 객체로만 |
| pdf | null | 필수 | 필수 | 필수 | 필수 | 원본 저장 키 참조, 원본 수정 불가 |
| text | 필수 | null | null | null | null | 직접 입력 텍스트, 가짜 파일·가짜 저장 키 없음 |
| other | 선택 | 선택 | 선택 | 선택 | 선택 | 둘 중 해당 방식으로 저장, 나머지는 null |

- photo/pdf는 `sha256`, `mimeType`, `byteSize`로 원문을 식별한다. text는 `sourceValue`로 원문을 식별한다.
- photo/pdf의 `sha256`는 **원문 원본 파일 해시**이며, OCR 결과·가공본·추출 후보 해시가 아니다.

#### 3.3.8 문서 검산 (이번 변경 기준)

아래 3개 사례로 3.3 규칙(원본 blob을 원본을 찾는 저장 키로 관리, SHA256/MIME/바이트 크기, 텍스트 원문 구분, 자동 교체 금지, 재업로드 경고 but 지급 단정 금지, 임시 모드 메모리만, 로그·콘솔·자동 요약 노출 금지, 원문 못 찾으면 누락 표시·다른 파일로 대체 금지, 재방문 시 같은 원본 열기, temporary 새로고침 후 원본 없음)이 개별 사례와 충돌하지 않는지 확인한다. **기존 수령 규칙(3.12, 3.13, 7장 검증 규칙)은 그대로 유지한다.**

##### 3.3.8.1 사례 1 — 사진 등록 후 OCR 재실행

입력:
- photo 원본 업로드. `sha256 = H1`, `mimeType = "image/jpeg"`, `byteSize = 245,760`, `originalBlobRef = "idb:ws-1/photo/abc-123"`. `sourceValue = null`.
- 이후 같은 사진에 대해 OCR 재실행.

기대 결과:
- `SourceDocument`는 그대로. `originalBlobRef`, `sha256`, `mimeType`, `byteSize` 갱신 없음.
- OCR 결과는 새 `ExtractionCandidate`로만 추가. 원문 원본·해시가 바뀌지 않음.
- 동일 사진임이 blob 해시로 식별되므로, 재업로드 경고 표시 대상이 될 수 있다(선택적 표시). 다만 사진 재업로드가 곧 동일 지급이라는 뜻은 아님.
- `originalBlobRef`는 화면용 object URL이 아니라 저장 키이며, 화면용 object URL은 열람할 때만 만들고 영구 저장 키로 쓰지 않음.
- persistent 모드에서는 `originalBlobRef`로 IndexedDB의 동일 Workspace 원본을 다시 열어 같은 원본을 다시 볼 수 있음(재방문 시 같은 원본 열기).
- blob 경로·원문 전체·해시는 로그·콘솔·자동 요약에 그대로 노출하지 않음. 사용자가 직접 열어보는 원문 화면에서는 blob 원본 다운로드와 사진 전체 열람을 허용한다.

판정:
- 통과. OCR 재실행이 원본 blob·해시·MIME·바이트 크기를 덮지 않으며, OCR은 추출 후보로 분리됨.

##### 3.3.8.2 사례 2 — 같은 PDF 재업로드

입력:
- PDF 원문 1개 등록: `sha256 = X`, `mimeType = "application/pdf"`, `byteSize = 912,000`, `originalBlobRef = "idb:ws-1/pdf/def-456"`.
- 나중에 동일 파일(동일 해시 X)을 다시 업로드.

기대 결과:
- 동일 blob 해시 감지 → **재업로드 경고** 표시.
- 기존 원문을 자동 삭제·교체하지 않음. 새 `SourceDocument`를 자동으로 만들지 않음(또는 만들더라도 기존 원문을 덮지 않음).
- 원문이 같다고 **동일 지급이라고 단정하지 않음.** 지급 식별은 입금일·금액·채널·사용자 확인으로 판단한다.
- 사용자가 "다른 문서"라고 확인하면 새 `SourceDocument`로 별도 저장 가능. 동일 기간 내 여러 원문 허용.
- hash가 다른 유사 PDF는 자동 중복 판정하지 않음. 재업로드 경고는 해시 일치 기준으로만 표시.
- `originalBlobRef`는 저장 키이며, 화면용 object URL은 열람할 때만 만들고 영구 저장 키로 쓰지 않음.
- persistent 모드에서는 기존 PDF 원본을 `originalBlobRef`로 다시 열어 재방문해도 같은 원본을 볼 수 있음.
- blob 경로·hash·MIME·byteSize의 원문 식별 조합은 로그·콘솔·자동 요약에 그대로 노출하지 않음. 사용자가 직접 열어보는 원문 화면에서는 blob 원본 다운로드와 PDF 전체 열람을 허용한다.

판정:
- 통과. 재업로드 경고 ≠ 지급 단정, 원본 교체 금지, 기존 수령 규칙(3.12/3.13)과 충돌 없음. 새 PDF가 실제 지급 증빙이면 `ActualPayment.sourceDocumentId`로 연결하되, 원문 단계에서 자동 합산하지 않음.

##### 3.3.8.3 사례 3 — 텍스트만 입력

입력:
- 사용자가 원문 텍스트를 직접 입력. `sourceValue = "…원문 전체…"`.

기대 결과:
- `SourceDocument` 생성: `sourceType = "text"`, `sourceValue` 채움, `originalBlobRef`·`mimeType`·`byteSize`·`sha256` **null**.
- 가짜 파일/가짜 blob/저장 키/hash/MIME/byteSize를 만들지 않음.
- 텍스트 원문도 추출 후보·확인값과 분리. 추출은 `ExtractionCandidate`, 확인은 `ConfirmedValue`.
- `sourceValue`(원문 전체)는 로그·콘솔·자동 요약에 그대로 노출하지 않음. 사용자가 직접 열어보는 원문 화면에서는 텍스트 원문 전체 열람을 허용한다.

판정:
- 통과. text 타입은 blob 기반 필드 없이 `sourceValue`만으로 원문 저장하며, photo/pdf 필드와 섞이지 않음.

##### 3.3.8.4 규칙 충돌 없음 확인

- 원본 보관 방식과 수령 규칙(3.12/3.13)은 분리: 원문 정체성(hash/MIME/byteSize/sourceValue)은 원문 단계에서만 쓰이고, 지급·배분·미수령 확인은 별도 객체로 판단한다. photo/pdf의 원본은 `originalBlobRef`(저장 키)로 찾고, `sha256`/`mimeType`/`byteSize`는 그 원본을 식별하는 메타데이터다.
- `originalBlobRef`는 object URL이 아니라 저장 키이며, 화면용 object URL은 열람할 때만 만들고 영구 저장 키로 쓰지 않는다.
- 동일 blob 해시는 "동일 문서" 후보일 뿐, "동일 지급"은 아님. 이 구분을 3.3.5와 3.3.8.2에서 명확히 함.
- 임시 모드: 위 사례의 원본(photo blob, text 원문)도 메모리에만 둠. 영구 저장(IndexedDB)에 원본/저장 키/해시/MIME/바이트 크기를 남기지 않음(2.5.2, 8장 참고). 임시 모드에서 새로고침/종료 후 메모리 원본이 없어지면 `originalBlobRef`로 원본을 못 찾는 상태이므로, 누락으로 표시하고 다른 파일로 대체하지 않는다.
- 재방문 시 같은 원본 열기: persistent 모드에서는 `originalBlobRef`로 같은 Workspace의 IndexedDB에 저장된 원본을 다시 연다. 재접속해도 blob 자체가 아닌 이 저장 키로 원본을 찾고, 새 object URL은 열람할 때만 만든다.
- 로그·콘솔·자동 요약 노출 금지: 위 사례 어디에서도 저장 키·원문 전체·해시 조합을 로그·콘솔·자동 요약에 그대로 쓰지 않음. 사용자가 직접 열어보는 원문 화면에서는 각 원문 전체 열람·원본 다운로드를 허용한다.
- OCR·가공본이 원본을 덮지 않음: 사례 1·2에서 확인.

결론:
- 3.3 변경(원본 blob을 찾는 저장 키로 관리, sha256/mimeType/byteSize/text 구분, 타입별 필수/null, 자동 교체 금지, 재업로드 경고 vs 지급 단정 금지, 임시 모드 메모리만, 원문 못 찾으면 누락 표시·다른 파일로 대체 금지, 재방문 시 같은 원본 열기, 노출 제어)은 이번 3개 사례와 충돌하지 않으며, 기존 수령 규칙과도 충돌하지 않는다.

#### 3.3.9 문서 검산 (원문 전면 열람 허용·콘솔 출력 금지 기준)

 이번 변경은 원문 노출을 전면 금지하는 것이 아니라, **사용자가 직접 열어보는 원문 화면**에서는 photo/PDF/텍스트 원문 전체 열람과 원본 다운로드를 허용하고, **로그·콘솔·자동 요약**에는 원문 전체·내부 저장 경로를 노출하지 않는 것으로 정리한다. 아래 3개 사례로 이 원칙이 3.3 및 관련 절과 충돌하지 않는지 확인한다. 타입·해시·수령 규칙은 그대로 유지한다.

##### 3.3.9.1 문서 검산 사례 A — 사진 전체 열람 + 콘솔 출력 금지

입력/상황:
- photo 원문 등록: `sha256 = H1`, `mimeType = "image/jpeg"`, `byteSize = 245,760`, `originalBlobRef = "idb:ws-1/photo/abc-123"`, `sourceValue = null`.
- 사용자가 원문 화면에서 사진을 열고 원본 다운로드를 시도한다.
- 동시에 시스템이 디버그 로그·콘솔·자동 요약 텍스트를 남긴다.

기대 결과:
- 원문 화면: photo 원본 다운로드와 사진 전체 열람을 허용한다(사용자 직접 열람 화면).
- 로그·콘솔·자동 요약: 저장 키·원문 전체·해시 조합을 그대로 노출하지 않는다. 구현에 필요한 메타만 남기고, 원문 전체·내부 저장 경로는 노출하지 않는다.
- 원문 자체는 `ExtractionCandidate`·`ConfirmedValue`와 분리되어 유지되고, OCR 재실행이 원본·해시를 덮어쓰지 않는다.

충돌 여부:
- 충돌 없음. 3.3.1이 "원문 전체·저장 키는 로그·콘솔·자동 요약에 그대로 노출하지 않고, 열람 화면에서만 보인다"고 정리했고, 8장도 같은 구분을 유지한다. photo/PDF 식별 필드(sha256/mimeType/byteSize/originalBlobRef)와 수령 규칙(3.12/3.13)은 그대로다.

##### 3.3.9.2 문서 검산 사례 B — PDF 전체 열람 + 콘솔 출력 금지

입력/상황:
- PDF 원문 등록: `sha256 = X`, `mimeType = "application/pdf"`, `byteSize = 912,000`, `originalBlobRef = "idb:ws-1/pdf/def-456"`.
- 사용자가 원문 화면에서 PDF를 열고 원본 다운로드를 시도한다.
- 동시에 콘솔 출력·자동 요약이 생성된다.

기대 결과:
- 원문 화면: PDF 전체 열람과 원본 다운로드를 허용한다.
- 로그·콘솔·자동 요약: 저장 키·hash·MIME·byteSize의 원문 식별 조합을 그대로 노출하지 않는다.
- 같은 파일 재업로드는 경고 대상일 수 있으나, 동일 지급으로 단정하지 않는다(3.3.5 유지).

충돌 여부:
- 충돌 없음. 원문 열람 허용과 콘솔·자동 요약 노출 금지는 서로 다른 대상이다. PDF 원본 수정 불가(19번 금지 조합)와도 충돌하지 않는다.

##### 3.3.9.3 문서 검산 사례 C — 텍스트 원문 전체 열람 + 콘솔 출력 금지

입력/상황:
- 텍스트 원문 직접 입력: `sourceType = "text"`, `sourceValue = "…원문 전체…"`.
- 사용자가 원문 화면에서 텍스트 전체를 연다.
- 동시에 로그·콘솔·자동 요약이 생성된다.

기대 결과:
- 원문 화면: 텍스트 원문 전체 열람을 허용한다.
- 로그·콘솔·자동 요약: `sourceValue`(원문 전체)를 그대로 노출하지 않는다.
- 텍스트 원본은 blob 없이 저장되며, 가짜 파일·가짜 저장 키/hash/MIME/byteSize를 만들지 않는다.

충돌 여부:
- 충돌 없음. text 원문은 `sourceValue`로만 원문을 식별하며, photo/pdf 필드와 섞이지 않는다. 원문 전체는 로그·콘솔·자동 요약에만 노출하지 않고, 사용자 직접 열람 화면에서는 허용한다.

##### 3.3.9.4 충돌 문장 정리 확인

이번 변경으로 직접 고친 문장은 다음 곳이다.

- 3.3 필드 표: `originalBlobRef`를 "사진·PDF 원본 blob 참조"에서 "사진·PDF 원본을 찾는 저장 키"로 바꾸고, 화면용 object URL이 아니라 영구 저장 키로 쓰지 않는다는 점, persistent에서는 같은 Workspace IndexedDB 원본을 다시 열고 temporary에서는 메모리 원본만 참조하며 못 찾으면 누락 표시·다른 파일로 대체하지 않는다는 점을 명시.
- 3.3 타입별 보관 방식: photo/pdf의 `originalBlobRef`를 blob 참조가 아니라 저장 키로 표현하고, text는 가짜 저장 키·가짜 파일을 만들지 않는다고 명확화.
- 3.3.7 타입별 필수/선택 요약: photo/pdf 비고를 "원본 blob 참조"에서 "원본 저장 키 참조"로 변경.
- 3.3.8 문서 검산: 규칙 충돌 없음 확인에서 원본 정체성 해시/MIME/byteSize/sourceValue로 정리하고, object URL과 저장 키 분리, 재방문 시 같은 원본 열기, 임시 모드 새로고침 후 원본 없음→누락 표시·대체 금지, 저장 키를 로그·콘솔·자동 요약에 그대로 노출하지 않음을 추가.
- 3.3.9 검산 사례 A·B·C: 입력 예시 `originalBlobRef`를 `"blob:…photo1"`·`"blob:…pdf1"`에서 `"idb:ws-1/photo/abc-123"`·`"idb:ws-1/pdf/def-456"` 등 저장 키 예시로 바꾸고, 로그·콘솔·자동 요약 노출 금지 대상을 "blob 경로"에서 "저장 키"로 표현.
- 8장 표·본문: "원본 blob 경로"를 "저장 키(originalBlobRef)"로 표현하고, 임시 모드에서 원본 못 찾으면 누락 표시·다른 파일로 대체 금지, 재방문 시 같은 Workspace IndexedDB 원본을 다시 여는 점을 추가.

결과:
- 옛 금지문을 남겨두지 않고, "사용자 직접 열람 화면 허용 / 로그·콘솔·자동 요약 노출 금지" 구분으로 통일했다.
- 타입 구분(photo/pdf/text/other), SHA-256/MIME/byteSize, 수령 규칙(3.12/3.13), 원본 교체 금지, 재업로드 경고 vs 지급 단정 금지는 그대로 유지한다.

### 3.4 추출 후보 (ExtractionCandidate)

OCR/AI 등이 내놓은 후보. 사용자 확인 전에는 확정값이 아니다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `sourceDocumentId` | 문자열(외래) | 예 | 원문 id. |
| `payPeriodId` | 문자열(외래) 또는 null | 예 | 후보 연결 기간. |
| `candidateType` | 문자열(열거) | 예 | `"payee" | "amount" | "date" | "item" | "hours" | "rate" | "deduction" | "other"` |
| `candidateValue` | 정수 또는 문자열 | 예 | 후보 값. 돈의 경우 정수 원. 시간의 경우 정수 분. |
| `candidateUnit` | 문자열 | 예 | `"won" | "minutes" | "date" | "text"` |
| `rawText` | 문자열 | 예 | 후보 근거 원문 조각. |
| `confidence` | 0~1 실수 | 예 | 기계 추정 신뢰도. |
| `status` | 문자열(열거) | 예 | `"pending" | "proposed" | "confirmed" | "rejected" | "superseded"` |
| `confirmedById` | 문자열 또는 null | 예 | 사용자 확인 시 연결한 세션/작업 식별자. |

- 추출 후보는 **후보일 뿐**이며, 사용자 확인 전에는 확정값으로 쓰지 않는다.
- 늦은 OCR/AI 응답이 최신 확인값을 덮지 않는다. 후보는 별도 객체로 남고, 확인값과 경쟁하지 않는다.

### 3.5 사용자 확인값 (ConfirmedValue)

사용자가 확인한 값. 원문·후보와 분리한다. **값·확인 상태·출처**를 함께 남긴다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
|| `targetType` | 문자열(열거) | 예 | `"payperiod" | "payment" | "statement" | "statementItem" | "workRecord" | "rateCondition" | "calculation" | "question" | "output"` |
|| `targetId` | 문자열(외래) | 예 | 확인 대상 객체의 고정 id. 배열의 순번이 아니라 해당 객체 id로 추적한다. |
|| `targetItemId` | 문자열 또는 null | 예 | 배열 내부 항목을 확인할 때는 그 항목의 고정 id(예: StatementItem.id). `targetType`이 배열 항목을 가리킬 때만 채운다. `targetItemId`가 있으면 `fieldName`과 함께 쓰고, 배열 순번 표기(예: `items[2]`)는 쓰지 않는다. |
|| `fieldName` | 문자열 또는 null | 예 | 확인 대상 필드명(예: `"amount"`, `"hoursMinutes"`, `"ratePerHourWon"`, `"baseHoursMinutes"`, `"netWorkMinutes"`, `"breakMinutes"`). 배열 항목 확인 시 `targetItemId`와 쌍을 이룬다. |
|| `fieldPath` | 문자열 또는 null | 예 | (호환 표기) 기존 `statement.items[2].amount` 형태 표기가 남아 있는 경우 참고용. 새 확인값은 `targetId` + `targetItemId` + `fieldName`으로 남긴다. |
|| `confirmedValue` | 정수 또는 문자열 또는 boolean 또는 null | 예 | 사용자가 확인한 값. 돈의 경우 정수 원, 시간의 경우 정수 분, 참/거짓이 필요한 항목은 boolean. 미확인이면 null. |
|| `confirmedValueUnit` | 문자열 | 예 | `"won" | "minutes" | "date" | "text" | "boolean" | "enum"` |
| `status` | 문자열(열거) | 예 | `"unconfirmed" | "confirmed" | "confirmedZero" | "estimated" | "missing"` |
| `statusNote` | 문자열 또는 null | 예 | 상태 설명 메모. |
|| `sourceDocumentId` | 문자열(외래) 또는 null | 예 | 이 확인값의 출처 원문 id. 확인이 원문에서 비롯됐으면 채운다. 직접 입력(`source = "user_input"`)이면 null일 수 있다. |
|| `sourceLocationNote` | 문자열 또는 null | 예 | 원문 내부 위치 메모(예: PDF 페이지, 사진 속 항목 위치, 텍스트 구간). 실제 원문 조각 자체를 여기에 넣지 않는다. 원문 조각은 `sourceRawFragment`로 남긴다. |
|| `sourceRawFragment` | 문자열 또는 null | 예 | 확인에 쓴 원문 조각(텍스트 원문 구간에서 복사한 문자열). photo/pdf면 해당 페이지/영역 메모만 남기고 여기엔 null. 원문 전체(`sourceValue`)를 다시 저장하지 않는다. |
|| `candidateId` | 문자열(외래) 또는 null | 예 | 추출 후보(`ExtractionCandidate.id`)를 보고 확인했으면 남긴다. 직접 입력이면 null. 후보 확인 여부는 `source = "user_review_of_candidate"`와 함께 본다. |
|| `source` | 문자열(열거) | 예 | `"user_input" | "user_review_of_candidate" | "user_review_of_source" | "import"` |
|| `sourceNote` | 문자열 또는 null | 예 | 출처 상세 자유 메모. 구조 필드로 추적이 충분하면 비운다. |
| `confirmedAt` | 날짜시간 또는 null | 예 | 사용자 확인 시각. |

**status 규칙 (핵심):**

| 상태 | 의미 | 0 처리 |
|---|---|---|
| `unconfirmed` | 아직 확인 안 됨 | 0으로 채우지 않음 |
| `confirmed` | 사용자가 값을 확인함 | 확인된 값 저장 |
| `confirmedZero` | 사용자가 0임을 확인함 | 0을 확인된 값으로 저장. 미확인과 구분 |
| `estimated` | 사용자가 추정값이라고 명시함 | 추정 표시, 자동 계산에는 넣지 않음 |
| `missing` | 값 없음이 확인됨(항목 부재 등) | 별도 상태. 0과 다름 |

- `confirmedValue = null` + `status = "unconfirmed"` → 미확인.
- `confirmedValue = 0` + `status = "confirmedZero"` → 0임을 확인함.
- 두 상태를 절대 섞지 않는다. 계산 시에도 구분한다(3.18, 3.19 참고).
- 출처는 다음 조합으로 추적한다.
  - `SourceDocument.id`(어떤 원문/증빙에서 왔는지)
  - 원문 내부 위치: 텍스트 원문은 원문 조각(rawText 수준) 또는 해당 구간, 사진/PDF는 페이지 또는 항목 식별 메모(문서 내부 위치)
  - 확인 대상이 배열 항목이면 `targetItemId`(항목 고정 id) + `fieldName`(필드명). 배열 순번으로 추적하지 않는다.
  - 추출 후보를 보고 확인했으면 `source = "user_review_of_candidate"`로 두고, 해당 후보 id가 있으면 별도 필드로 후보 id를 남긴다(이번 모델에서는 `ExtractionCandidate.id`를 기억·추적한다).
- 계산은 **한 군데로 정한 ConfirmedValue**에서 가져온 확인값만 입력으로 쓴다. 같은 값을 여러 곳에 따로 저장하지 않는다. 값 타입은 돈(정수 원), 시간(정수 분), 참/거짓(boolean), 문자열, null을 포함하고, 단위/타입이 다른 값을 섞어 계산 입력으로 쓰지 않는다.

### 3.6 명세서 (Statement)

명세서 전체. 항목·실지급액·내부 합계를 담는다. **명세서 기재 실지급액은 별도 필드로 보존**하고, 내부 계산값으로 덮어쓰지 않는다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `payPeriodId` | 문자열(외래) | 예 | |
| `jobId` | 문자열(외래) | 예 | |
| `sourceDocumentId` | 문자열(외래) 또는 null | 예 | 연결된 원문 문서. |
| `statementType` | 문자열(열거) | 예 | `"standard" | "revised" | "draft"` |
| `effectiveDate` | 날짜 또는 null | 예 | 수정본 적용일(사용자 확인 후). |
| `baseHoursMinutes` | 정수 또는 null | 예 | 명세서 기준 근무 시간(분). 미확인이면 null. |
| `baseRatePerHourWon` | 정수 또는 null | 예 | 명세서상 시급(원/시간). 미확인이면 null. |
| `items` | 배열(3.7 참조) | 예 | 명세서 항목 목록. |
| `statedNetPay` | 정수 또는 null | 예 | **명세서 기재 실지급액(원).** 내부 계산값과 별도 보존. |
| `statedTotalPay` | 정수 또는 null | 예 | 명세서 기재 총지급(원). |
| `statedDeduction` | 정수 또는 null | 예 | 명세서 기재 공제(원). |
| `internalCalculatedNetPay` | 정수 또는 null | 예 | 내부 계산 실지급액(원). 명세서 기재액과 다르면 둘 다 보존. |
|| `internalCalculatedTotal` | 정수 또는 null | 예 | 내부 계산 합계(원). |
|| `status` | 문자열(열거) | 예 | `"draft" | "confirmed" | "superseded" | "corrected"` |
|| `previousStatementId` | 문자열 또는 null | 예 | 이전 유효 명세서 id(버전 체인). 신규 원본이면 null. |
|| `adopted` | boolean | 예 | 사용자가 이 수정본/명세서를 현재 채택했는지. |
|| `adoptedAt` | 날짜시간 또는 null | 예 | 사용자가 채택을 확인한 시각. 미채택이면 null. |
||| `periodAdopted` | boolean | 예 | (`adopted = true`일 때) 이 명세서가 해당 급여기간의 현재 채택본인지 표시. 현재 채택본은 일반본/수정본을 통틀어 기간당 최대 1개. |

#### 3.6.1 전월/당월 수정본 구분

- 같은 급여기간의 명세서가 여러 버전일 수 있다. `revision`, `statementType = "revised"`, 그리고 이전본 연결 필드로 구분한다.
- 새 명세서 업로드가 기존 명세서를 자동 교체하지 않는다. 기존 명세서는 `status = "superseded"`로 표시하고 보존한다.
- 수정본은 **이전본ID**를 명시한다. `previousStatementId`는 직전 유효 명세서 id를 가리킨다(버전 체인). 신규 원본 명세서는 `previousStatementId = null`.
- 수정본 적용 여부는 **사용자의 채택 여부·시점**으로 기록한다.
  - `adopted = true/false`로 현재 사용자가 해당 수정본을 채택했는지 표시한다.
  - 채택 시점은 `adoptedAt`에 남긴다. 미채택이면 null.
- 명세서 **현재 채택본은 일반본/수정본을 통틀어 기간당 최대 1개**다. 즉 같은 급여기간에 `adopted = true`인 명세서가 이미 있으면 같은 기간에 새 채택본을 다시 만들 수 없다.
- **새 본 채택과 이전본 해제는 함께 성공**해야 한다. 새 본을 채택하면 이전 채택본은 `superseded`로 정리하고, 이전본 해제가 함께 확정되기 전에는 새 본 채택만 먼저 확정하지 않는다. 저장된 상태는 "채택본 교체 완료" 또는 "아무 변화 없음" 둘 중 하나여야 하며, 새 본 채택만 적용되고 이전본 해제가 누락되는 부분 저장 상태를 허용하지 않는다.
- **업로드만으로는 이전본 상태(채택/해제)가 바뀌지 않는다.** 새 파일을 올렸다고 기존 채택본이 자동으로 superseded되거나 해제되지 않는다. 이전본 상태 변경은 사용자가 명시적으로 새 본을 채택 확인해야만 함께 발생한다.
- 정정 전 원문·이전본은 보존한다.

### 3.7 명세서 항목 (StatementItem)

명세서 내부 개별 항목. 원문 추출 후보·사용자 확인값과 분리한다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | 항목 자체 id. |
| `statementId` | 문자열(외래) | 예 | 속한 명세서 id. |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | (명세서 하위로 저장 시)
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `itemType` | 문자열(열거) | 예 | `"basePay" | "overtime" | "night" | "holiday" | "allowance" | "deduction" | "other"` |
| `itemName` | 문자열 또는 null | 예 | 항목명. |
| `amount` | 정수 또는 null | 예 | 항목 금액(원). 미확인이면 null. |
| `amountStatus` | 문자열(열거) | 예 | `"unconfirmed" | "confirmed" | "confirmedZero" | "estimated" | "missing"` |
| `hoursMinutes` | 정수 또는 null | 예 | 해당 항목의 근무 시간(분). 해당 시. |
| `hoursStatus` | 문자열(열거) | 예 | 시간 확인 상태(위 amountStatus와 동일 체계). |
| `ratePerHourWon` | 정수 또는 null | 예 | 항목 적용 시급(원/시간). |
| `rateStatus` | 문자열(열거) | 예 | 시급 확인 상태. |
| `candidateRef` | 문자열 또는 null | 예 | 추출 후보 id(확인 전 후보 출처 추적). |
| `note` | 문자열 또는 null | 예 | 항목 메모. |

- 항목의 `amount`, `hoursMinutes`, `ratePerHourWon`은 각각 **별도 확인 상태**를 가진다.
- 항목 금액 = 명세서 내부 산술 대상. 확인되지 않은 항목을 0으로 채우지 않는다.

### 3.8 근무기록 (WorkRecord)

날짜별 출퇴근·휴게·메모·증빙. 상태는 예정/실제/회상/미기록으로 구분한다.

|| 필드 | 타입 | 필수 | 설명 |
||---|---|---|---|
|| `id` | 문자열 | 예 | |
|| `workspaceId` | 문자열 | 예 | |
|| `revision` | 정수 | 예 | |
|| `createdAt` | 날짜시간 | 예 | |
|| `updatedAt` | 날짜시간 | 예 | |
|| `payPeriodId` | 문자열(외래) 또는 null | 예 | |
|| `jobId` | 문자열(외래) | 예 | |
|| `workDate` | 날짜 | 예 | 실제 근무일. |
|| `status` | 문자열(열거) | 예 | `"planned" | "actual" | "recalled" | "unrecorded"` |
|| `startTimeMinutes` | 정수 또는 null | 예 | 시작 시각(자정 기준 분). 미확인이면 null. |
|| `endTimeMinutes` | 정수 또는 null | 예 | 종료 시각(자정 기준 분, 다음날 허용). |
|| `endTimeDate` | 문자열 또는 null | 예 | 종료 날짜 확인 표기. `"sameDay"` 또는 `"nextDay"` 중 하나. 미확인이면 null. 시작 대비 종료가 같은 날인지 다음날인지 저장하는 사실 필드이며, 계산된 근무분과 구분한다. |
|| `breakMinutes` | 정수 또는 null | 예 | 휴게(분). 미확인이면 null. |
|| `breakStatus` | 문자열(열거) | 예 | `"unconfirmed" | "confirmed" | "confirmedZero" | "missing"` |
|| `elapsedMinutes` | 정수 또는 null | 예 | 시작~종료 경과분(계산값). 실제 근무분과 구분한다. 미확인이면 null. |
|| `netWorkMinutes` | 정수 또는 null | 예 | 근무 순분(계산값 또는 사용자 확인값). 입력 경과·휴게·끝 날짜 사실과 구분하여 저장한다. 미확인이면 null. |
|| `nightFlag` | boolean 또는 null | 예 | 야간 구간 포함 여부. 확인 전이면 null. |
|| `note` | 문자열 또는 null | 예 | 메모. |
|| `sourceDocumentId` | 문자열(외래) 또는 null | 예 | 증빙 원문. |
|| `recordedAt` | 날짜시간 | 예 | 근무기록 작성/정정일. 근무일과 분리. |
|| `gapFlag` | boolean | 예 | 시간 겹침·모호 구간 표시. |
|| `correctionHistory` | 배열(3.8.3 참조) 또는 null | 예 | 정정 시 값·사유 이력. 정정 없으면 빈 배열 또는 null. |

**상태 규칙:**

- `unrecorded`는 기록이 없는 상태. 0분·결근으로 채우지 않는다.
- `actual`은 사용자가 실제로 확인한 기록. `recalled`은 나중에 회상한 기록. 둘을 구분한다.
- `planned`는 예정. 실제 합산에는 넣지 않는다.
- **계산된 근무분과 직접 확인한 근무분은 구분한다.** `netWorkMinutes`는 계산값일 수도 있고 사용자 확인값일 수도 있으며, 둘은 서로 다른 출처로 남긴다. `startTimeMinutes`·`endTimeMinutes`·`endTimeDate`·`breakMinutes` 같은 출퇴근 사실을 확정한 입력을, 계산된 `netWorkMinutes`를 정정했다고 해서 역수정하지 않는다.
- 계산값 정정으로 출퇴근 사실을 역수정하지 않는다. 정정은 `correctionHistory`에 값·사유와 함께 남기고, 입력 사실과 계산 근무분은 별도로 갱신한 뒤 이력화한다.

#### 3.8.1 미기록과 0분 확인 구분

- `status = "unrecorded"` + `netWorkMinutes = null` → 미기록.
- `status = "actual"` + `netWorkMinutes = 0` + `confirmStatus = "confirmedZero"` → 확인된 0분.
- 두 상태를 별도 상태로 표시한다.

#### 3.8.2 근무일 vs 작성/정정일

- `workDate`(근무일)와 `recordedAt`(작성/정정일)은 별도 필드. 합치지 않는다.
- "며칠치로 계산"할 때 기준을 섞지 않는다.

#### 3.8.3 정정 이력 보존

- 근무기록의 시간과 근무분은 정정할 수 있다. 정정 전 값은 삭제하지 않고 이력으로 남긴다.
- `correctionHistory` 각 항목은 정정 시점의 값과 정정 사유를 보존한다. 정정 뒤에도 이전 값이 남아, 어떤 값이 어떻게 바뀌었는지 추적한다.
- 계산된 근무분(`netWorkMinutes`)을 정정해도, 입력 경과(`elapsedMinutes`)/휴게(`breakMinutes`)/끝 날짜/다음날 여부 같은 입력 사실과 계산 근무분은 함께 갱신하고 이력으로 남긴다.
- 정정 이력 항목표:

|| 필드 | 타입 | 필수 | 설명 |
||---|---|---|---|
|| `at` | 날짜시간 | 예 | 정정 시각. |
|| `field` | 문자열 | 예 | 정정 대상 필드명(예: `"elapsedMinutes"`, `"breakMinutes"`, `"endTimeDate"`, `"netWorkMinutes"`). |
|| `beforeValue` | 정수 또는 boolean 또는 문자열 또는 null | 예 | 정정 전 값. |
|| `afterValue` | 정수 또는 boolean 또는 문자열 또는 null | 예 | 정정 후 값. |
|| `reason` | 문자열 또는 null | 예 | 정정 사유(사용자 메모/확인 필요). |

- 정정 이력 항목은 값 외에도 날짜·문자열을 보존할 수 있다. 예를 들어 `field`가 날짜 관련 입력이면 `beforeValue`/`afterValue`에 날짜 문자열을 남기고, 메모형 정정이면 `reason`에 문자열로 사유를 남긴다.

### 3.9 시급 조건 (RateCondition)

시급과 적용일을 기록한다. 과거 기록 자동 변경 금지, 역산 금지. 시급 유형은 시급/월급/일급/기타/미확인으로 구분하며, 시급이 미확인이면 `ratePerHourWon`은 **null**로 둔다.

|| 필드 | 타입 | 필수 | 설명 |
||---|---|---|---|
|| `id` | 문자열 | 예 | |
|| `workspaceId` | 문자열 | 예 | |
|| `revision` | 정수 | 예 | |
|| `createdAt` | 날짜시간 | 예 | |
|| `updatedAt` | 날짜시간 | 예 | |
|| `jobId` | 문자열(외래) | 예 | |
|| `rateType` | 문자열(열거) | 예 | `"hourly" | "monthly" | "daily" | "other" | "unknown"`. 시급 유형과 적용 범위 구분. |
|| `ratePerHourWon` | 정수 또는 null | 예 | 시급(원/시간). 정수, 1 이상 1,000,000 이하(정상 범위). `rateType = "hourly"`일 때 중심 값이며, 미확인이면 null. |
|| `rateStatus` | 문자열(열거) | 예 | `"confirmed" | "unconfirmed" | "conflicting"` |
|| `effectiveDate` | 날짜 또는 null | 예 | 적용 시작일. 미확인이면 null(보류). |
|| `effectiveEnd` | 날짜 또는 null | 예 | 적용 종료일. |
|| `source` | 문자열 또는 null | 예 | 시급 출처 메모. |
|| `note` | 문자열 또는 null | 예 | 시급 메모·확인 필요 사항. |
|| `isMinimumWageReference` | boolean | 예 | 사용자가 명시로 선택한 최저시급 참고 여부. 자동 대입 아님. |

**규칙:**

- 시급이 미확인이면 `rateType = "unknown"`이고 `ratePerHourWon`은 **null**로 둔다. 임의 시급을 만들어 역산하거나 자동 대입하지 않는다.
- 월급·일급 입력은 `rateType = "monthly" | "daily"`로 보존하되, 이를 시급으로 역산하지 않는다.
- `rateType = "other"`로 기록한 시급/단가도 시급으로 자동 환산하지 않는다. 환산이 필요하면 별도 확인값과 적용 시점을 기록한다.
- 적용일이 미확인이면 과거 기간에 자동 적용하지 않는다(자동 소급 금지). 새로 확인한 시급을 과거 기록에 자동 반영하지 않는다.
- 시급이 겹치면 `rateStatus = "conflicting"`으로 보류.
- 시급이 0 이하이거나 1,000,000 초과면 자료는 보존하되 기본급 참고 산술은 보류.
- 과거 기록을 새로 확인한 시급으로 자동 소급 수정하지 않는다. 정정은 사용자 확인 후 별도 이력·정정과 연결한다.

### 3.10 실제 지급 (ActualPayment)

사용자가 확인한 실제 입금액. 양수만 정상 값. 0원 수령은 별도 상태.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `jobId` | 문자열(외래) | 예 | |
| `sourceDocumentId` | 문자열(외래) 또는 null | 예 | 지급 증빙 원문. |
| `paymentChannel` | 문자열(열거) | 예 | `"bankTransfer" | "cash" | "other"` |
| `channelStatus` | 문자열(열거) | 예 | `"confirmed" | "unconfirmed"` (현금 등은 확인 전 보류) |
| `amount` | 정수 | 예 | 실제 지급액(원). **양수만 정상.** |
| `amountStatus` | 문자열(열거) | 예 | `"confirmed" | "unconfirmed"` |
| `depositDate` | 날짜 또는 null | 예 | 실제 입금 확인일. |
| `depositDateStatus` | 문자열(열거) | 예 | `"expected" | "confirmed"` |
| `note` | 문자열 또는 null | 예 | 지급 메모·중복/분할 확인 사항. |
| `duplicateFlag` | boolean | 예 | 동일 지급 중복 의심 표시. |
|| `splitGroup` | 문자열 또는 null | 예 | 분할 지급 그룹 식별자. |
|| `duplicateOf` | 문자열 배열 또는 null | 예 | 동일 지급으로 식별된 다른 ActualPayment.id 목록. 새 ID/파일 해시만으로는 중복 판단하지 않으며, 입금일·금액·채널·사용자 확인 조합으로 관리한다. |
|| `status` | 문자열(열거) | 예 | `"active" | "invalidated"`. 무효화 시 `invalidated`로 표시하고, 기록· ID는 보존한다. |

**규칙:**

- `amount`는 **양수**만 정상 값으로 다룬다. 0은 실제 지급으로 보지 않는다.
- 서로 다른 입금·계좌·현금·캡처·사용자 확인이 확인되면 **서로 다른 ActualPayment**로 등록한다. 같은 입금을 중복 등록하려는 시도는 `duplicateOf`로 표시한다.
- 중복·무효(`status = "invalidated"`)인 지급은 **지급 합계에서 제외**한다. 중복 의심만으로는 자동 제외하지 않고, 무효 처리는 별도로 확정한다.
- `ActualPayment`에는 **급여기간 `payPeriodId`를 넣지 않는다.** 월 귀속은 `PaymentAllocation`(`actualPaymentId` + `payPeriodId` + `allocatedAmount`) 하나로만 관리한다. 직접 `payPeriodId`와 이중 관리하지 않는다.
- 0원 수령 확인은 **같은 3.13 객체(kind=zeroReceipt)**로 처리한다. 실제 지급 합계에 넣지 않는다.
- 실제 지급 반영에는 양수 확인 + 급여 귀속 확인이 필요하다. 급여 귀속은 배분된 `PaymentAllocation`을 통해 확인한다.
- 무효 상태(`invalidated`)로 바뀐 지급은 삭제하지 않고 ID와 원 자료를 보존한다. 무효인 지급의 배분·합계 반영은 폐기한다.

### 3.11 외화·모호 입력 처리 (참고)

- 외화 입력은 원화 환산을 자동 적용하지 않는다. 환산이 필요하면 사용자 확인값과 적용 시점을 별도로 기록한다.
- "대략", "약" 등 모호 입력은 그대로 보존하고 자동 계산에 넣지 않는다.
- 돈 정상 범위: 절댓값 999,999,999 이하. 초과 시 자료 보존 + 산술 보류.

### 3.12 지급 배분 (PaymentAllocation)

한 지급을 여러 급여기간에 배분. 월 귀속과 월 합계의 근거는 이 객체다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `actualPaymentId` | 문자열(외래) | 예 | 원본 지급 id. |
| `payPeriodId` | 문자열(외래) | 예 | 배분 대상 급여기간. |
| `allocatedAmount` | 정수(양수) | 예 | 배분 금액(원). **0원 배분은 허용하지 않는다.** 배분하지 않으면 행을 만들지 않고 미배분으로 처리한다. |
| `allocationStatus` | 문자열(열거) | 예 | `confirmed | unconfirmed`. 미확인 상태에서는 월 합계에 반영하지 않는다. |
| `note` | 문자열 또는 null | 예 | 배분 메모. |

**제약(저장 시 검증 대상, 7장):**

- 같은 `actualPaymentId` + `payPeriodId` 쌍은 **하나만** 존재한다. 중복 배분 행은 허용하지 않는다.
- `allocatedAmount`는 **양수 정수**다.
- 같은 `actualPaymentId`의 `PaymentAllocation` 중 **확인된(`confirmed`) 배분 합계**는 원본 지급의 **확인된 금액 이하**여야 한다.
  - 원본 지급 `amountStatus = confirmed`이면, 확인된 배분 합계 ≤ 원본 지급 `amount`.
  - 원본 지급이 미확인 상태면, 확인된 배분만 따로 보고 최종 수령 총액을 단정하지 않는다.
- 배분 합계가 원본 지급 금액보다 작으면 나머지는 **미배분**으로 남긴다. 미배분은 월별 합산에서 제외한다.
- 배분 합계가 원본 지급 금액을 넘으면 그 배분은 적용 불가로 본다.
- `PaymentAllocation`이 없는 지급은 해당 급여기간에 배분된 것으로 보지 않는다. 귀속·월 합계는 이 객체로만 판단한다.

#### 3.12.1 배분 확정 규칙 (미수령·0원 수령 확인과의 공존)

- 같은 급여기간에 **active 상태의 미수령·0원 수령 확인**이 있으면, 해당 기간의 새 배분은 **`allocationStatus = unconfirmed`**으로만 남길 수 있다. 그 기간의 confirmed 확정 배분과 active 미수령·0원 수령 확인이 공존하는 저장은 허용하지 않는다.
- 반대로, 같은 급여기간에 확인된(`confirmed`) `PaymentAllocation`이 **하나라도** 있으면 그 기간에 **`UnreceivedConfirmation.active`는 생성할 수 없다.** 실제 입금 기록이나 다른 급여기간의 배분까지 막지는 않는다. 막는 것은 같은 급여기간의 `confirmed` 배분과 `active` 미수령·0원 수령 확인이 동시에 존재하는 저장뿐이다.

- 같은 급여기간의 active 미수령 확인은 kind와 무관하게 최대 1개다. 기존 active 또는 confirmed 배분이 있으면 새 active 생성은 거부한다.
- active가 있으면 같은 기간의 confirmed 배분을 거부한다. 사용자 동의로 active를 released로 바꾸고 이력을 보존한 뒤 배분을 확정한다. active를 만들 목적으로 실제 지급이나 confirmed 배분을 자동 삭제/해제하지 않는다.
- 기존 미수령·0원 수령 확인을 사용자가 해제 동의한 뒤에야 같은 급여기간에 `confirmed` 배분을 확정할 수 있다. 해제 동의를 안 하면 새 배분은 미확정(`unconfirmed`)으로 남긴다.
- 배분이 `unconfirmed`이면 그 배분은 월 합계(금액·수령 방식 확인된 지급의 confirmed 배분만 합산)에 반영하지 않는다. 해제 동의와 확정 전에는 월 합계에 넣지 않는다.
- 미수령·0원 수령 확인을 해제해도 기존 객체는 삭제하지 않고 `released`로 바꾸며, 이력과 함께 보존한다.

### 3.13 미수령·0원 수령 확인 (UnreceivedConfirmation)

받지 못했다고 확인한 상태(미수령)와 0원 수령을 확인한 상태를 **하나의 타입으로 합쳐** 관리한다. 실제 지급(양수)과는 구분되고, 같은 기간에 나중에 지급을 확인하면 사용자가 해제에 동의한 경우 해제(`released`)로 바꾸고 이력을 남긴다. 아직 수령 여부를 모르는 미확인 상태는 이 객체와 별도다(미확인 = 아직 기록 없음).

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `payPeriodId` | 문자열(외래) | 예 | |
| `jobId` | 문자열(외래) | 예 | |
| `sourceDocumentId` | 문자열(외래) 또는 null | 예 | |
| `kind` | 문자열(열거) | 예 | `unreceived | zeroReceipt`. 못 받았는지, 0원 수령인지 구분. |
| `status` | 문자열(열거) | 예 | `active | released` |
| `confirmedAt` | 날짜시간 | 예 | 미수령/0원 수령 확인 시각. |
| `releasedAt` | 날짜시간 또는 null | 예 | 해제 시각. 해제된 경우만 채운다. |
| `releaseNote` | 문자열 또는 null | 예 | 해제 메모. |
| `history` | 배열(3.13.1 참조) | 예 | 상태 변경 이력. |
| `note` | 문자열 또는 null | 예 | 확인 메모. |

#### 3.13.1 이력 항목

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `at` | 날짜시간 | 예 | 변경 시각. |
| `action` | 문자열(열거) | 예 | `created | released` |
| `note` | 문자열 또는 null | 예 | 변경 사유·메모. |

**규칙:**

- 미수령·0원 수령 확인은 **현재 유효(`active`) / 해제(`released`) 상태**와 **이력**을 함께 남긴다. 0원도 `active`로 기록한다.
- 같은 급여기간의 `UnreceivedConfirmation.active`는 **kind와 무관하게 최대 1개**만 허용한다. 같은 기간에 `active`가 이미 있으면 새 `active`는 만들지 않는다(저장 거부).
- 미수령·0원 수령 확인은 실제 지급 합계(금액·수령 방식이 확인된 지급의 confirmed 배분만 합산)에 넣지 않는다.
- 같은 기간의 active 미수령 확인과 confirmed 배분만 공존할 수 없다. 실제 지급 기록이나 다른 기간의 배분은 허용하며, 입금 기록만으로 active를 자동 해제하지 않는다.
- 같은 급여기간에 `confirmed` `PaymentAllocation`이 하나라도 이미 있으면, 그 기간에 `UnreceivedConfirmation.active`는 **생성할 수 없다.** 실제 입금 기록이나 다른 급여기간의 배분까지 막지 않는다. 막는 것은 같은 급여기간의 `confirmed` 배분과 `active` 미수령·0원 수령 확인이 동시에 존재하는 저장뿐이다.
- 어떤 급여기간에 `active` 미수령·0원 수령 확인이 있으면, 같은 기간에 새로 배분을 확정(confirmed)하지 않는다. 새 배분은 미확정(`unconfirmed`)으로만 남긴다. 해제 동의 후에만 해당 기간의 confirmed 배분이 가능하다(3.12.1).
- 같은 급여기간에 나중 지급(양수)을 확인하면, 기존 `active` 확인을 **바로 자동 해제하지 않는다.** 사용자에게 해제 여부를 확인하고, 해제할 경우 `released`로 바꾸고 `releasedAt`, `releaseNote`, 이력에 `released` 항목을 추가한다.
- 해제하더라도 기존 객체는 삭제하지 않고, 이력과 함께 보존한다.
- 실제 지급으로 반영하려면 양수 확인 + 급여 귀속 확인이 필요하다.
- 미확인(수령 여부를 아직 모르는 상태)은 이 객체가 아니라 "기록 없음"으로 둔다. 미수령·0원 수령 확인은 사용자가 '못 받았다'/'0원 받았다'고 확인한 경우만 생성한다.

### 3.14 의문 (Question)

확인·정리 중인 쟁점. 상태 전이 규칙을 따른다(DOMAIN.md 9장).

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `payPeriodId` | 문자열(외래) 또는 null | 예 | |
| `jobId` | 문자열(외래) | 예 | |
| `questionType` | 문자열(열거) | 예 | `"amountDiff" | "missingItem" | "missingPayment" | "unconfirmedHours" | "rateConflict" | "unreceived" | "other"` |
| `title` | 문자열 | 예 | 쟁점 제목. |
| `description` | 문자열 | 예 | 쟁점 설명. |
| `status` | 문자열(열거) | 예 | 아래 상태 전이 표 참고. |
| `statusNote` | 문자열 또는 null | 예 | 상태 메모. |
| `relatedActualPaymentId` | 문자열 또는 null | 예 | 관련 실제 지급. |
| `relatedStatementId` | 문자열 또는 null | 예 | 관련 명세서. |
| `relatedWorkRecordId` | 문자열 또는 null | 예 | 관련 근무기록. |
| `relatedRateConditionId` | 문자열 또는 null | 예 | 관련 시급 조건. |
| `closingReason` | 문자열 또는 null | 예 | 종결 시 이유. `"paymentResolved" | "stopped" | "other"` |
| `closedAt` | 날짜시간 또는 null | 예 | 종결 시각. |

**상태 전이(강제 아님, 가능한 전이):**

| 현재 상태 | 다음 상태(사용자 행동) | 금액 영향 |
|---|---|---|
| `preparing` | `waiting_evidence` | 산정 보류 유지, 입력값만 보존 |
| `waiting_evidence` | `reviewing` | 새 자료는 항목·금액·날짜별 확인 후 반영, 기존 확인값과 병존 가능 |
| `preparing`/`reviewing` | `explained` | 산정 결과는 참고치 유지, 체불·차액 확정 아님 |
| `explained`/`reviewing` | `action_ready` | 지급 약속·실제 지급·남은 의문 분리 표시, 약속 합산 안 함 |
| `action_ready` | `waiting_reply` | 약속만 오면 reviewing, 실제 지급은 양수 확인 후만 반영 |
| `waiting_reply`/`reviewing` | `reviewing` (답변·보완·지급 약속) | 지급 약속 합산 안 함 |
| `waiting_reply`/`reviewing` | `reviewing` (실제 지급 양수 확인) | 급여 귀속 확인 후 결과 버전 갱신, 다른 의문 유지 |
| 위 상태 전부(종결 전) | `user_closed` | 자동 종결 조건 아님. 차액은 체불 자동 확정 아님 |
| `user_closed` | `user_closed` 유지 + 새 근거 표시 | 종결 상태 유지, 새 근거 별도 표시 |
| `user_closed` | `reviewing` (사용자가 다시 열면) | 남은 의문 재검토 |

- 기록만 시작한 사람에게는 의문을 자동 생성하지 않는다.

### 3.15 후속 답변 (FollowUpAnswer)

문의·상담 흐름에서 답변·보완 요청·수정 명세서 연결.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `questionId` | 문자열(외래) | 예 | 연결 의문. |
| `answerType` | 문자열(열거) | 예 | `"reply" | "supplementRequest" | "revisedStatement"` |
| `answerContent` | 문자열 | 예 | 답변·요청 내용. |
| `relatedStatementId` | 문자열(외래) 또는 null | 예 | 수정 명세서 연결 시. |
| `answerDate` | 날짜시간 또는 null | 예 | 답변 시점. |
| `confirmedById` | 문자열 또는 null | 예 | 사용자 확인 시. |
| `status` | 문자열(열거) | 예 | `"pending" | "sent" | "confirmed"` |

### 3.16 지급 약속 (PaymentPromise)

실제 지급과 분리하는 약속 기록.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `questionId` | 문자열(외래) | 예 | |
| `promisedAmount` | 정수 또는 null | 예 | 약속 금액. 미확인이면 null. |
| `promisedDate` | 날짜 또는 null | 예 | 약속 입금일. |
| `status` | 문자열(열거) | 예 | `"promised" | "partialDelivered" | "fulfilled"` |
| `note` | 문자열 또는 null | 예 | |

**규칙:**

- 지급 약속은 합산하지 않는다.
- 약속만으로 입금·사건 종결로 처리하지 않는다.

### 3.17 계산 결과 (CalculationResult)

세 가지 산술을 분리해 각각 결과를 남긴다. 어느 결과도 체불 확정으로 바꾸지 않는다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `payPeriodId` | 문자열(외래) | 예 | |
| `calculationType` | 문자열(열거) | 예 | `"statementInternal" | "paymentDiff" | "basePayReference"` |
| `calculationSubtype` | 문자열 또는 null | 예 | 세부 유형(예: `"netPayVerification"`, `"itemSumCheck"` 등). |
| `inputSnapshot` | 객체 | 예 | 계산에 쓴 입력값 스냅샷(사용자 확인값 기준). |
| `resultValue` | 정수 또는 null | 예 | 계산 결과(원). 보류 시 null. |
| `resultStatus` | 문자열(열거) | 예 | `"computed" | "pending" | "suspended" | "outOfRange"` |
| `suspendedReason` | 문자열 또는 null | 예 | 보류 사유. |
| `outOfRangeDetail` | 문자열 또는 null | 예 | 범위 초과 상세. |
| `roundingMethod` | 문자열 | 예 | `"roundHalfUp_afterSum"` 고정(이 앱 산술 규칙). |
| `relatedStatementId` | 문자열(외래) 또는 null | 예 | |
| `relatedActualPaymentId` | 문자열(외래) 또는 null | 예 | |
| `relatedRateConditionId` | 문자열(외래) 또는 null | 예 | |
| `isDeprecated` | boolean | 예 | 아래 6장 버전 연결 참고. |
| `deprecatedByRevision` | 정수 또는 null | 예 | 새 결과 버전 revision. |
| `deprecatedAt` | 날짜시간 또는 null | 예 | |

**세 산술 분리:**

1. **명세서 내부 산술(`statementInternal`)**: 명세서 항목 합산·차감으로 명세서 totals 확인.
2. **지급 차이(`paymentDiff`)**: 명세서 실지급액 − 해당 급여기간에 확인해서 배분한 지급만. 미연결·미확인 지급은 뺄셈에 넣지 않음.
3. **기본급 참고 산술(`basePayReference`)**: 시간·시급 등 입력 조건에 따른 기본급 참고치. 자동 추가 지급 확정 아님.

- 세 결과는 서로 혼동하지 않고 각각 결과를 남긴다.
- 중간 곱·합이 정수 범위를 넘으면 계산 보류, 어느 단계에서 넘었는지 남긴다.

### 3.18 출력 (Output)

한국어 + 선택 언어, 같은 사실·같은 버전 출력. 구버전 표시.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `payPeriodId` | 문자열(외래) | 예 | |
| `outputType` | 문자열(열거) | 예 | `"summary" | "comparison" | "inquiryDraft" | "consultDraft" | "calculationSummary" | "exportedFile"` |
| `language` | 문자열 | 예 | `"ko" | "en" | "vi" | "ne" | "km"` |
| `content` | 문자열 또는 객체 | 예 | 출력 내용. |
| `version` | 정수 | 예 | 출력 버전(결과 버전과 연결). |
| `status` | 문자열(열거) | 예 | `"generated" | "pending" | "failed" | "deprecated"` |
| `statusNote` | 문자열 또는 null | 예 | 생성 대기·실패 사유. |
| `relatedCalculationId` | 문자열(외래) 또는 null | 예 | 연결 계산 결과. |
| `relatedQuestionId` | 문자열(외래) 또는 null | 예 | |
| `isDeprecated` | boolean | 예 | 구버전 표시. |
| `deprecatedByOutputId` | 문자열 또는 null | 예 | 새 출력 id. |
| `generatedAt` | 날짜시간 또는 null | 예 | 생성 완료 시각. |

**규칙:**

- 정정 반영 후 출력은 **새 버전으로만** 제공. 구버전은 `isDeprecated = true`.
- 생성·검토 완료 항목만 최신 결과로 표시. 생성 대기·실패 상태는 최신 결과로 표시 안 함.
- 새 정정과 무관한 다른 기간 출력은 재생성 대상 아님.
- 내려받은 PDF는 소급 수정 불가. 앱에서 구버전 표시 + 필요 시 새 파일 생성.

### 3.19 양언어 출력 버전 묶음 (BilingualOutputBundle) — 선택

한국어 출력과 선택 언어 출력을 같은 사실·같은 버전으로 함께 확인·출력하기 위한 묶음.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | 문자열 | 예 | |
| `workspaceId` | 문자열 | 예 | |
| `revision` | 정수 | 예 | |
| `createdAt` | 날짜시간 | 예 | |
| `updatedAt` | 날짜시간 | 예 | |
| `payPeriodId` | 문자열(외래) | 예 | |
| `bundleVersion` | 정수 | 예 | 묶음 버전. |
| `koOutputId` | 문자열(외래) | 예 | 한국어 출력 id. |
| `targetLangOutputId` | 문자열(외래) | 예 | 선택 언어 출력 id. |
| `status` | 문자열(열거) | 예 | `"ready" | "pending" | "partial"` |
| `isDeprecated` | boolean | 예 | |
| `deprecatedByBundleId` | 문자열 또는 null | 예 | |

- 정정 시 양언어 출력의 금액·버전 표기가 일치해야 한다.
- 예전 출력(구버전)은 구버전으로 표시한다.

---

## 4. 관계도 (텍스트 표기)

### 4.1 엔티티 관계 (간략)

```
[Job] 1 ── N [PayPeriod]
   │              │
   │              ├──── N [SourceDocument] (원문)
   │              │         │
   │              │         └──── N [ExtractionCandidate] (추출 후보)
   │              │
   │              ├──── N [Statement] (명세서)
   │              │         │
   │              │         └──── N [StatementItem] (명세서 항목)
   │              │
   │              ├──── N [WorkRecord] (근무기록)
   │              │
   │              ├──── N [RateCondition] (시급 조건)
   │              │
   |              ├──── N [PaymentAllocation] (payPeriodId -> PayPeriod.id; actualPaymentId -> ActualPayment.id)
   │              │
   │              ├──── N [UnreceivedConfirmation] (미수령·0원 수령 확인: 상태·이력) — active/released + history 보존
   │              │
   │              ├──── N [Question] (의문)
   │              │         │
   │              │         ├──── N [FollowUpAnswer] (후속 답변)
   │              │         └──── N [PaymentPromise] (지급 약속)
   │              │
   │              ├──── N [CalculationResult] (계산 결과)
   │              │
   │              └──── N [Output] (출력)
                          │
                          └──── N [BilingualOutputBundle] (양언어 묶음, 선택)
   │
   └──── N [ConfirmedValue] (사용자 확인값) — 다수 targetType/대상 연결
```

### 4.2 확인값 분리 관계

```
[SourceDocument] (원문)
   │
   ├─▶ [ExtractionCandidate] (추출 후보) — 확인 전, 후보 상태
   │
   └─▶ [ConfirmedValue] (사용자 확인값) — 값·상태·출처 함께 저장
         │
         └─▶ 실제 계산에 쓰이는 값은 ConfirmedValue에서 가져온 확인값만
```

- 원문 → 추출 후보 → 사용자 확인값 순서로 가지만, **각 단계는 별도 객체**다.
- 추출 후보가 확인되지 않으면 확정값으로 쓰지 않는다.
- 늦은 OCR/AI 응답이 최신 ConfirmedValue를 덮지 않는다.

### 4.3 지급 배분 관계와 월 합계 (예시 1 — 배분만, 미수령 없음)

```
[ActualPayment] (입금액 100,000, 확인됨)
   │
   ├──▶ [PaymentAllocation] 급여기간 X(전월): 60,000 (confirmed)
   ├──▶ [PaymentAllocation] 급여기간 Y(당월): 30,000 (confirmed)
   └──▶ 미배분 10,000 (별도 상태, 월별 합산 제외)
```

- 배분 합계(90,000) ≤ 입금액(100,000) → 계산 가능.
- 미배분 10,000원은 0으로 채우지 않는다.
- 월 합계는 **금액·수령 방식이 확인된 지급의 confirmed 배분만** 더한다. 이 예시에서는 지급(A)이 확인됐고 배분 1·2가 모두 confirmed이므로 월 합계에 반영된다. 미배분은 반영하지 않는다.
- `actualPaymentId + payPeriodId` 쌍은 배분 1, 배분 2 각각 하나씩만 존재 → 중복 배분 아님.

### 4.4 미수령·0원 수령 확인과 새 지급 확정 (예시 2 — 별도 기간 Z, 해제 동의 후 확정)

```
급여기간 Z에 먼저 [UnreceivedConfirmation] active
   (kind=unreceived 또는 zeroReceipt, 미수령/0원 수령 확인, 해제 전)

이후
   Z에 실제 지급(B) 20,000원(확인됨) 추가
   → 사용자가 Z의 미수령 확인 해제에 동의
   → [UnreceivedConfirmation] status = released (releasedAt, releaseNote, history에 released 추가)
   → Z에 [PaymentAllocation] actualPaymentId=B, payPeriodId=Z, allocatedAmount=20,000, confirmed
   → Z 합계 = 20,000원 (확정 후 월 합계에 반영)
```

- **배분 전에는 월 합계에 반영하지 않는다.** 지급(B)이 확인돼도, 해제 동의와 확정 배분(confirmed) 전까지는 Z 합계·월 합계에 넣지 않는다.
- active 미수령 확인과 공존할 수 없는 것은 같은 기간의 confirmed 배분이다. 실제 지급 기록 자체는 허용한다. 사용자가 미수령 확인 해제에 동의하면 released로 바꾸고 이력을 보존한 뒤 해당 기간 배분을 확정한다.
- 해제 동의 없이 새 배분을 넣으면 그 배분은 `unconfirmed`으로 남고 월 합계에 반영하지 않는다. 해제 동의를 안 하면 새 배분은 미확정 상태로 남는다.
- 같은 기간에 active 미수령·0원 수령 확인이 있으면 그 기간의 새 confirmed 배분은 저장하지 않는다. 공존 저장은 허용하지 않는다.

### 4.5 미수령·0원 수령 확인과 배분·동시 확정 검증 (4개 시나리오)

아래 4개 시나리오는 미수령·0원 수령 확인과 지급/배분의 경계를 명시한 검산이다.

#### 4.5.1 시나리오 A — Z active 미수령 중, 다른 기간(X) 배분은 허용

```
급여기간 Z에 [UnreceivedConfirmation] active (kind=unreceived)
급여기간 X에 실제 지급(A) 100,000원(확인됨)
   → Z에는 active 미수령 확인이 있지만, X는 다른 급여기간이다.
   → X에 [PaymentAllocation] actualPaymentId=A, payPeriodId=X, allocatedAmount=60,000, confirmed 저장 가능.
```

- Z의 active 미수령 확인은 **같은 기간 Z의 confirmed 배분만 거부**한다.
- 다른 급여기간(X)의 실제 지급·배분까지 막지 않는다. X 배분은 정상적으로 저장된다.
- 결론: 같은 기간(Z) active 미수령 확인 + 다른 기간(X) confirmed 배분 공존 가능. 모순 없음.

#### 4.5.2 시나리오 B — Z active 미수령 중, Z 확정 배분(confirmed)은 거부

```
급여기간 Z에 [UnreceivedConfirmation] active (kind=unreceived 또는 zeroReceipt)
급여기간 Z에 실제 지급(C) 30,000원(확인됨)
   → Z에 [PaymentAllocation] actualPaymentId=C, payPeriodId=Z, allocatedAmount=30,000, confirmed 저장 시도
   → 같은 기간 Z에 active 미수령·0원 수령 확인이 있으므로, Z confirmed 배분 저장 거부.
   → 대신 Z에는 [PaymentAllocation] actualPaymentId=C, payPeriodId=Z, allocatedAmount=30,000, unconfirmed만 허용.
```

- 같은 기간 Z에 active 미수령·0원 수령 확인이 있으면, Z confirmed 배분은 저장 거부다.
- Z에는 confirmed 대신 `unconfirmed` 배분만 남길 수 있다. 해제 동의 전까지 월 합계에 반영하지 않는다.
- 실제 지급(C) 자체는 저장 가능하다. 막는 것은 같은 기간 Z의 confirmed 배분이지, 실제 지급 기록 전체가 아니다.
- 결론: Z active 미수령 확인 + Z confirmed 배분 공존 불가. Z unconfirmed 배분만 가능. 모순 없음.

#### 4.5.3 시나리오 C — Z active 미수령 해제(사용자 동의) 후, Z 확정 배분 허용

```
급여기간 Z에 [UnreceivedConfirmation] active (kind=unreceived 또는 zeroReceipt)
급여기간 Z에 실제 지급(D) 30,000원(확인됨) 추가
   → 사용자가 Z의 미수령 확인 해제에 동의
   → [UnreceivedConfirmation] status = released (releasedAt, releaseNote, history에 released 추가)
   → Z에 [PaymentAllocation] actualPaymentId=D, payPeriodId=Z, allocatedAmount=30,000, confirmed 저장 가능
   → Z 합계 = 30,000원 (월 합계에 반영)
```

- 해제 동의를 받기 전에는 Z confirmed 배분이 불가능하다(시나리오 B).
- 사용자가 해제에 동의하면, `active`를 `released`로 바꾸고 이력과 `releasedAt`, `releaseNote`를 남긴다.
- 해제 후에는 같은 기간 Z에 confirmed 배분이 가능하다.
- 결론: Z active 미수령 → 사용자 동의 → released → Z confirmed 배분 허용. 모순 없음.

#### 4.5.4 시나리오 D — Z active 미수령과 같은 period active 미수령 중복 생성은 거부

```
급여기간 Z에 [UnreceivedConfirmation] active (kind=unreceived)
   → 같은 Z에 [UnreceivedConfirmation] active (kind=zeroReceipt) 저장 시도
   → 같은 급여기간 Z에 active 미수령·0원 수령 확인이 이미 있으므로, 새 active 저장 거부.
```

- 같은 급여기간의 `UnreceivedConfirmation.active`는 **kind와 무관하게 최대 1개**만 허용한다.
- 기존 active를 먼저 만든 상태에서 같은 기간에 새 active를 만들려는 시도는 저장 거부다.
- released 이후라도 같은 기간에 다른 active나 confirmed 배분이 있으면 새 active를 생성하지 않는다. 둘 다 없고 사용자가 현재 미수령을 확인했을 때만 생성한다. kind가 달라도 active는 기간당 최대 1개다.

#### 4.5.5 모순 여부 결론

- 시나리오 A: Z active + X confirmed 배분 → 서로 다른 급여기간 → 공존 가능. 모순 없음.
- 시나리오 B: Z active + Z confirmed 배분 → 같은 기간 충돌 → 공존 불가(거부). 모순 없음.
- 시나리오 C: Z active → 해제(사용자 동의, 이력 보존) → Z confirmed 배분 허용. 모순 없음.
- 시나리오 D: Z active + 같은 period Z active 중복 → 최대 1개 규칙 위반 → 저장 거부. 모순 없음.
- 검증: Z active 중복 거부, Z confirmed 배분 거부, X 배분 허용, 해제 후 Z 배분 허용 모두 문서 규칙과 일관된다.

---

## 5. 버전·정정 연결 관계 (핵심)

### 5.1 확인값 변경과 결과 버전 저장 함께 성공

- `ConfirmedValue` 변경 시 관련 `CalculationResult`, `Output`, `BilingualOutputBundle`의 새 버전을 **같은 시점에 함께 저장**한다.
- 둘 중 하나만 먼저 저장하지 않는다. 저장 실패 시 이전 확인값과 이전 버전을 유지한다. 부분 저장(반만 성공) 상태로 두지 않는다.

### 5.2 근거 정정이 어떤 버전을 오래된 것으로 만드는지

- 정정(수정 명세서 적용, 확인값 변경 등)이 발생하면:
  - 해당 급여기간·의문·계산·출력의 **이전 버전**에 `isDeprecated = true`를 설정한다.
  - `deprecatedByRevision` / `deprecatedByOutputId` / `deprecatedByBundleId`로 새 버전을 가리킨다.
- 무관한 다른 달·다른 기간 변경은 같이 바꾸지 않는다.
- 정정 전 원문·이력은 보존한다(`SourceDocument` 삭제 안 함, `Statement` `status = "superseded"`).

### 5.3 버전 전이 예시 (DOMAIN.md 11장 사례 B)

```
Statement(9,120분)           → revision 1 → CalcResult(명세서 내부, 2,000,000)
   │                                  CalcResult(지급 차이, 20,000)
   │                                  CalcResult(기본급 참고, null)
   │
   ▼ 정정: 160시간 확인
   CalcResult(기본급 참고, 96,000) → 새 revision, 이전 결과 유지
   │
   ▼ 정정: 158시간 확인
   CalcResult(기본급 참고, 72,000)
   │
   ▼ 정정: 수정 명세서 적용(9,480분)
   Statement(9,480분) → revision 2 → CalcResult(명세서 내부, 2,072,000)
                                    CalcResult(지급 차이, 72,000)
                                    CalcResult(기본급 참고, 0)
   │
   └─ 이전 revision 1 결과들은 isDeprecated = true,
      deprecatedByRevision = 2 로 연결.
```

- 원본 지급 차이 20,000원과 정정 후 차이 72,000원은 별개 쟁점. 중복 합산하지 않는다.
- 기본급 참고 산술 차이(96,000 / 72,000)는 참고치. 자동 추가 지급 확정 아님.

### 5.4 예시 1 — 지급 A 10만원, X/Y 배분, 미배분 1만 (별도 미수령 없음)

아래 예는 **미수령·0원 수령 확인이 없는** 상황에서 지급 한 건을 두 급여기간에 배분한 경우의 검산이다.

#### 5.4.1 입력

| 항목 | 값 |
|---|---|
| 실제 지급(A) | 100,000원 (확인됨, 양수) |
| 배분 1 | 급여기간 X(전월)에 60,000원 배분, `allocationStatus = confirmed` |
| 배분 2 | 급여기간 Y(당월)에 30,000원 배분, `allocationStatus = confirmed` |
| 미배분 | 100,000 − (60,000 + 30,000) = 10,000원 |

#### 5.4.2 배분 검산

- 배분 합계(90,000) ≤ 실제 지급(A) 100,000 → 적용 가능.
- 미배분 10,000원은 0으로 채우지 않고 별도 상태로 표시한다.
- 미배분은 월별 합산에서 제외한다. 전월/당월 합산은 **금액·수령 방식이 확인된 지급의 confirmed 배분만** 본다.
- `actualPaymentId + payPeriodId` 쌍은 배분 1, 배분 2 각각 하나씩만 존재 → 중복 배분 아님.

#### 5.4.3 월 합계

- 지급(A)는 확인됐고(amountStatus = confirmed), 배분 1·2도 confirmed이므로 X 합계 = 60,000, Y 합계 = 30,000으로 월 합계에 반영된다.
- 미배분 10,000원은 월 합계에 넣지 않는다.

### 5.5 예시 2 — 별도 기간 Z 미수령 확인 → 지급 B 2만원 → 사용자 해제 동의 → Z 배분 확정 → Z 합계 2만원

아래 예는 **먼저 미수령·0원 수령 확인이 active로 있고**, 나중에 실제 지급(양수)이 들어온 뒤 사용자 해제 동의를 거쳐 배분을 확정하는 경우의 검산이다.

#### 5.5.1 입력

| 단계 | 내용 |
|---|---|
| 1 | 급여기간 Z에 `UnreceivedConfirmation` active가 먼저 있었음 (kind=unreceived 또는 zeroReceipt, 미수령/0원 수령 확인, 해제 전) |
| 2 | 이후 급여기간 Z에 실제 지급(B) 20,000원(확인됨, 양수) 추가 확인 |
| 3 | 사용자가 Z의 미수령·0원 수령 확인 해제에 동의 |
| 4 | Z에 `PaymentAllocation` actualPaymentId=B, payPeriodId=Z, allocatedAmount=20,000, allocationStatus=confirmed 확정 |

#### 5.5.2 배분 전 상태

- 지급(B)가 확인돼도 **해제 동의와 확정 배분(confirmed) 전까지는 Z 합계·월 합계에 반영하지 않는다.**
- Z에 active 미수령·0원 수령 확인이 있는 동안에는 새 confirmed 배분을 저장하지 않는다. 공존 저장은 허용하지 않는다. 해제 전에 새 배분을 넣으면 그 배분은 `unconfirmed`으로만 남고, 월 합계에 반영하지 않는다. 해제 동의를 안 하면 새 배분은 미확정 상태로 남는다.

#### 5.5.3 해제 후 확정

- 사용자가 해제에 동의하면:
  - `UnreceivedConfirmation.status = released`,
  - `releasedAt`, `releaseNote`, 이력에 `released` 항목 추가.
  - 기존 객체는 삭제하지 않고 보존한다.
- 이후 Z에 confirmed 배분(20,000)을 확정하고, **Z 합계 = 20,000원**으로 월 합계에 반영한다.

#### 5.5.4 수령 확인 상태 검산 (예시 1·2 공통 규칙)

- `PayPeriod.receiptStatus`는 `unknown | partial | complete`로 관리한다.
- `complete`는 등록 여부와 관계없이 해당 급여기간의 수령 내역을 빠짐없이 확인했다는 사용자 명시가 있을 때만 사용한다. 등록된 지급만 확인한 상태나 명세서 금액을 전부 받았다는 뜻이 아니다.
- 일부 입금 확인만으로는 `complete`로 바꾸지 않는다. 일부 확인은 `partial`로 남는다.
- `PayPeriod.periodStart`·`periodEnd`가 없으면 귀속·월 비교는 보류한다. 월 귀속은 `PaymentAllocation`으로만 판단한다.

#### 5.5.5 모순 여부 결론

- 예시 1: 배분 합계 ≤ 입금액, 동일 pair 중복 없음, 미배분 별도 처리 → 규칙 위반 없음.
- 예시 2: active 미수령 확인 중에도 실제 지급 기록은 저장할 수 있다. 같은 기간의 confirmed 배분만 거부한다. 사용자 동의로 active를 released로 바꾸고 이력을 남긴 뒤 해당 기간 배분을 확정해 월 합계에 반영한다.
- 미수령·0원 수령 확인 해제와 실제 지급 반영은 별도 객체·별도 시점 → 충돌 없음.
- 수령 확인 상태는 일부/전체 분리 → automatic complete 없음.

---

### 5.6 출력 버전 연결

```
Output(ko, version 1)   → Output(ko, version 2)로 갱신 시
Output(targetLang, version 1) → Output(targetLang, version 2)
BilingualOutputBundle(version 1) → BilingualOutputBundle(version 2)

이전 버전들: isDeprecated = true, deprecatedByOutputId / deprecatedByBundleId 연결.
```

---

## 6. 저장하면 안 되는 조합 (금지 조합)

아래 조합은 저장·계산·표시하지 않는다. 위반 시 보너스 데이터가 아닌 **오류/보류**로 본다.

| # | 금지 조합 | 이유 | 처리 |
|---|---|---|---|
| 1 | `ActualPayment.amount ≤ 0` | 실제 지급은 양수만 | 저장 거부 또는 별도 상태(0원 수령은 UnreceivedConfirmation kind=zeroReceipt) |
| 2 | `PaymentAllocation` 합계 > 원본 `ActualPayment.amount` | 배분 과다 | 적용 불가, 보류, 사용자에게 재배분 확인 |
| 3 | `ConfirmedValue.status = "unconfirmed"` + `confirmedValue = 0` | 미확인과 확인된 0 혼동 | 상태·값 분리. 미확인이면 null 유지 |
| 4 | `ConfirmedValue.status = "confirmedZero"` + `confirmedValue = null` | 확인된 0인데 값 없음 | 확인된 0은 value=0, status=confirmedZero로 저장 |
| 5 | 새 `SourceDocument` 업로드로 기존 `ConfirmedValue` 자동 교체 | 원문 자동 교체 금지 | 기존 확인값 보존, 별도 객체로 남김 |
| 6 | `ExtractionCandidate` 미확인 상태를 확정값으로 계산에 사용 | 후보=후보 | 확인 전에는 계산 입력 아님 |
| 7 | `WorkRecord.status = "unrecorded"` + `netWorkMinutes = 0` (확인 없이) | 미기록을 0분·결근으로 확정 | 별도 `unrecorded` 상태 유지 |
| 8 | `WorkRecord.status = "planned"`를 실제 근무 합계에 포함 | 예정은 실제 아님 | 예정은 합계에서 제외 |
| 9 | `Question.status` 전이 없이 실제 지급 확정만 반영 | 상태 전이 규칙 무시 | 실제 지급 확인 시 reviewing/reviewing 유지, 결과 버전 갱신 |
| 10 | `PaymentPromise`만으로 실제 지급 합산 | 약속=입금 아님 | 약속은 별도 표시, 합산 대상 아님 |
| 11 | `SomePaymentConfirmed` → 자동으로 `FullReceiptConfirmed` | 일부≠전체 | 일부 확인은 일부 상태 유지, `PayPeriod.receiptStatus = "complete"`는 전체 확인 표시일 때만 |
| 12 | 같은 급여기간의 active 미수령 확인과 confirmed PaymentAllocation 공존 | 같은 기간 배타 규칙 위반 | 어느 쪽을 나중에 저장해도 거부. 실제 지급 기록/다른 기간 배분은 허용. active는 사용자 동의로 해제하고 이력 보존 |
| 12a | `UnreceivedConfirmation` 해제 시 이력 미보존 | 이력 보존 규칙 위반 | `released`로 바꾸고 `releasedAt`, `releaseNote`, 이력에 `released` 항목 추가 |
| 13 | `Statement.statedNetPay`와 `internalCalculatedNetPay` 중 하나를 덮어씀 | 둘 다 보존 | 차이 시 둘 다 저장, 비교는 기재액 기준 |
| 14 | `CalculationResult` 하나가 다른 산술 결과를 덮어씀 | 세 산술 분리 | 각각 별도 객체로, 결과 구분 |
| 15 | 정정 반영 시 관련 출력·계산 중 일부만 새 버전으로 갱신 | 함께 성공 규칙 위반 | 확인값+결과 버전 함께 저장, 실패 시 롤백 유지 |
| 16 | `RateCondition` 시급 범위 밖 값(시급≤0, 시급>1,000,000)을 정상 계산에 사용 | 범위 밖 처리 규칙 | 자료 보존 + 기본급 참고 산술 보류 |
| 17 | `WorkRecord` 근무 구간 > 1,440분 또는 종료 시점 > 다음날 | 범위 밖 | 자료 보존 + 그 구간 산정 보류 |
| 18 | `PaymentAllocation`에 0원 배분 행 추가 / `actualPaymentId+payPeriodId` 중복 행 생성 | 배분 규칙 위반 | 0원 배분 금지, 동일 pair 하나, 불필요 시 행 미생성 |
| 18a | `ActualPayment`에 `payPeriodId`를 직접 넣고 `PaymentAllocation`과 이중 관리 | 월 귀속 이중 관리 금지 | 월 귀속은 `PaymentAllocation`으로만 |
| 19 | `downloaded PDF` 값을 앱 단정만으로 소급 수정 | 소급 수정 불가 | 구버전 표시 + 필요 시 새 파일 생성 |
| 20 | 로그·콘솔·자동 요약에 `sourceValue`/`fileName` 원문 전체나 `originalBlobRef` 등 내부 저장 경로를 그대로 노출 | 노출 제어 | 사용자 직접 열람 화면에서는 원문 전체 열람·원본 다운로드 허용. 로그·콘솔·자동 요약에는 원문 전체와 원본 blob 경로 노출 금지(열람 화면과 로그/출력 구분) |

---

## 7. 저장 시 검증 규칙 (로컬 저장 로직 참고)

코드/설치/기존 파일 수정은 다음 작업. 여기서는 규칙만 적는다.

1. **지급 배분·월 귀속 검증**: 월 귀속은 `PaymentAllocation`(`actualPaymentId` + `payPeriodId` + `allocatedAmount`)로만 판단한다. `ActualPayment`에 `payPeriodId`를 직접 넣지 않는다.
2. **동일 pair 중복 금지**: 같은 `actualPaymentId` + `payPeriodId` 쌍은 `PaymentAllocation`에 하나만 존재한다.
3. **배분액 양수 검증**: `PaymentAllocation.allocatedAmount > 0`. 0원 배분은 허용하지 않고, 배분하지 않으면 행을 만들지 않는다.
4. **확인된 배분 합계 검증**: 같은 `actualPaymentId`의 `PaymentAllocation` 중 `allocationStatus = "confirmed"`인 배분 합계는 원본 지급의 확인된 금액 이하. 원본 지급이 미확인이면 확인된 배분만 따로 보고 최종 수령 총액을 단정하지 않는다.
5. **지급 배분 합계 검증(보조)**: 같은 `actualPaymentId`의 모든 배분 합계 ≤ `ActualPayment.amount`. 초과 시 적용 불가.
6. **양수 검증**: `ActualPayment.amount > 0`인 실제 지급만 저장한다. 사용자가 0원 수령을 확인하면 3.13의 `UnreceivedConfirmation`으로 기록하고 지급 거래/합계에는 넣지 않는다. 음수 입력 자료는 보존하되 실제 지급이나 0원 수령 확인으로 변환하지 않고 확인 필요로 남긴다.
7. **null/0 구분 저장**: `ConfirmedValue`는 `status`와 `confirmedValue`를 쌍으로 저장. 미확인은 `status="unconfirmed"`, `confirmedValue=null`.
8. **중복 지급 확인**: `actualPaymentId` + 입금일 + 금액 + 채널 조합으로 중복 의심 표시. 동일 지급 식별 확인 시 추가 합산 대신 재업로드로 처리.
9. **기간 미확인 임시 저장**: `payPeriodId` null 허용, 단 월별 비교열·지급 귀속 확정 제외. `PayPeriod.periodStart`·`periodEnd` null이면 월 비교/귀속 보류.
10. **수령 확인 상태 규칙**: `PayPeriod.receiptStatus`는 `unknown / partial / complete`로 관리. 일부 입금 확인만으로 `complete`로 바꾸지 않는다.
11. **미수령 확인 규칙**: 같은 급여기간의 active 미수령 확인과 confirmed 배분만 공존을 금지한다. 실제 지급 기록이나 다른 기간 배분은 허용한다. active 해제는 사용자 동의를 받고 이력을 보존한다. confirmed 배분이 있으면 그 기간의 active 생성은 거부한다.
12. **범위 검증**: 돈 절댓값 ≤ 999,999,999. 시급 1~1,000,000. 근무 구간 0~1,440분. 범위 밖은 자료 보존 + 산술 보류.
13. **버전 함께 저장**: `ConfirmedValue` 변경 시 관련 `CalculationResult`, `Output`, `BilingualOutputBundle` 새 버전 동시 저장. 실패 시 이전 상태 유지.
14. **active와 confirmed 배분 상호 차단**: 같은 급여기간에 `UnreceivedConfirmation.active`가 있으면 같은 기간의 `confirmed` `PaymentAllocation`은 저장하지 않는다. 반대로 같은 급여기간에 `confirmed` `PaymentAllocation`이 하나라도 이미 있으면 그 기간에 `UnreceivedConfirmation.active`는 생성하지 않는다. 막는 것은 같은 급여기간의 `confirmed` 배분과 `active` 미수령·0원 수령 확인이 동시에 존재하는 저장뿐이다. 실제 지급 기록이나 다른 급여기간의 배분은 막지 않는다.
15. **active 중복 금지**: 같은 급여기간의 `UnreceivedConfirmation.active`는 kind와 무관하게 최대 1개만 허용한다. 같은 기간에 `active`가 이미 있으면 새 `active`는 저장하지 않는다(저장 거부).

---

## 8. 노출 제어 참고 (상세 절차는 다음 작업)

- `SourceDocument.fileName`, `sourceValue`, `originalBlobRef`, `sha256`, `mimeType`, `byteSize` 등 원문·원본 메타데이터는 **로그·콘솔·자동 생성된 요약 텍스트에 전체 노출되지 않도록** 처리한다.
- photo/pdf 원문에서는 원본 저장 키(`originalBlobRef`)·원본 해시·MIME·바이트 크기까지 로그·콘솔·자동 요약 노출 제어 대상에 포함한다. 텍스트 원문에서는 `sourceValue`(원문 전체)를 로그·콘솔·자동 요약 노출 제어 대상으로 둔다.
- **사용자 직접 열람 화면**은 위 로그·콘솔·자동 요약과 구분한다. 사용자가 직접 열어보는 원문 화면에서는 photo/PDF/텍스트 원문 전체 열람과 원본 다운로드를 허용한다. originalBlobRef는 원본을 찾는 저장 키이며, 화면용 object URL은 열람할 때만 만들고 영구 저장 키로 쓰지 않는다. 열람 화면에서 원문 전체·저장 키를 근거로 원본을 열어 보여주는 것과, 로그·콘솔·자동 요약에 그대로 쓰는 것은 다른 문제다.
- 이번 데이터 모델에서는 **존재·메타 정보는 보존**하고, 로그·콘솔·자동 요약에는 원문 전체·내부 저장 키·저장 키 기반 식별 조합을 그대로 노출하지 않는다. 열람 화면 노출과 로그/출력 노출 금지는 별도로 다룬다.
- 노출 제어는 OCR 결과·추출 후보·전송용 가공본에도 동일하게 적용한다. 원문 원본·해시를 덮는 방식으로 노출 제어를 구현하지 않는다(3.3.4, 3.3.5 참고).
- 백업 암호화/삭제/멀티탭 세부 절차, 구현 수준 노출 제어는 다음 작업으로 남긴다.
- 임시 모드(`mode = "temporary"`)에서 원본을 못 찾으면 누락으로 표시하고, 다른 파일로 대체하지 않는다. 재방문(영구 모드 재접속) 시에는 `originalBlobRef`로 같은 Workspace의 IndexedDB 원본을 다시 열어 같은 원본을 본다.

| 보호 대상 | 저장 위치 구분 | 로그·콘솔·자동 요약 처리(비구현) | 사용자 직접 열람 화면 |
|---|---|---|---|
| sourceValue(text 원문 전체) | 사용자 기기 IndexedDB·메모리 | 원문 전체 노출 금지 | 텍스트 원문 전체 열람·원본 다운로드 허용 |
| originalBlobRef(photo/pdf 저장 키) | 사용자 기기·메모리 등 | 저장 키(그리고 hash/MIME/byteSize)의 원문 식별이 가능한 조합을 그대로 노출 금지 | 저장 키로 원본을 찾아 blob 원본 다운로드 허용 |
| sha256 / mimeType / byteSize | 메타 저장 | 원문 식별이 가능한 조합을 무분별하게 노출하지 않음(원본 못 찾으면 누락 표시, 다른 파일로 대체하지 않음) | 사용자 직접 열람 화면 표시와는 별개(절차 다음 작업) |
| 추출 후보·OCR 결과 | 별도 객체 | 원문처럼 보이도록 노출하지 않음 | 원문 원본·해시를 덮지 않음 |

원문 열람은 사용자 기기에서 허용하는 방향과, 로그·불필요한 출력에 노출하지 않는 방향을 구분해 둔다:

- **사용자 직접 열람 화면**: 사용자가 등록한 photo/PDF/텍스트 원문을 열람/다운로드할 수 있도록 한다. 이 화면에서는 원문 전체 열람과 원본 다운로드를 허용한다.
- **로그·콘솔·자동 요약 노출 금지**: 디버그 로그, 콘솔 출력, 자동 생성된 요약 텍스트 등에 원문 전체·blob 경로·원본 식별 조합을 그대로 쓰지 않는다. 열람 화면과 달리, 로그·콘솔·자동 요약에는 원문 전체와 내부 저장 경로를 노출하지 않는다. 구현에 필요한 메타만 남기고 원문은 별도 보관·로그/출력 미노출로 다룬다.

임시 모드(`mode = "temporary"`)에서는 원본(photo/pdf blob, text 원문)도 메모리에만 둔다. 영구 저장(IndexedDB)에 원본/해시/MIME/바이트 크기를 남기지 않으며, 새로고침/종료 시 사라진다. 임시 모드에서 "저장됐다"고 표시하지 않는다(2.5.2 참고).

---


## 9. 저장 모드

- 각 객체의 id는 객체 고유 ID, workspaceId는 소속 Workspace.id 참조다.
- 저장 설정의 activeWorkspaceId는 현재 선택한 Workspace.id를 가리킨다. Workspace 객체 자체에는 activeWorkspaceId가 없다.
- persistent는 IndexedDB에서 기존 Workspace와 활성 포인터를 다시 열어 기록을 이어간다.
- temporary는 메모리만 사용하며 새로고침/종료 시 사라진다.
- 서버 계정/서버 영구 DB/자동 동기화는 포함하지 않는다. 상세 저장/복원 절차는 다음 작업이다.


---

## 10. 요약 테이블 (빠르게 참고)

| 객체 | 핵심 필드 타입 | null 허용 핵심 | 확인 상태 분리 | 비고 |
|---|---|---|---|---|
| Job | id, workspaceId, revision, createdAt, updatedAt, name(null), employerName(null), currency, language | name, employerName | 사용자 확인값 | workspaceId는 소속 Workspace.id 참조 |
| Workspace | id, mode(persistent/temporary), revision, createdAt, updatedAt | 없음(모두 필수) | 설정 변경 시 revision 증가 | activeWorkspaceId는 별도 저장 설정의 포인터이며 Workspace 필드가 아님. 다른 Workspace 참조 금지 |
| PayPeriod | + label(null), periodStart(null), periodEnd(null), depositDateExpected(null), depositDateActual(null), receiptStatus(unknown/partial/complete), status | periodStart, periodEnd, depositDateActual | 기간 미확인 임시 저장 가능, 일부≠complete | 월 귀속은 PaymentAllocation으로만 |
| SourceDocument | sourceType(photo/pdf/text/other), fileName(null 허용), sourceValue(text 시 원문 전체, photo/pdf 시 null), originalBlobRef(photo/pdf 필수, 원본을 찾는 저장 키), sha256(photo/pdf 필수·원본 전체, text/other은 별도), mimeType(photo/pdf 필수), byteSize(photo/pdf 필수), status, supersedesId(null 허용) | sourceType에 따라 필수/선택 다름(아래 3.3.7 참조) | 원문 보존, 자동 교체 금지, OCR·가공본이 원본·해시 덮지 않음 | photo/pdf는 저장 키+sha256+mimeType+byteSize로 식별, text는 sourceValue로 식별, temporary에서 원본을 못 찾으면 누락 표시·다른 파일 대체 금지, persistent는 재방문 시 같은 Workspace IndexedDB 원본을 다시 열음. 화면용 object URL은 열람할 때만 만들고 영구 저장 키로 쓰지 않음 |
| ExtractionCandidate | + candidateType, candidateValue, candidateUnit, rawText, confidence, status | candidateValue, confirmedById | 후보=후보, 확인 전 미확정 | |
| ConfirmedValue | + targetType, targetId, fieldPath, confirmedValue(null), confirmedValueUnit, status, source | confirmedValue(상태 따라) | unconfirmed/confirmed/confirmedZero/estimated/missing 분리 | 값·상태·출처 함께 |
| Statement | + statementType, effectiveDate(null), baseHoursMinutes(null), items, statedNetPay(null), internalCalculatedNetPay(null), status | effectiveDate, baseHoursMinutes, statedNetPay | 기재액·내부계산 별도 보존 | 전월/당월 수정본 구분 |
| StatementItem | + itemType, itemName(null), amount(null), amountStatus, hoursMinutes(null), hoursStatus, ratePerHourWon(null), rateStatus, candidateRef(null) | amount, hoursMinutes, ratePerHourWon | 각 필드별 확인 상태 | |
| WorkRecord | + workDate, status, startTimeMinutes(null), endTimeMinutes(null), breakMinutes(null), breakStatus, netWorkMinutes(null), nightFlag(null), recordedAt, gapFlag | startTimeMinutes, endTimeMinutes, breakMinutes, netWorkMinutes | 미기록/확인0분 분리 | 근무일≠작성일 |
| RateCondition | + ratePerHourWon, rateStatus, effectiveDate(null), effectiveEnd(null), source(null), isMinimumWageReference | effectiveDate | 시급 범위·적용일 확인 | 역산 금지 |
| ActualPayment | + jobId, sourceDocumentId(null), paymentChannel, channelStatus, amount(양수만), amountStatus, depositDate(null), depositDateStatus, note(null), duplicateFlag, splitGroup(null) | sourceDocumentId, depositDate, splitGroup, note | 채널별 확인 상태 | 급여기간 직접 링크 없음, 0원 수령은 3.13 kind=zeroReceipt |
| PaymentAllocation | id, workspaceId, revision, createdAt, updatedAt, actualPaymentId, payPeriodId, allocatedAmount, allocationStatus, note(null) | note | confirmed/unconfirmed | 양수 정수, 동일 지급/기간 쌍 하나, 확인 배분 합은 확인 지급액 이하, 미배분은 월 합계 제외 |

| UnreceivedConfirmation | + payPeriodId, jobId, sourceDocumentId(null), kind(unreceived/zeroReceipt), status(active/released), confirmedAt, releasedAt(null), releaseNote(null), history, note(null) | sourceDocumentId, releasedAt, releaseNote, note | active/released + 이력 보존 | 같은 기간 active 최대 1개(kind 무관). 같은 기간 confirmed 배분과만 공존 금지. 실제 지급 기록/다른 기간 배분 허용. 사용자 동의로 active 해제 후 해당 기간 배분 확정 |
| Question | + questionType, title, description, status, statusNote(null), related~Id(null들), closingReason(null), closedAt(null) | 관련 id들, closingReason, closedAt | 상태 전이 규칙 따름 | 기록만 시작 시 자동 생성 금지 |
| FollowUpAnswer | + questionId, answerType, answerContent, relatedStatementId(null), answerDate(null), confirmedById(null), status | relatedStatementId, answerDate, confirmedById | | |
| PaymentPromise | + questionId, promisedAmount(null), promisedDate(null), status, note(null) | promisedAmount, promisedDate | 합산 대상 아님 | |
| CalculationResult | + calculationType, calculationSubtype(null), inputSnapshot, resultValue(null), resultStatus, suspendedReason(null), outOfRangeDetail(null), roundingMethod, related~Id(null들), isDeprecated, deprecatedByRevision(null) | resultValue, 관련 id들 | 세 산술 분리, 보류/범위초과 구분 | |
| Output | + outputType, language, content, version, status, statusNote(null), relatedCalculationId(null), relatedQuestionId(null), isDeprecated, deprecatedByOutputId(null), generatedAt(null) | 관련 id들, generatedAt | 구버전 표시, 생성 대기/실패 분리 | |
| BilingualOutputBundle(선택) | + payPeriodId, bundleVersion, koOutputId, targetLangOutputId, status, isDeprecated, deprecatedByBundleId(null) | deprecatedByBundleId | 양언어 버전 일치 | |

---

문서 버전: 1.0 (이번 작업 설계판)  
근거 파일: `AGENTS.md`, `PRD.md`, `docs/specs/DOMAIN.md`  
범위 밖(다음 작업): 백업 암호화/삭제/멀티탭 세부 절차, 노출 제어 구현, IndexedDB 스키마 정의, 저장 검증 코드.
