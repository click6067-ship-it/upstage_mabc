# -*- coding: utf-8 -*-
"""
입력 가드 (보조). 현재는 서버(server.py)에 검증 로직이 있으므로,
여기는 중복 방지용으로 최소 인터페이스만 둔다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from backend.contracts import ConfirmedMapping, DocumentPayload, Period


def validate_compare_request(req) -> Tuple[bool, List[Dict[str, Any]]]:
    """외부에서 재사용할 수 있는 요청 유효성 검사. 실패 시 (False, fieldErrors)."""
    errors: List[Dict[str, Any]] = []
    if not req.versionKey or len(req.versionKey) > 200:
        errors.append({"field": "versionKey", "code": "INVALID_VERSION_KEY", "messageKey": "INVALID_INPUT"})
    if req.schemaVersion != 1:
        errors.append({"field": "schemaVersion", "code": "UNSUPPORTED_SCHEMA", "messageKey": "INVALID_INPUT"})
    if req.mode != "revision":
        errors.append({"field": "mode", "code": "UNSUPPORTED_MODE", "messageKey": "INVALID_INPUT"})
    if req.payloadBefore is None or req.payloadAfter is None:
        errors.append({"field": "payload", "code": "MISSING_PAGES", "messageKey": "INVALID_INPUT"})
        return False, errors
    if not _payload_ok(req.payloadBefore, errors, "payloadBefore"):
        return False, errors
    if not _payload_ok(req.payloadAfter, errors, "payloadAfter"):
        return False, errors
    if not _mappings_ok(req.payloadBefore, req.payloadAfter, req.confirmedMappings, errors):
        return False, errors
    return True, errors


def _payload_ok(payload: DocumentPayload, errors: List[Dict[str, Any]], prefix: str) -> bool:
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
        if len(sec.items) > 200:
            errors.append({"field": f"{prefix}.sections[].items", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"})
        for item in sec.items:
            if not item.id or len(item.id) > 200:
                errors.append({"field": f"{prefix}.sections[].items[].id", "code": "INVALID_ID", "messageKey": "INVALID_INPUT"})
            if item.position is not None and not (isinstance(item.position, int) and item.position >= 0):
                errors.append({"field": f"{prefix}.sections[].items[].position", "code": "INVALID_POSITION", "messageKey": "INVALID_INPUT"})
            if item.key is not None and len(item.key) > 200:
                errors.append({"field": f"{prefix}.sections[].items[].key", "code": "INVALID_KEY", "messageKey": "INVALID_INPUT"})
            if len(item.sourceRefs) > 50:
                errors.append({"field": f"{prefix}.sections[].items[].sourceRefs", "code": "TOO_LARGE", "messageKey": "TOO_LARGE"})
    return len(errors) == 0


def _period_ymd_ok(p: Period) -> bool:
    if len(p.start) != 10 or len(p.end) != 10:
        return False
    from datetime import date

    try:
        s = date.fromisoformat(p.start)
        e = date.fromisoformat(p.end)
        return s <= e
    except ValueError:
        return False


def _mappings_ok(
    before: DocumentPayload,
    after: DocumentPayload,
    mappings: List[ConfirmedMapping],
    errors: List[Dict[str, Any]],
) -> bool:
    before_ids = _all_item_ids(before)
    after_ids = _all_item_ids(after)
    seen_before: Dict[str, str] = {}
    seen_after: Dict[str, str] = {}
    for m in mappings:
        if m.beforeItemId == m.afterItemId:
            errors.append({"field": "confirmedMappings", "code": "INVALID_MAPPING", "messageKey": "INVALID_INPUT"})
            continue
        if m.beforeItemId in seen_before or m.afterItemId in seen_after:
            errors.append({"field": "confirmedMappings", "code": "DUPLICATE_MAPPING", "messageKey": "INVALID_INPUT"})
            continue
        if m.beforeItemId not in before_ids:
            errors.append({"field": "confirmedMappings", "code": "UNKNOWN_ID", "messageKey": "INVALID_INPUT"})
            continue
        if m.afterItemId not in after_ids:
            errors.append({"field": "confirmedMappings", "code": "UNKNOWN_ID", "messageKey": "INVALID_INPUT"})
            continue
        seen_before[m.beforeItemId] = m.afterItemId
        seen_after[m.afterItemId] = m.beforeItemId
    return len(errors) == 0


def _all_item_ids(payload: DocumentPayload) -> List[str]:
    ids = []
    for sec in payload.sections:
        for item in sec.items:
            ids.append(item.id)
    return ids
