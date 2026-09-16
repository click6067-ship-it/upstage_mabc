import json, os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.contracts import ExplainRequest, ExplainErrorBody, ErrorDetail
from backend.explanation import (
    build_explain_payload,
    parse_explain_response,
    _MAX_CONTEXT_BYTES,
    _USER_PROMPT_TEMPLATE,
)
from backend.providers.solar import call as solar_call, SolarError, _REQUEST_TIMEOUT_SEC


def _uuid_format(v: str) -> bool:
    from uuid import UUID

    try:
        UUID(v)
        return True
    except Exception:
        return False


async def handler(request):
    try:
        body_bytes = await request.body()
    except Exception:
        body_bytes = b''

    if len(body_bytes) > 65536:
        return _too_large_response("00000000-0000-0000-0000-000000000000")

    try:
        req = ExplainRequest.model_validate_json(body_bytes)
    except Exception as exc:
        errors: list[dict] = []
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

        return _error_response("00000000-0000-0000-0000-000000000000", "INVALID_INPUT", "INVALID_INPUT", errors)

    if not _uuid_format(req.requestId):
        return _error_response(
            req.requestId,
            "INVALID_INPUT",
            "INVALID_INPUT",
            [{"field": "requestId", "code": "INVALID_UUID", "messageKey": "INVALID_INPUT"}],
        )

    if req.maxItems > 100:
        return _error_response(
            req.requestId,
            "TOO_LARGE",
            "TOO_LARGE",
            [{"field": "maxItems", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"}],
        )

    items_and_limit = (req.items, req.maxItems)

    paid_features_enabled = os.environ.get("PAID_FEATURES_ENABLED", "0").strip().lower() in ("1", "true", "yes")
    if not paid_features_enabled:
        return _explain_success_response(
            req.requestId,
            req.versionKey,
            ["현재 설명 기능이 준비되지 않았습니다. 나중에 다시 시도해 주세요."],
            [],
        )

    try:
        payload = build_explain_payload(*items_and_limit, max_bytes=_MAX_CONTEXT_BYTES)
        solar_result = solar_call(payload, timeout_sec=_REQUEST_TIMEOUT_SEC)
    except SolarError as exc:
        return _explain_error_response(req.requestId, req.versionKey, exc.message, exc.retryable)
    except Exception:
        return _explain_error_response(req.requestId, req.versionKey, "설명 요청 중 예기치 않은 오류가 발생했습니다.", True)

    try:
        parsed = parse_explain_response(solar_result["content"])
    except Exception:
        return _explain_error_response(req.requestId, req.versionKey, "설명 응답을 해석하지 못했습니다.", True)

    if not parsed["explanations"] and not parsed["questions"]:
        return _explain_error_response(req.requestId, req.versionKey, "설명 응답을 해석하지 못했습니다.", True)

    return _explain_success_response(req.requestId, req.versionKey, parsed["explanations"], parsed["questions"])


def _error_response(request_id: str, code: str, messageKey: str, fieldErrors: list[dict]):
    return (
        400,
        {"Content-Type": "application/json", "Cache-Control": "no-store"},
        json.dumps(
            ExplainErrorBody(
                requestId=request_id,
                error=ErrorDetail(
                    code=code, messageKey=messageKey, retryable=False, fieldErrors=fieldErrors
                ),
            ).model_dump()
        ),
    )


def _too_large_response(request_id: str):
    return (
        413,
        {"Content-Type": "application/json", "Cache-Control": "no-store"},
        json.dumps(
            ExplainErrorBody(
                requestId=request_id,
                error=ErrorDetail(
                    code="TOO_LARGE",
                    messageKey="TOO_LARGE",
                    retryable=False,
                    fieldErrors=[{"field": "payload", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"}],
                ),
            ).model_dump()
        ),
    )


def _explain_success_response(request_id: str, version_key: str, explanations: list[str], questions: list[str]):
    return (
        200,
        {"Content-Type": "application/json", "Cache-Control": "no-store"},
        json.dumps(
            {
                "requestId": request_id,
                "versionKey": version_key,
                "explanations": explanations,
                "questions": questions,
                "error": None,
            }
        ),
    )


def _explain_error_response(request_id: str, version_key: str, message: str, retryable: bool):
    return (
        200,
        {"Content-Type": "application/json", "Cache-Control": "no-store"},
        json.dumps(
            {
                "requestId": request_id,
                "versionKey": version_key,
                "explanations": [],
                "questions": [],
                "error": {"message": message, "retryable": retryable},
            }
        ),
    )
