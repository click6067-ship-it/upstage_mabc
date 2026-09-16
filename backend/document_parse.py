# -*- coding: utf-8 -*-
"""
Upstage Document Parse 호출부.

- 공식 문서 기준 sync endpoint: POST https://api.upstage.ai/v1/document-digitization
- form-field 업로드(document + model + output_formats)로 PDF를 마크다운으로 변환한다.
- 키 원문·원본 PDF·응답 본문은 로그/저장하지 않는다.
- 외부 호출에는 타임아웃을 적용한다.
- UPSTAGE_API_KEY가 비어 있으면 호출하지 않고 DocumentParseError를 즉시 반환한다.
- 유료 기능 플래그는 이 모듈이 아니라 upload_api 쪽에서 판단한다.
"""

from __future__ import annotations

import io
import logging
import os
import socket
import time
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("paychecker-ocr.document-parse")

DOCUMENT_PARSE_URL = "https://api.upstage.ai/v1/document-digitization"
_REQUEST_TIMEOUT_SEC = 60
_DEFAULT_MODEL = "document-parse"


class DocumentParseError(Exception):
    """Document Parse 호출/해석 실패."""

    def __init__(
        self,
        message: str,
        retryable: bool = True,
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.retryable = retryable


def _has_api_key() -> bool:
    v = os.environ.get("UPSTAGE_API_KEY")
    return bool(v and v.strip())


def _api_key() -> str:
    return os.environ.get("UPSTAGE_API_KEY", "").strip()


def _guess_content_type(filename: str) -> str:
    low = filename.lower()
    if low.endswith(".pdf"):
        return "application/pdf"
    if low.endswith(".png"):
        return "image/png"
    if low.endswith(".jpg") or low.endswith(".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"


def _encode_multipart(
    document_bytes: bytes,
    document_filename: str,
    fields: Dict[str, str],
) -> tuple[bytes, str]:
    """requests 없이 multipart/form-data 본문을 만든다.

    반환: (body_bytes, content_type_header_value)
    """
    boundary = "----PaycheckerOcrMultipart{}".format(int(time.time() * 1_000_000))
    lines: list[bytes] = []
    CRLF = b"\r\n"

    # 파일 필드
    content_type = _guess_content_type(document_filename)
    lines.append(b"--" + boundary.encode() + CRLF)
    lines.append(
        f'Content-Disposition: form-data; name="document"; '
        f'filename="{document_filename}"'.encode()
        + CRLF
    )
    lines.append(b"Content-Type: " + content_type.encode() + CRLF)
    lines.append(CRLF)
    lines.append(document_bytes)
    lines.append(CRLF)

    # 일반 필드
    for name, value in fields.items():
        lines.append(b"--" + boundary.encode() + CRLF)
        lines.append(
            f'Content-Disposition: form-data; name="{name}"'.encode()
            + CRLF
        )
        lines.append(CRLF)
        lines.append(value.encode())
        lines.append(CRLF)

    # 종료 경계
    lines.append(b"--" + boundary.encode() + b"--" + CRLF)

    body = b"".join(lines)
    content_type_header = "multipart/form-data; boundary={}".format(boundary)
    return body, content_type_header


def parse_document(
    pdf_bytes: bytes,
    pdf_filename: str,
    *,
    model: Optional[str] = None,
    output_formats: Optional[str] = None,
    timeout_sec: int = _REQUEST_TIMEOUT_SEC,
) -> Dict[str, Any]:
    """Upstage Document Parse에 PDF를 보내고 파싱 결과를 반환한다.

    반환 dict 예시:
        {
            "api": "2.0",
            "model": "...",
            "content": {"markdown": "...", "html": "...", "text": "..."},
            "elements": [...],
            "usage": {"pages": 1},
        }

    - pdf_bytes: 실제 PDF 바이트.
    - pdf_filename: 확장자 포함 파일명(예: "wage-slip.pdf").
    - model: 미지정 시 document-parse 사용.
    - output_formats: 미지정 시 ['markdown'] 사용(문자열로 전송).
    - 실패 시 DocumentParseError 반환.
    """
    api_key = _api_key()
    if not api_key:
        raise DocumentParseError(
            "UPSTAGE_API_KEY가 설정되지 않아 Document Parse를 호출하지 않았다.",
            retryable=False,
            detail={"code": "MISSING_API_KEY"},
        )

    fields: Dict[str, str] = {"model": model or _DEFAULT_MODEL}
    if output_formats:
        fields["output_formats"] = output_formats
    else:
        fields["output_formats"] = "['markdown']"

    body, content_type = _encode_multipart(pdf_bytes, pdf_filename, fields)

    req = Request(
        DOCUMENT_PARSE_URL,
        data=body,
        headers={
            "Content-Type": content_type,
            "Authorization": "Bearer " + api_key,
            "Cache-Control": "no-store",
            "User-Agent": "paychecker-ocr/1.0",
        },
        method="POST",
    )

    ctx_timeout = timeout_sec
    try:
        with urlopen(req, timeout=ctx_timeout) as resp:
            raw = resp.read()
            status = resp.status
    except HTTPError as exc:
        try:
            snippet = exc.read(512).decode("utf-8", errors="replace")
        except Exception:
            snippet = ""
        logger.warning(
            "document-parse http error status=%s len(snippet)=%s",
            exc.code,
            len(snippet),
        )
        raise DocumentParseError(
            "Document Parse 요청이 실패했습니다 (HTTP {}).".format(exc.code),
            retryable=exc.code >= 500,
            detail={"code": "HTTP_ERROR", "status": exc.code, "snippet_length": len(snippet)},
        ) from None
    except (URLError, socket.timeout, TimeoutError, OSError) as exc:
        logger.warning("document-parse network/timeout error: %s", type(exc).__name__)
        raise DocumentParseError(
            "Document Parse 요청을 제시간에 완료하지 못했습니다.",
            retryable=True,
            detail={"code": "NETWORK_TIMEOUT"},
        ) from None

    if status != 200:
        raise DocumentParseError(
            "Document Parse 응답이 예상과 다릅니다 (상태 {}).".format(status),
            retryable=True,
            detail={"code": "UNEXPECTED_STATUS", "status": status},
        )

    try:
        parsed = _json.loads(raw.decode("utf-8"))
    except Exception:
        logger.warning("document-parse 응답 파싱 실패, raw 길이=%s", len(raw))
        raise DocumentParseError(
            "Document Parse 응답을 읽지 못했습니다.",
            retryable=True,
            detail={"code": "PARSE_ERROR"},
        )

    return parsed


# urllib.request로 보내지만 JSON 해석용 부수입 import
import json as _json
