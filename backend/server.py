# -*- coding: utf-8 -*-
"""
FastAPI 백엔드 (백엔드 전용).

- GET /api/health
- POST /api/compare (before/after 각각의 payload + confirmedMappings)
- 요청 본문/결과/키/개인정보는 로그에 남기지 않는다.
- 사용자 입력은 파일 경로/URL/셸 실행으로 쓰지 않는다.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Sequence

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.contracts import (
    CompareRequest,
    CompareResultData,
    ErrorBody,
    ErrorDetail,
    HealthResponse,
    ExplainRequest,
    ExplainErrorBody,
)
from backend.doc_compare.adapter import compare_documents
from backend.explanation import (
    build_explain_payload,
    parse_explain_response,
    _MAX_CONTEXT_BYTES,
    _USER_PROMPT_TEMPLATE,
)
from backend.providers.solar import (
    call as solar_call,
    SolarError,
    _REQUEST_TIMEOUT_SEC,
)
from backend.upload_api import router as parse_upload_router

logger = logging.getLogger("doc-compare-api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="doc-compare-api", version="1.0.0")

app.include_router(parse_upload_router)

@app.middleware("http")
async def _no_store(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


ENGINE_VERSION = "1.0.0"
BUILD_ID = "dev"


@app.get("/api/health")
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        buildId=BUILD_ID,
        engineVersion=ENGINE_VERSION,
        paidFeaturesEnabled=False,
    )


@app.post("/api/compare")
async def compare(request: Request) -> JSONResponse:
    # 요청 본문 크기 제한 (실제 읽은 바이트 기준, Content-Length만 믿지 않음)
    try:
        body_bytes = await request.body()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=ErrorBody(
                requestId="00000000-0000-0000-0000-000000000000",
                error=ErrorDetail(code="INVALID_INPUT", messageKey="INVALID_INPUT", retryable=False),
            ).model_dump(),
        )
    if len(body_bytes) > 524288:
        return _too_large_response(
            "00000000-0000-0000-0000-000000000000",
            {"field": "payload", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"},
        )

    # 파싱 / 기본 검증
    try:
        req = CompareRequest.model_validate_json(body_bytes)
    except ValidationError as exc:
        field_errors: list[Dict[str, Any]] = []
        for err in exc.errors():
            field = ".".join(str(p) for p in err["loc"]) if err["loc"] else "request"
            field_errors.append({"field": field, "code": "VALIDATION_ERROR", "messageKey": "INVALID_INPUT"})
        return JSONResponse(
            status_code=400,
            content=ErrorBody(
                requestId="00000000-0000-0000-0000-000000000000",
                error=ErrorDetail(
                    code="INVALID_INPUT",
                    messageKey="INVALID_INPUT",
                    retryable=False,
                    fieldErrors=field_errors,
                ),
            ).model_dump(),
        )

    # 가드: requestId / mode / payloadBefore/After / 매핑
    guard_err = _guard_compare(req)
    if guard_err is not None:
        return _error_response(req.requestId, guard_err)

    # 집합 크기/문자열 상한 검사 (요청 본문 크기 제한과 별개로, 내용 기준 413)
    limit_err = _payload_limit_ok(req.payload.before, req.payload.after)
    if limit_err is not None:
        return _too_large_response(req.requestId, limit_err)

    # 같은 일자리/기간 검증 (이 구현에서는 before/after가 다르면 거절)
    same_emp, same_period, guard_errors = _same_employment_and_period(
        req.payload.before, req.payload.after
    )
    if not same_emp or not same_period:
        return _error_response(
            req.requestId,
            ErrorDetail(
                code="INVALID_INPUT",
                messageKey="INVALID_INPUT",
                retryable=False,
                fieldErrors=guard_errors,
            ),
        )

    # 실제 비교 수행
    try:
        result = compare_documents(req.payload.before, req.payload.after, req.payload.confirmedMappings)
    except ValueError:
        return _error_response(
            req.requestId,
            ErrorDetail(
                code="INVALID_INPUT",
                messageKey="INVALID_INPUT",
                retryable=False,
                fieldErrors=[{"field": "payload", "code": "UNSUPPORTED_CASE", "messageKey": "INVALID_INPUT"}],
            ),
        )

    # 성공 응답
    return JSONResponse(
        status_code=200,
        content={
            "requestId": req.requestId,
            "versionKey": req.versionKey,
            "engineVersion": ENGINE_VERSION,
            "data": result.model_dump(),
            "warnings": result.warnings or [],
        },
    )


@app.post("/api/explain")
async def explain(request: Request) -> JSONResponse:
    """POST /api/explain — Solar 설명/질문 생성 엔드포인트.

    - UPSTAGE_API_KEY 환경변수만 사용. 키 원문·본문·응답은 로그/저장하지 않는다.
    - 요청 본문 최대 64 KiB. 초과 시 413/TOO_LARGE.
    - PAID_FEATURES_ENABLED는 기본 OFF 유지. 계정권한/호출상한이 주입돼 있으면 합성자료 1회만 실호출.
    - 다른 모델 폴백 없음.
    - 호출 실패 시 기존 비교 결과는 남기고 이유를 짧게 표시한다.
    """
    # 요청 본문 크기 제한
    try:
        body_bytes = await request.body()
    except Exception:
        return _error_response("00000000-0000-0000-0000-000000000000", ErrorDetail(
            code="INVALID_INPUT",
            messageKey="INVALID_INPUT",
            retryable=False,
        ))

    if len(body_bytes) > 65536:
        return _too_large_response("00000000-0000-0000-0000-000000000000", {
            "field": "payload",
            "code": "TOO_LARGE",
            "messageKey": "TOO_LARGE",
        })

    # 파싱 / 기본 검증
    try:
        req = ExplainRequest.model_validate_json(body_bytes)
    except ValidationError as exc:
        field_errors: list[Dict[str, Any]] = []
        for err in exc.errors():
            field = ".".join(str(p) for p in err["loc"]) if err["loc"] else "request"
            field_errors.append({"field": field, "code": "VALIDATION_ERROR", "messageKey": "INVALID_INPUT"})
        return JSONResponse(
            status_code=400,
            content=ExplainErrorBody(
                requestId="00000000-0000-0000-0000-000000000000",
                error=ErrorDetail(
                    code="INVALID_INPUT",
                    messageKey="INVALID_INPUT",
                    retryable=False,
                    fieldErrors=field_errors,
                ),
            ).model_dump(),
        )

    # 가드: requestId 유효성
    if not _uuid_format(req.requestId):
        return _error_response(req.requestId, ErrorDetail(
            code="INVALID_INPUT",
            messageKey="INVALID_INPUT",
            retryable=False,
            fieldErrors=[{"field": "requestId", "code": "INVALID_UUID", "messageKey": "INVALID_INPUT"}],
        ))

    # 항목 수 제한: maxItems 범위 내인지 확인
    if req.maxItems > 100:
        return _error_response(req.requestId, ErrorDetail(
            code="TOO_LARGE",
            messageKey="TOO_LARGE",
            retryable=False,
            fieldErrors=[{"field": "maxItems", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"}],
        ))

    # 요청 크기 초과: 실제 보낼 항목 텍스트를 미리 계산해 크기 제한
    items_text = _build_item_text_for_explain(req.items, req.maxItems)
    request_context = _USER_PROMPT_TEMPLATE.format(items=items_text)
    if len(request_context.encode("utf-8")) > _MAX_CONTEXT_BYTES:
        # 항목 수를 줄여 다시 시도
        reduced_max = max(1, req.maxItems // 2)
        items_text = _build_item_text_for_explain(req.items, reduced_max)
        request_context = _USER_PROMPT_TEMPLATE.format(items=items_text)
        if len(request_context.encode("utf-8")) > _MAX_CONTEXT_BYTES:
            return _error_response(req.requestId, ErrorDetail(
                code="TOO_LARGE",
                messageKey="TOO_LARGE",
                retryable=False,
                fieldErrors=[{"field": "items", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"}],
            ))

    # Solar 호출 준비 확인
    paid_features_enabled = os.environ.get("PAID_FEATURES_ENABLED", "0").strip().lower() in ("1", "true", "yes")
    if not paid_features_enabled:
        # 기본 OFF: mock/합성 응답만 반환
        return _explain_success_response(req.requestId, req.versionKey, [
            "현재 설명 기능이 준비되지 않았습니다. 나중에 다시 시도해 주세요.",
        ], [])

    # 실제 Solar 호출
    try:
        payload = build_explain_payload(req.items, max_items=req.maxItems, max_bytes=_MAX_CONTEXT_BYTES)
        solar_result = solar_call(payload, timeout_sec=_REQUEST_TIMEOUT_SEC)
    except SolarError as exc:
        logger.warning("solar 호출 실패: %s, retryable=%s", exc.message, exc.retryable)
        return _explain_error_response(req.requestId, req.versionKey, exc.message, exc.retryable)
    except Exception as exc:
        logger.warning("solar 호출 중 예기치 않은 오류: %s", type(exc).__name__)
        return _explain_error_response(req.requestId, req.versionKey, "설명 요청 중 예기치 않은 오류가 발생했습니다.", True)

    # 응답 파싱
    try:
        parsed = parse_explain_response(solar_result["content"])
    except Exception as exc:
        logger.warning("solar 응답 파싱 실패: %s", type(exc).__name__)
        return _explain_error_response(req.requestId, req.versionKey, "설명 응답을 해석하지 못했습니다.", True)

    if not parsed["explanations"] and not parsed["questions"]:
        return _explain_error_response(req.requestId, req.versionKey, "설명 응답을 해석하지 못했습니다.", True)

    return _explain_success_response(
        req.requestId,
        req.versionKey,
        parsed["explanations"],
        parsed["questions"],
    )


def _build_item_text_for_explain(items: List[Dict[str, Any]], max_items: int) -> str:
    """Solar 프롬프트에 넣을 항목 텍스트를 만든다."""
    lines = []
    shown = 0
    for ic in items:
        if shown >= max_items:
            lines.append(f"  ... (최대 {max_items}개 항목까지만 표시한다)")
            break
        before_id = ic.get("beforeItemId") or ""
        after_id = ic.get("afterItemId") or ""
        label = ic.get("label") or ""
        kind = ic.get("contentKind", "unknown")
        moved = ic.get("moved", False)
        changed = ic.get("changedFields") or []
        b_amount = ic.get("beforeAmount")
        if b_amount is None:
            bf = ic.get("beforeFields")
            b_amount = bf.get("amountKrw") if isinstance(bf, dict) else None
        a_amount = ic.get("afterAmount")
        if a_amount is None:
            af = ic.get("afterFields")
            a_amount = af.get("amountKrw") if isinstance(af, dict) else None

        label_parts = []
        if label:
            label_parts.append(f"항목명={label}")
        if before_id and after_id:
            label_parts.append(f"항목ID 기존={before_id} → 정정={after_id}")
        elif before_id:
            label_parts.append(f"항목ID 기존={before_id}")
        elif after_id:
            label_parts.append(f"항목ID 정정={after_id}")

        if kind:
            label_parts.append(f"종류={kind}")
        if moved:
            label_parts.append("위치이동")
        if changed:
            label_parts.append(f"바뀐필드={','.join(changed)}")

        line = "  - " + " | ".join(label_parts)
        if b_amount is not None or a_amount is not None:
            b_str = f"{b_amount}원" if b_amount is not None else "금액 없음"
            a_str = f"{a_amount}원" if a_amount is not None else "금액 없음"
            line += f"\n    금액: 기존 {b_str} → 정정 {a_str}"
        else:
            line += "\n    금액: 둘 다 없음"
        lines.append(line)
        shown += 1
    return "\n".join(lines)


def _explain_success_response(request_id: str, version_key: str, explanations: List[str], questions: List[str]) -> JSONResponse:
    """Solar 설명/질문 성공 응답."""
    return JSONResponse(
        status_code=200,
        content={
            "requestId": request_id,
            "versionKey": version_key,
            "explanations": explanations,
            "questions": questions,
            "error": None,
        },
    )


def _explain_error_response(request_id: str, version_key: str, message: str, retryable: bool) -> JSONResponse:
    """Solar 설명/질문 오류 응답."""
    return JSONResponse(
        status_code=200,
        content={
            "requestId": request_id,
            "versionKey": version_key,
            "explanations": [],
            "questions": [],
            "error": {"message": message, "retryable": retryable},
        },
    )


# ---------------------------------------------------------------------------
# 가드 헬퍼
# ---------------------------------------------------------------------------

def _guard_compare(req: CompareRequest) -> ErrorDetail | None:
    errors: list[Dict[str, Any]] = []

    if not _uuid_format(req.requestId):
        errors.append({"field": "requestId", "code": "INVALID_UUID", "messageKey": "INVALID_INPUT"})

    if not req.versionKey or len(req.versionKey) > 200:
        errors.append({"field": "versionKey", "code": "INVALID_VERSION_KEY", "messageKey": "INVALID_INPUT"})

    if req.schemaVersion != 1:
        errors.append({"field": "schemaVersion", "code": "UNSUPPORTED_SCHEMA", "messageKey": "INVALID_INPUT"})

    if req.payload.mode != "revision":
        errors.append({"field": "payload.mode", "code": "UNSUPPORTED_MODE", "messageKey": "INVALID_INPUT"})

    if req.payload.before is None or req.payload.after is None:
        errors.append({"field": "payload", "code": "MISSING_PAGES", "messageKey": "INVALID_INPUT"})
        if errors:
            return ErrorDetail(code="INVALID_INPUT", messageKey="INVALID_INPUT", retryable=False, fieldErrors=errors)

    if not _payload_ok(req.payload.before, errors, prefix="payload.before"):
        return ErrorDetail(code="INVALID_INPUT", messageKey="INVALID_INPUT", retryable=False, fieldErrors=errors)

    if not _payload_ok(req.payload.after, errors, prefix="payload.after"):
        return ErrorDetail(code="INVALID_INPUT", messageKey="INVALID_INPUT", retryable=False, fieldErrors=errors)

    if not _mappings_ok(req.payload.before, req.payload.after, req.payload.confirmedMappings, errors):
        return ErrorDetail(code="INVALID_INPUT", messageKey="INVALID_INPUT", retryable=False, fieldErrors=errors)

    if errors:
        return ErrorDetail(code="INVALID_INPUT", messageKey="INVALID_INPUT", retryable=False, fieldErrors=errors)
    return None


def _payload_limit_ok(before, after):
    """요청 내용 기준 상한 검사.

    - before/after 각각 모든 섹션 합쳐 항목 200개 이하
    - item.label, fields.text 각각 최대 2000자
    - 위반 시 413/TOO_LARGE용 fieldErrors 항목을 반환한다.
    """
    err: Dict[str, Any] | None = None

    before_count = _count_items(before)
    if before_count > 200:
        err = {"field": "payload.before", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"}

    after_count = _count_items(after)
    if after_count > 200:
        err = {"field": "payload.after", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"}

    if err is not None:
        return err

    if _any_label_text_too_long(before, prefix="payload.before"):
        return {"field": "payload.before", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"}
    if _any_label_text_too_long(after, prefix="payload.after"):
        return {"field": "payload.after", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"}

    return None


def _count_items(payload) -> int:
    if payload is None:
        return 0
    n = 0
    for sec in payload.sections:
        n += len(sec.items)
    return n


def _any_label_text_too_long(payload, prefix: str) -> bool:
    if payload is None:
        return False
    for sec in payload.sections:
        for item in sec.items:
            if item.label is not None and len(item.label) > 2000:
                return True
            if item.fields is not None and item.fields.text is not None and len(item.fields.text) > 2000:
                return True
    return False


def _uuid_format(v: str) -> bool:
    from uuid import UUID

    try:
        UUID(v)
        return True
    except Exception:
        return False


def _payload_ok(payload, errors, prefix):
    if not payload.documentId or len(payload.documentId) > 200:
        errors.append({"field": f"{prefix}.documentId", "code": "INVALID_ID", "messageKey": "INVALID_INPUT"})
    if not payload.employmentKey or len(payload.employmentKey) > 200:
        errors.append({"field": f"{prefix}.employmentKey", "code": "INVALID_ID", "messageKey": "INVALID_INPUT"})
    if not _period_ymd_ok(payload.period):
        errors.append({"field": f"{prefix}.period", "code": "INVALID_PERIOD", "messageKey": "INVALID_INPUT"})
    if not payload.revisionKey or len(payload.revisionKey) > 200:
        errors.append({"field": f"{prefix}.revisionKey", "code": "INVALID_ID", "messageKey": "INVALID_INPUT"})
    if len(payload.sections) > 100:
        errors.append({"field": f"{prefix}.sections", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"})
    for sec in payload.sections:
        if not sec.key or len(sec.key) > 200:
            errors.append({"field": f"{prefix}.sections[].key", "code": "INVALID_KEY", "messageKey": "INVALID_INPUT"})
        for item in sec.items:
            if not item.id or len(item.id) > 200:
                errors.append({"field": f"{prefix}.sections[].items[].id", "code": "INVALID_ID", "messageKey": "INVALID_INPUT"})
            if item.position is not None and (not isinstance(item.position, int) or item.position < 0):
                errors.append({"field": f"{prefix}.sections[].items[].position", "code": "INVALID_POSITION", "messageKey": "INVALID_INPUT"})
            if item.key is not None and len(item.key) > 200:
                errors.append({"field": f"{prefix}.sections[].items[].key", "code": "INVALID_KEY", "messageKey": "INVALID_INPUT"})
            if len(item.sourceRefs) > 50:
                errors.append({"field": f"{prefix}.sections[].items[].sourceRefs", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"})
            for idx, sr in enumerate(item.sourceRefs):
                _check_source_ref(errors, f"{prefix}.sections[].items[].sourceRefs[{idx}]", sr)
    return len(errors) == 0


def _check_source_ref(errors: list[Dict[str, Any]], prefix: str, sr):
    # Pydantic 파싱 결과(BaseModel)와 직접 dict 입력 양쪽을 수용
    if isinstance(sr, dict):
        sr_dict = sr
        sr_model = None
    else:
        try:
            sr_dict = sr.model_dump()
            sr_model = sr
        except Exception:
            errors.append({"field": prefix, "code": "INVALID_SOURCE_REF", "messageKey": "INVALID_INPUT"})
            return
    sourceId = sr_dict.get("sourceId")
    if not isinstance(sourceId, str) or not sourceId.strip():
        errors.append({"field": f"{prefix}.sourceId", "code": "SOURCE_ID_REQUIRED", "messageKey": "INVALID_INPUT"})
    locator = sr_dict.get("locator")
    if locator is None:
        if isinstance(sr, dict) and "locator" in sr:
            errors.append({"field": f"{prefix}.locator", "code": "INVALID_LOCATOR", "messageKey": "INVALID_INPUT"})
        return
    if not isinstance(locator, dict):
        errors.append({"field": f"{prefix}.locator", "code": "INVALID_LOCATOR", "messageKey": "INVALID_INPUT"})
        return
    page = locator.get("page")
    if page is not None and (not isinstance(page, int) or page < 1):
        errors.append({"field": f"{prefix}.locator.page", "code": "PAGE_INVALID", "messageKey": "INVALID_INPUT"})
    itemId = locator.get("itemId")
    if itemId is not None and (not isinstance(itemId, str) or not itemId.strip()):
        errors.append({"field": f"{prefix}.locator.itemId", "code": "ITEM_ID_INVALID", "messageKey": "INVALID_INPUT"})
    excerpt = locator.get("excerpt")
    if excerpt is not None:
        if not isinstance(excerpt, str):
            errors.append({"field": f"{prefix}.locator.excerpt", "code": "EXCERPT_INVALID", "messageKey": "INVALID_INPUT"})
        elif len(excerpt) > 500:
            errors.append({"field": f"{prefix}.locator.excerpt", "code": "EXCERPT_TOO_LONG", "messageKey": "INVALID_INPUT"})


def _period_ymd_ok(period) -> bool:
    if len(period.start) != 10 or len(period.end) != 10:
        return False
    from datetime import date

    try:
        s = date.fromisoformat(period.start)
        e = date.fromisoformat(period.end)
        return s <= e
    except ValueError:
        return False


def _mappings_ok(before, after, mappings, errors):
    before_ids = _all_item_ids(before)
    after_ids = _all_item_ids(after)
    seen_before = {}
    seen_after = {}
    for m in mappings:
        if m.beforeItemId == m.afterItemId:
            errors.append({"field": "confirmedMappings", "code": "INVALID_MAPPING", "messageKey": "INVALID_INPUT"})
            continue
        if m.beforeItemId in seen_before or m.afterItemId in seen_after:
            errors.append({"field": "confirmedMappings", "code": "DUPLICATE_MAPPING", "messageKey": "INVALID_INPUT"})
            continue
        if m.beforeItemId not in before_ids:
            errors.append({"field": "confirmedMappings", "code": "UNKNOWN_BEFORE_ID", "messageKey": "INVALID_INPUT"})
            continue
        if m.afterItemId not in after_ids:
            errors.append({"field": "confirmedMappings", "code": "UNKNOWN_AFTER_ID", "messageKey": "INVALID_INPUT"})
            continue
        seen_before[m.beforeItemId] = m.afterItemId
        seen_after[m.afterItemId] = m.beforeItemId
    return len(errors) == 0


def _all_item_ids(payload):
    ids = []
    for sec in payload.sections:
        for item in sec.items:
            ids.append(item.id)
    return ids


def _same_employment_and_period(before, after):
    errors = []
    same_emp = before.employmentKey == after.employmentKey
    same_period = before.period.start == after.period.start and before.period.end == after.period.end
    if not same_emp:
        errors.append({"field": "payloadBefore.employmentKey", "code": "DIFFERENT_EMPLOYMENT", "messageKey": "INVALID_INPUT"})
    if not same_period:
        errors.append({"field": "payloadBefore.period", "code": "DIFFERENT_PERIOD", "messageKey": "INVALID_INPUT"})
    return same_emp, same_period, errors


def _too_large_response(request_id, detail=None):
    return JSONResponse(
        status_code=413,
        content=ErrorBody(
            requestId=request_id,
            error=ErrorDetail(
                code="TOO_LARGE",
                messageKey="TOO_LARGE",
                retryable=False,
                fieldErrors=[] if detail is None else [detail],
            ),
        ).model_dump(),
    )


def _error_response(request_id, detail):
    return JSONResponse(
        status_code=400,
        content=ErrorBody(
            requestId=request_id,
            error=detail,
        ).model_dump(),
    )
