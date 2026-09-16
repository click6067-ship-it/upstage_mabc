# -*- coding: utf-8 -*-
"""
Solar Pro4 HTTP 공급자.

- API: https://api.upstage.ai/v1/chat/completions
- 모델: solar-pro4
- 서버 환경변수 UPSTAGE_API_KEY만 사용. 키 원문은 로그/저장하지 않는다.
- 요청/응답 본문은 저장하지 않는다. no-store 적용.
- timeout, 중복 클릭 방지, 새 비교 시 이전 설명 무효화, 늦은 응답 무시를 지원한다.
- 외부 SDK 없이 Python 표준 라이브러리(urllib)만 사용한다.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("doc-compare-solar")

API_URL = "https://api.upstage.ai/v1/chat/completions"
_REQUEST_TIMEOUT_SEC = 30
_DEFAULT_MODEL = "solar-pro4"


class SolarError(Exception):
    """Solar 호출 실패."""

    def __init__(self, message: str, retryable: bool = True, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.retryable = retryable


def _has_api_key() -> bool:
    """ UPSTAGE_API_KEY 환경변수가 비어 있지 않은지 확인한다. 키 원문은 반환/출력하지 않는다."""
    v = os.environ.get("UPSTAGE_API_KEY")
    return bool(v and v.strip())


def _api_key() -> str:
    """호출용 키를 반환한다. 환경변수가 비어 있으면 빈 문자열을 반환한다."""
    v = os.environ.get("UPSTAGE_API_KEY", "")
    return v.strip()


def _build_request_payload(payload: Dict[str, Any]) -> bytes:
    """요청 본문을 JSON으로 직렬화한다. 키나 원문을 포함한 로그/저장은 하지 않는다."""
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def call(
    payload: Dict[str, Any],
    timeout_sec: int = _REQUEST_TIMEOUT_SEC,
    model_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Solar 채팅 completions를 호출한다.

    - UPSTAGE_API_KEY가 비어 있으면 호출하지 않고 SolarError를 즉시 반환한다.
    - 타임아웃, HTTP 오류, 잘못된 응답을 처리한다.
    - 응답 본문은 호출부만 잠깐 해석하고 버린다. 저장하지 않는다.
    - 중복 호출 방지/무효화는 호출부(state router)에서 담당한다.
    """
    api_key = _api_key()
    if not api_key:
        raise SolarError(
            "UPSTAGE_API_KEY가 설정되지 않아 Solar를 호출하지 않았다.",
            retryable=False,
            detail={"code": "MISSING_API_KEY"},
        )

    req_payload = dict(payload)
    if model_override:
        req_payload["model"] = model_override
    elif "model" not in req_payload:
        req_payload["model"] = _DEFAULT_MODEL

    body_bytes = _build_request_payload(req_payload)

    req = Request(
        API_URL,
        data=body_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Cache-Control": "no-store",
            "User-Agent": "doc-compare-explain/1.0",
        },
        method="POST",
    )

    # 타임아웃은 connect + read 둘 다 적용
    ctx_timeout = timeout_sec
    try:
        with urlopen(req, timeout=ctx_timeout) as resp:
            raw = resp.read()
            status = resp.status
    except HTTPError as exc:
        # 4xx/5xx 응답 본문은 짧게만 보고 버린다.
        try:
            body_snippet = exc.read(256).decode("utf-8", errors="replace")
        except Exception:
            body_snippet = ""
        logger.warning(
            "solar http error status=%s len(body_snippet)=%s",
            exc.code,
            len(body_snippet),
        )
        raise SolarError(
            f"Solar 요청이 실패했습니다 (HTTP {exc.code}).",
            retryable=exc.code >= 500,
            detail={"code": "HTTP_ERROR", "status": exc.code, "snippet_length": len(body_snippet)},
        ) from None
    except (URLError, socket.timeout, TimeoutError, OSError) as exc:
        logger.warning("solar network/timeout error: %s", type(exc).__name__)
        raise SolarError(
            "Solar 요청을 제시간에 완료하지 못했습니다.",
            retryable=True,
            detail={"code": "NETWORK_TIMEOUT"},
        ) from None

    if status != 200:
        raise SolarError(
            f"Solar 응답이 예상과 다릅니다 (상태 {status}).",
            retryable=True,
            detail={"code": "UNEXPECTED_STATUS", "status": status},
        )

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        logger.warning("solar 응답 파싱 실패, raw 길이=%s", len(raw))
        raise SolarError(
            "Solar 응답을 읽지 못했습니다.",
            retryable=True,
            detail={"code": "PARSE_ERROR"},
        )

    # 응답에서choices[0].message.content만 꺼낸다. 없으면 오류.
    choices = parsed.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        raise SolarError(
            "Solar 응답에 선택지가 없습니다.",
            retryable=True,
            detail={"code": "UNEXPECTED_RESPONSE"},
        )
    first = choices[0]
    message = first.get("message")
    content = None
    if isinstance(message, dict):
        content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise SolarError(
            "Solar 응답에 설명 텍스트가 없습니다.",
            retryable=True,
            detail={"code": "EMPTY_RESPONSE"},
        )

    return {"content": content}


def is_ready() -> bool:
    """현재 환경에서 Solar 호출이 준비됐는지 확인한다.

    - UPSTAGE_API_KEY가 있으면 True. 없으면 False.
    - PAID_FEATURES_ENABLED 같은 기능 플래그와 무관하게, 키 유무만 본다.
    - 실제 호출 가능 여부(권한·상한·계정 상태)는 이 함수에서 보증하지 않는다.
    """
    return _has_api_key()
