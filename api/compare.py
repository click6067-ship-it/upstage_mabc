import json, sys, os
from uuid import UUID

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.contracts import (
    CompareRequest,
    ErrorBody,
    ErrorDetail,
)
from backend.doc_compare.adapter import compare_documents


def _uuid_format(v: str) -> bool:
    try:
        UUID(v)
        return True
    except Exception:
        return False


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


async def handler(request):
    try:
        body_bytes = await request.body()
    except Exception:
        body_bytes = b''

    if len(body_bytes) > 524288:
        return _too_large_response(
            "00000000-0000-0000-0000-000000000000",
            {"field": "payload", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"},
        )

    try:
        req = CompareRequest.model_validate_json(body_bytes)
    except Exception as exc:
        errors = []
        try:
            from pydantic import ValidationError

            if isinstance(exc, ValidationError):
                for err in exc.errors():
                    field = ".".join(str(p) for p in err["loc"]) if err["loc"] else "request"
                    errors.append(
                        {"field": field, "code": "VALIDATION_ERROR", "messageKey": "INVALID_INPUT"}
                    )
        except Exception:
            errors.append({"field": "request", "code": "VALIDATION_ERROR", "messageKey": "INVALID_INPUT"})

        rid = req.requestId if hasattr(req, "requestId") and _uuid_format(req.requestId) else "00000000-0000-0000-0000-000000000000"
        return _json_error_response(rid, "INVALID_INPUT", "INVALID_INPUT", errors)

    guard_err = _guard_compare(req)
    if guard_err is not None:
        return _json_error_response(req.requestId, guard_err.code, guard_err.messageKey, guard_err.fieldErrors)

    limit_err = _payload_limit_ok(req.payload.before, req.payload.after)
    if limit_err is not None:
        return _too_large_response(req.requestId, limit_err)

    same_emp, same_period, guard_errors = _same_employment_and_period(
        req.payload.before, req.payload.after
    )
    if not same_emp or not same_period:
        return _json_error_response(
            req.requestId,
            "INVALID_INPUT",
            "INVALID_INPUT",
            guard_errors,
        )

    try:
        result = compare_documents(
            req.payload.before, req.payload.after, req.payload.confirmedMappings
        )
    except ValueError:
        return _json_error_response(
            req.requestId,
            "INVALID_INPUT",
            "INVALID_INPUT",
            [{"field": "payload", "code": "UNSUPPORTED_CASE", "messageKey": "INVALID_INPUT"}],
        )

    return _json_success_response(req, result)


def _guard_compare(req) -> ErrorDetail | None:
    errors: list[dict] = []

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
        return ErrorDetail(
            code="INVALID_INPUT", messageKey="INVALID_INPUT", retryable=False, fieldErrors=errors
        )

    if not _payload_ok(req.payload.before, errors, prefix="payload.before"):
        return ErrorDetail(
            code="INVALID_INPUT", messageKey="INVALID_INPUT", retryable=False, fieldErrors=errors
        )

    if not _payload_ok(req.payload.after, errors, prefix="payload.after"):
        return ErrorDetail(
            code="INVALID_INPUT", messageKey="INVALID_INPUT", retryable=False, fieldErrors=errors
        )

    if not _mappings_ok(req.payload.before, req.payload.after, req.payload.confirmedMappings, errors):
        return ErrorDetail(
            code="INVALID_INPUT", messageKey="INVALID_INPUT", retryable=False, fieldErrors=errors
        )

    if errors:
        return ErrorDetail(
            code="INVALID_INPUT", messageKey="INVALID_INPUT", retryable=False, fieldErrors=errors
        )
    return None


def _payload_limit_ok(before, after):
    before_count = _count_items(before)
    if before_count > 200:
        return {"field": "payload.before", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"}

    after_count = _count_items(after)
    if after_count > 200:
        return {"field": "payload.after", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"}

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


def _payload_ok(payload, errors, prefix):
    if not payload.documentId or len(payload.documentId) > 200:
        errors.append({"field": f"{prefix}.documentId", "code": "INVALID_ID", "messageKey": "INVALID_INPUT"})
    if not payload.employmentKey or len(payload.employmentKey) > 200:
        errors.append(
            {"field": f"{prefix}.employmentKey", "code": "INVALID_ID", "messageKey": "INVALID_INPUT"}
        )
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
                errors.append(
                    {"field": f"{prefix}.sections[].items[].id", "code": "INVALID_ID", "messageKey": "INVALID_INPUT"}
                )
            if item.position is not None and (not isinstance(item.position, int) or item.position < 0):
                errors.append(
                    {
                        "field": f"{prefix}.sections[].items[].position",
                        "code": "INVALID_POSITION",
                        "messageKey": "INVALID_INPUT",
                    }
                )
            if item.key is not None and len(item.key) > 200:
                errors.append(
                    {"field": f"{prefix}.sections[].items[].key", "code": "INVALID_KEY", "messageKey": "INVALID_INPUT"}
                )
            if len(item.sourceRefs) > 50:
                errors.append(
                    {
                        "field": f"{prefix}.sections[].items[].sourceRefs",
                        "code": "TOO_LARGE",
                        "messageKey": "INVALID_INPUT",
                    }
                )
    return len(errors) == 0


def _mappings_ok(before, after, mappings, errors):
    before_ids = _all_item_ids(before)
    after_ids = _all_item_ids(after)
    seen_before: dict[str, str] = {}
    seen_after: dict[str, str] = {}
    for m in mappings:
        if m.beforeItemId == m.afterItemId:
            errors.append({"field": "confirmedMappings", "code": "INVALID_MAPPING", "messageKey": "INVALID_INPUT"})
            continue
        if m.beforeItemId in seen_before or m.afterItemId in seen_after:
            errors.append(
                {"field": "confirmedMappings", "code": "DUPLICATE_MAPPING", "messageKey": "INVALID_INPUT"}
            )
            continue
        if m.beforeItemId not in before_ids:
            errors.append(
                {"field": "confirmedMappings", "code": "UNKNOWN_BEFORE_ID", "messageKey": "INVALID_INPUT"}
            )
            continue
        if m.afterItemId not in after_ids:
            errors.append(
                {"field": "confirmedMappings", "code": "UNKNOWN_AFTER_ID", "messageKey": "INVALID_INPUT"}
            )
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
        errors.append(
            {"field": "payloadBefore.employmentKey", "code": "DIFFERENT_EMPLOYMENT", "messageKey": "INVALID_INPUT"}
        )
    if not same_period:
        errors.append(
            {"field": "payloadBefore.period", "code": "DIFFERENT_PERIOD", "messageKey": "INVALID_INPUT"}
        )
    return same_emp, same_period, errors


def _json_error_response(request_id: str, code: str, messageKey: str, fieldErrors: list[dict]):
    return (
        json.dumps(
            ErrorBody(
                requestId=request_id,
                error=ErrorDetail(
                    code=code, messageKey=messageKey, retryable=False, fieldErrors=fieldErrors
                ),
            ).model_dump(),
            ensure_ascii=False,
        ),
        400,
        {"Content-Type": "application/json", "Cache-Control": "no-store"},
    )


def _json_success_response(req: CompareRequest, result) -> tuple[str, int, dict]:
    return (
        json.dumps(
            {
                "requestId": req.requestId,
                "versionKey": req.versionKey,
                "engineVersion": "1.0.0",
                "data": result.model_dump(),
                "warnings": result.warnings or [],
            },
            ensure_ascii=False,
        ),
        200,
        {"Content-Type": "application/json", "Cache-Control": "no-store"},
    )


def _too_large_response(request_id: str, detail: dict | None = None):
    return (
        json.dumps(
            ErrorBody(
                requestId=request_id,
                error=ErrorDetail(
                    code="TOO_LARGE",
                    messageKey="TOO_LARGE",
                    retryable=False,
                    fieldErrors=[] if detail is None else [detail],
                ),
            ).model_dump(),
            ensure_ascii=False,
        ),
        413,
        {"Content-Type": "application/json", "Cache-Control": "no-store"},
    )
