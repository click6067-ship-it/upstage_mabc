# -*- coding: utf-8 -*-
"""
API 통합 테스트: server.py의 GET /api/health, POST /api/compare를
합성 자료로 실제 HTTP 호출해 검증한다.

- root에서 `python -B -m backend.tests.test_api`로 단독 실행한다.
- uvicorn을 별도 스레드에서 띄우고 httpx 없이 urllib으로 루프백 호출한다.
- 포트 중복 기동을 방지하고, 이번 테스트가 시작한 서버만 종료한다.
- 합성 자료: 식대 50000원 -> 60000원 -> 70000원 변경 확인.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict
from uuid import uuid4

from backend.contracts import (
    CompareRequest,
    ComparePayload,
    ConfirmedMapping,
    DocumentPayload,
    FieldValue,
    Item,
    Period,
    Section,
    SourceLocator,
    SourceRef,
)

BASE_URL = "http://127.0.0.1:8009"


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _payload(
    document_id: str = "d1",
    employment_key: str = "e1",
    period_start: str = "2026-09-01",
    period_end: str = "2026-09-30",
    revision_key: str = "r1",
    items: list[Item] | None = None,
) -> DocumentPayload:
    return DocumentPayload(
        documentId=document_id,
        employmentKey=employment_key,
        period=Period(start=period_start, end=period_end),
        revisionKey=revision_key,
        sections=[Section(key="급여", items=items or [])],
    )


def _item(id: str, key: str | None, *, amount: int | None = None, position: int | None = None, text: str | None = None) -> Item:
    return Item(
        id=id,
        key=key,
        position=position,
        fields=FieldValue(amountKrw=amount, minutes=None, rateKrw=None, text=text),
        sourceRefs=[],
    )


def _src(source_id: str, *, page: int | None = None, item_id: str | None = None, excerpt: str | None = None) -> SourceRef:
    return SourceRef(
        sourceId=source_id,
        locator=SourceLocator(page=page, itemId=item_id, excerpt=excerpt),
    )


def _item_with_src(id: str, key: str | None, *, amount: int | None = None, position: int | None = None, text: str | None = None, source_id: str, src_page: int | None = None, src_item_id: str | None = None, src_excerpt: str | None = None) -> Item:
    return Item(
        id=id,
        key=key,
        position=position,
        fields=FieldValue(amountKrw=amount, minutes=None, rateKrw=None, text=text),
        sourceRefs=[_src(source_id, page=src_page, item_id=src_item_id, excerpt=src_excerpt)],
    )


def make_req(
    version_key: str,
    before: DocumentPayload,
    after: DocumentPayload,
    mappings: list[ConfirmedMapping] | None = None,
    request_id: str | None = None,
) -> CompareRequest:
    rid = request_id if request_id is not None else str(uuid4())
    return CompareRequest(
        schemaVersion=1,
        requestId=rid,
        versionKey=version_key,
        payload=ComparePayload(
            mode="revision",
            before=before,
            after=after,
            confirmedMappings=mappings or [],
        ),
    )


def _http_json(
    method: str,
    path: str,
    payload: dict[str, Any],
    timeout_sec: float = 5.0,
    request_id: str | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    if request_id is not None:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Request-Id": request_id,
        }
    else:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
            return {"status": resp.status, "body": json.loads(raw)}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return {"status": exc.code, "body": json.loads(raw)}
        except json.JSONDecodeError:
            return {"status": exc.code, "body": {"raw": raw}}


def wait_for_health(*, timeout_sec: float = 20.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL + "/api/health", timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


# ---------------------------------------------------------------------------
# 서버 헬퍼
# ---------------------------------------------------------------------------

_SERVER_THREAD: threading.Thread | None = None
_SERVER_PROC: "uvicorn.Server | None" = None
_SHUTDOWN_EV = threading.Event()
_SHUTDOWN_FAILED = threading.Event()


def _run_server() -> None:
    import uvicorn

    config = uvicorn.Config(
        "backend.server:app",
        host="127.0.0.1",
        port=8009,
        log_level="error",
        lifespan="off",
    )
    server = uvicorn.Server(config)
    global _SERVER_PROC
    _SERVER_PROC = server
    # 서버가 정상 기동 후 요청 처리 가능한 상태가 되면 루프 종료 지점까지 실행
    try:
        server.run()
    finally:
        _SERVER_PROC = None


def _port_in_use(host: str, port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def _start_server() -> None:
    global _SERVER_THREAD

    if _SERVER_THREAD is not None and _SERVER_THREAD.is_alive():
        raise RuntimeError("서버가 이미 기동 중이다")

    if _port_in_use("127.0.0.1", 8009):
        raise RuntimeError("포트가 이미 사용 중이다")

    t = threading.Thread(target=_run_server, daemon=True)
    t.start()
    _SERVER_THREAD = t

    if not wait_for_health(timeout_sec=20.0):
        _shutdown_server()
        raise RuntimeError("서버 기동 실패")

    # 서버가 요청을 받아들이기까지 작은 여유
    time.sleep(0.3)


def _shutdown_server() -> None:
    global _SERVER_PROC, _SERVER_THREAD

    proc = _SERVER_PROC
    if proc is not None:
        try:
            proc.should_exit = True
        except Exception:
            pass
    if _SERVER_THREAD is not None:
        _SERVER_THREAD.join(timeout=5.0)
        if _SERVER_THREAD.is_alive():
            _SHUTDOWN_FAILED.set()
        else:
            _SERVER_THREAD = None
    _SERVER_PROC = None
    _SHUTDOWN_EV.set()


def _stop_server() -> None:
    _shutdown_server()


# ---------------------------------------------------------------------------
# 공통 피스
# ---------------------------------------------------------------------------

def _doc_식대(amount: int, *, id: str, key: str = "식대", position: int = 1) -> DocumentPayload:
    return _payload(items=[_item(id=id, key=key, amount=amount, position=position)])


def _compare_식대(amount_before: int, amount_after: int) -> dict[str, Any]:
    before = _doc_식대(amount_before, id="b1")
    after = _doc_식대(amount_after, id="a1")
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings)
    return _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)


# ---------------------------------------------------------------------------
# 1) health
# ---------------------------------------------------------------------------

def test_health() -> None:
    resp = _http_json("GET", "/api/health", {})
    assert resp["status"] == 200
    body = resp["body"]
    assert body["status"] == "ok"
    assert body["buildId"] == "dev"
    assert body["engineVersion"] == "1.0.0"
    assert body["paidFeaturesEnabled"] is False


# ---------------------------------------------------------------------------
# 2) 동일 자료
# ---------------------------------------------------------------------------

def test_동일_자료() -> None:
    resp = _compare_식대(50000, 50000)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    assert data["summary"]["changed"] == 0
    assert data["summary"]["unchanged"] == 1
    assert data["itemChanges"][0]["contentKind"] == "unchanged"
    assert data["itemChanges"][0]["moved"] is False
    assert data["itemChanges"][0]["changedFields"] == []


# ---------------------------------------------------------------------------
# 3) 순수 이동
# ---------------------------------------------------------------------------

def test_순수_이동() -> None:
    before = _payload(items=[_item("b1", "식대", amount=50000, position=1)])
    after = _payload(items=[_item("a1", "식대", amount=50000, position=2)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    assert data["summary"]["moved"] == 1
    assert data["summary"]["changed"] == 0
    ic = data["itemChanges"][0]
    assert ic["contentKind"] == "unchanged"
    assert ic["moved"] is True


# ---------------------------------------------------------------------------
# 4) 이동과 추가가 같이 발생
# ---------------------------------------------------------------------------

def test_이동과_추가_동시() -> None:
    before = _payload(items=[_item("b1", "식대", amount=50000, position=1)])
    after = _payload(items=[
        _item("a1", "식대", amount=50000, position=2),
        _item("a2", "교통비", amount=20000, position=1),
    ])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    assert data["summary"]["added"] == 1
    assert data["summary"]["moved"] == 1
    kinds = {ic["contentKind"] for ic in data["itemChanges"]}
    assert kinds == {"unchanged", "added"}


# ---------------------------------------------------------------------------
# 5) 금액 변경
# ---------------------------------------------------------------------------

def test_금액_변경() -> None:
    resp = _compare_식대(50000, 60000)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    assert data["summary"]["changed"] == 1
    ic = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1")
    assert ic["contentKind"] == "changed"
    assert ic["changedFields"] == ["amountKrw"]
    assert ic["beforeFields"]["amountKrw"] == 50000
    assert ic["afterFields"]["amountKrw"] == 60000


# ---------------------------------------------------------------------------
# 6) 내용 변경과 이동 동시
# ---------------------------------------------------------------------------

def test_내용_변경_이동_동시() -> None:
    before = _payload(items=[_item("b1", "식대", amount=50000, position=1, text="식대")])
    after = _payload(items=[_item("a1", "급식비", amount=60000, position=2, text="급식비")])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    ic = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1")
    assert ic["moved"] is True
    assert ic["changedFields"] == ["amountKrw", "text"]
    assert ic["contentKind"] == "changed"


# ---------------------------------------------------------------------------
# 7) 대응이 모호하면 unresolved
# ---------------------------------------------------------------------------

def test_대응_모호_unresolved() -> None:
    before = _payload(items=[_item("b1", "식대", amount=50000)])
    after = _payload(items=[_item("a1", "식대", amount=60000)])
    req = make_req("v1", before, after, mappings=[])
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    kinds = {ic["contentKind"] for ic in data["itemChanges"]}
    assert kinds == {"unresolved"}


# ---------------------------------------------------------------------------
# 8) 중복 id 거절
# ---------------------------------------------------------------------------

def test_중복_id_거절() -> None:
    before = _payload(items=[_item("dup", "식대", amount=50000), _item("dup", "식대", amount=60000)])
    after = _payload(items=[_item("a1", "식대", amount=50000)])
    req = make_req("v1", before, after, mappings=[])
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 400
    assert resp["body"]["error"]["code"] == "INVALID_INPUT"


# ---------------------------------------------------------------------------
# 9) 잘못된 mapping 거절
# ---------------------------------------------------------------------------

def test_잘못된_mapping_거절() -> None:
    before = _payload(items=[_item("b1", "식대", amount=50000)])
    after = _payload(items=[_item("a1", "식대", amount=50000)])
    mappings = [
        ConfirmedMapping(beforeItemId="b1", afterItemId="missing"),
        ConfirmedMapping(beforeItemId="b1", afterItemId="a1"),
    ]
    req = make_req("v1", before, after, mappings=mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 400
    assert any(e.get("field") == "confirmedMappings" for e in resp["body"]["error"]["fieldErrors"])


# ---------------------------------------------------------------------------
# 10) 다른 일자리 / 기간 거절
# ---------------------------------------------------------------------------

def test_다른_일자리_거절() -> None:
    before = _payload(employment_key="e1", items=[_item("b1", "식대", amount=50000)])
    after = _payload(employment_key="e2", items=[_item("a1", "식대", amount=50000)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings=mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 400
    assert any(e.get("code") == "DIFFERENT_EMPLOYMENT" for e in resp["body"]["error"]["fieldErrors"])


def test_다른_기간_거절() -> None:
    before = _payload(
        period_start="2026-09-01",
        period_end="2026-09-30",
        items=[_item("b1", "식대", amount=50000)],
    )
    after = _payload(
        period_start="2026-10-01",
        period_end="2026-10-31",
        items=[_item("a1", "식대", amount=50000)],
    )
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings=mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 400
    assert any(e.get("code") == "DIFFERENT_PERIOD" for e in resp["body"]["error"]["fieldErrors"])


# ---------------------------------------------------------------------------
# 11) 지원하지 않는 mode 거절
# ---------------------------------------------------------------------------

def test_지원하지_않는_mode_거절() -> None:
    before = _payload(items=[_item("b1", "식대", amount=50000)])
    after = _payload(items=[_item("a1", "식대", amount=50000)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings=mappings)
    body = req.model_dump()
    body["payload"]["mode"] = "monthly"
    resp = _http_json("POST", "/api/compare", body, request_id=req.requestId)
    assert resp["status"] == 400
    assert any(e.get("code") == "UNSUPPORTED_MODE" for e in resp["body"]["error"]["fieldErrors"])


# ---------------------------------------------------------------------------
# 12) 입력 한도 초과 거절
# ---------------------------------------------------------------------------

def test_입력_한도_초과_거절() -> None:
    big = "x" * 300
    before = _payload(document_id=big, employment_key=big, items=[_item("b1", "식대", amount=50000)])
    after = _payload(items=[_item("a1", "식대", amount=50000)])
    req = make_req("v1", before, after, mappings=[])
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 400
    assert any(e.get("code") in ("INVALID_ID", "TOO_LARGE") for e in resp["body"]["error"]["fieldErrors"])


# ---------------------------------------------------------------------------
# 13) 누락 / null / 0 구분
# ---------------------------------------------------------------------------

def test_누락_null_0_구분() -> None:
    before = _payload(items=[_item("b1", "식대", amount=0)])
    after = _payload(items=[_item("a1", "식대", amount=None)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings=mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    ic = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1")
    assert ic["changedFields"] == ["amountKrw"]
    assert ic["beforeFields"]["amountKrw"] == 0
    assert ic["afterFields"]["amountKrw"] is None


# ---------------------------------------------------------------------------
# 14) 식대 50000 -> 60000 -> 70000 연속 확인
# ---------------------------------------------------------------------------

def test_식대_50000_60000_70000_연속() -> None:
    def 비교(금액_전: int, 금액_후: int) -> dict[str, Any]:
        before = _doc_식대(금액_전, id="b1")
        after = _doc_식대(금액_후, id="a1")
        mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
        req = make_req("v1", before, after, mappings)
        return _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)

    r1 = 비교(50000, 60000)
    assert r1["status"] == 200
    data1 = r1["body"]["data"]
    ic1 = next(ic for ic in data1["itemChanges"] if ic["beforeItemId"] == "b1")
    assert ic1["changedFields"] == ["amountKrw"]
    assert ic1["beforeFields"]["amountKrw"] == 50000
    assert ic1["afterFields"]["amountKrw"] == 60000
    assert ic1["contentKind"] == "changed"

    r2 = 비교(60000, 70000)
    assert r2["status"] == 200
    data2 = r2["body"]["data"]
    ic2 = next(ic for ic in data2["itemChanges"] if ic["beforeItemId"] == "b1")
    assert ic2["changedFields"] == ["amountKrw"]
    assert ic2["beforeFields"]["amountKrw"] == 60000
    assert ic2["afterFields"]["amountKrw"] == 70000
    assert ic2["contentKind"] == "changed"

    assert r1["body"]["data"] != r2["body"]["data"], "바뀐 금액이 응답에 반영되어야 함"


# ---------------------------------------------------------------------------
# 15) 잘못된 UUID 요청Id 거절
# ---------------------------------------------------------------------------

def test_잘못된_uuid_요청_거절() -> None:
    before = _payload(items=[_item("b1", "식대", amount=50000)])
    after = _payload(items=[_item("a1", "식대", amount=50000)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings=mappings, request_id="not-a-uuid")
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 400
    assert any(e.get("code") == "INVALID_UUID" for e in resp["body"]["error"]["fieldErrors"])


# ---------------------------------------------------------------------------
# 16) 출처 보존: 요청 sourceRefs가 비교 응답까지 그대로 유지
# ---------------------------------------------------------------------------

def _req_with_src(before_source_id: str, after_source_id: str, *, before_page: int | None = None, after_page: int | None = None, before_excerpt: str | None = None, after_excerpt: str | None = None) -> dict[str, Any]:
    before = _payload(items=[_item_with_src("b1", "식대", amount=50000, source_id=before_source_id, src_page=before_page, src_excerpt=before_excerpt)])
    after = _payload(items=[_item_with_src("a1", "식대", amount=60000, source_id=after_source_id, src_page=after_page, src_excerpt=after_excerpt)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings)
    return _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)


def test_출처_요청에서_응답까지_보존() -> None:
    resp = _req_with_src("src-1", "src-2", before_page=1, after_page=2, before_excerpt="식대 50000원", after_excerpt="식대 60000원")
    assert resp["status"] == 200
    data = resp["body"]["data"]
    ic = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1")
    assert ic["beforeSourceRefs"] != []
    assert ic["afterSourceRefs"] != []
    assert ic["beforeSourceRefs"][0]["sourceId"] == "src-1"
    assert ic["afterSourceRefs"][0]["sourceId"] == "src-2"
    assert ic["beforeSourceRefs"][0]["locator"]["page"] == 1
    assert ic["afterSourceRefs"][0]["locator"]["page"] == 2
    assert ic["beforeSourceRefs"][0]["locator"]["excerpt"] == "식대 50000원"
    assert ic["afterSourceRefs"][0]["locator"]["excerpt"] == "식대 60000원"


def test_출처_없으면_빈배열_유지() -> None:
    before = _payload(items=[_item("b1", "식대", amount=50000)])
    after = _payload(items=[_item("a1", "식대", amount=60000)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    ic = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1")
    assert ic["beforeSourceRefs"] == []
    assert ic["afterSourceRefs"] == []


def test_출처_모르면_null_유지() -> None:
    before = _payload(items=[_item_with_src("s1", "식대", amount=50000, source_id="s1", src_page=None, src_item_id=None, src_excerpt=None)])
    after = _payload(items=[_item_with_src("s1", "식대", amount=60000, source_id="s1", src_page=None, src_item_id=None, src_excerpt=None)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    before.sections[0].items[0].id = "b1"
    after.sections[0].items[0].id = "a1"
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    ic = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1")
    assert ic["beforeSourceRefs"][0]["locator"]["page"] is None
    assert ic["beforeSourceRefs"][0]["locator"]["itemId"] is None
    assert ic["beforeSourceRefs"][0]["locator"]["excerpt"] is None


def test_이동에서_전후_출처_보존() -> None:
    before = _payload(items=[_item_with_src("s-before", "식대", amount=50000, position=1, source_id="s-before", src_page=1)])
    after = _payload(items=[_item_with_src("s-after", "식대", amount=50000, position=2, source_id="s-after", src_page=2)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    before.sections[0].items[0].id = "b1"
    after.sections[0].items[0].id = "a1"
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    ic = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1")
    assert ic["moved"] is True
    assert ic["beforeSourceRefs"][0]["sourceId"] == "s-before"
    assert ic["afterSourceRefs"][0]["sourceId"] == "s-after"


def test_추회에서_출처_보존() -> None:
    before = _payload(items=[_item_with_src("s-before", "식대", amount=50000, position=1, source_id="s-before")])
    after = _payload(items=[
        _item_with_src("s-after", "식대", amount=50000, position=2, source_id="s-after"),
        _item_with_src("s-add", "교통비", amount=20000, position=1, source_id="s-add"),
    ])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    before.sections[0].items[0].id = "b1"
    after.sections[0].items[0].id = "a1"
    after.sections[0].items[1].id = "a2"
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    added = next(ic for ic in data["itemChanges"] if ic["afterItemId"] == "a2")
    assert added["contentKind"] == "added"
    assert added["afterSourceRefs"][0]["sourceId"] == "s-add"


def test_삭제에서_출처_보존() -> None:
    before = _payload(items=[_item_with_src("s-del", "식대", amount=50000, position=1, source_id="s-del", src_page=1)])
    after = _payload(items=[])
    mappings = []
    before.sections[0].items[0].id = "b1"
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    deleted = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1")
    assert deleted["contentKind"] == "deleted"
    assert deleted["beforeSourceRefs"][0]["sourceId"] == "s-del"
    assert deleted["beforeSourceRefs"][0]["locator"]["page"] == 1


def test_보류_unresolved에서_출처_보존() -> None:
    before = _payload(items=[_item_with_src("s-before", "식대", amount=50000, source_id="s-before", src_page=1)])
    after = _payload(items=[_item_with_src("s-after", "식대", amount=60000, source_id="s-after", src_page=2)])
    mappings = []
    before.sections[0].items[0].id = "b1"
    after.sections[0].items[0].id = "a1"
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    unmatched_before = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1" and ic["afterItemId"] is None)
    assert unmatched_before["contentKind"] == "unresolved"
    assert unmatched_before["beforeSourceRefs"][0]["sourceId"] == "s-before"
    unmatched_after = next(ic for ic in data["itemChanges"] if ic["afterItemId"] == "a1" and ic["beforeItemId"] is None)
    assert unmatched_after["contentKind"] == "unresolved"
    assert unmatched_after["afterSourceRefs"][0]["sourceId"] == "s-after"


# ---------------------------------------------------------------------------
# 17) 누락/null/0 왕복: {} / {"amountKrw":null} / {"amountKrw":0} — 실제 HTTP 9조합 검사
# ---------------------------------------------------------------------------

def _compare_fields_direct(
    before_fields: Dict[str, Any],
    after_fields: Dict[str, Any],
    *,
    before_id: str = "b1",
    after_id: str = "a1",
    before_amount: int | None = None,
    after_amount: int | None = None,
) -> dict[str, Any]:
    """요청 dict에 fields를 직접 넣어 POST /api/compare를 호출한다.

    - ``before_fields``/``after_fields``는 응답의 beforeFields/afterFields와
      정확히 일치해야 하는 값이다.
    - before/after 각각 amount를 가진 기본 항목 위에, 지정한 fields만 얹는다.
    - 보내는 JSON의 페이로드도 함께 출력해 확인할 수 있다.
    """
    import json as _json
    from uuid import uuid4 as _uuid4

    before_item: Dict[str, Any] = {
        "id": before_id,
        "key": "식대",
        "position": 1,
        "fields": before_fields,
        "sourceRefs": [],
    }
    after_item: Dict[str, Any] = {
        "id": after_id,
        "key": "식대",
        "position": 1,
        "fields": after_fields,
        "sourceRefs": [],
    }
    body: Dict[str, Any] = {
        "schemaVersion": 1,
        "requestId": str(_uuid4()),
        "versionKey": "v1",
        "payload": {
            "mode": "revision",
            "before": {
                "documentId": "d1",
                "employmentKey": "e1",
                "period": {"start": "2026-09-01", "end": "2026-09-30"},
                "revisionKey": "r1",
                "sections": [{"key": "급여", "items": [before_item]}],
            },
            "after": {
                "documentId": "d1",
                "employmentKey": "e1",
                "period": {"start": "2026-09-01", "end": "2026-09-30"},
                "revisionKey": "r1",
                "sections": [{"key": "급여", "items": [after_item]}],
            },
            "confirmedMappings": [{"beforeItemId": before_id, "afterItemId": after_id}],
        },
    }
    print(f"[compare-fields] 요청 before={before_fields!r} after={after_fields!r}")
    print(f"[compare-fields] 발송 JSON = {_json.dumps(body, ensure_ascii=False)}")
    return _http_json("POST", "/api/compare", body)


def _changed_expected(before_fields: Dict[str, Any], after_fields: Dict[str, Any]) -> list[str]:
    """adapter._changed_fields와 같은 규칙으로 changedFields 기대값을 계산한다."""
    names = ["amountKrw", "minutes", "rateKrw", "text"]
    out: list[str] = []
    for name in names:
        a_set = name in before_fields
        b_set = name in after_fields
        if a_set and b_set:
            if before_fields[name] != after_fields[name]:
                out.append(name)
        elif a_set != b_set:
            out.append(name)
    return sorted(out)


def test_필드러운드트립_3케이스() -> None:
    """{} / {"amountKrw":null} / {"amountKrw":0} 전후 9조합을 실제 HTTP로 검사한다.

    보내는 JSON의 페이로드와 응답의 beforeFields/afterFields가 입력과
    정확히 같은지 확인한다. 동일 조합은 changedFields=[], 다르면
    changedFields=["amountKrw"]이다.
    """
    cases: list[tuple[Dict[str, Any], Dict[str, Any]]] = [
        ({}, {}),
        ({}, {"amountKrw": None}),
        ({}, {"amountKrw": 0}),
        ({"amountKrw": None}, {}),
        ({"amountKrw": None}, {"amountKrw": None}),
        ({"amountKrw": None}, {"amountKrw": 0}),
        ({"amountKrw": 0}, {}),
        ({"amountKrw": 0}, {"amountKrw": None}),
        ({"amountKrw": 0}, {"amountKrw": 0}),
    ]
    for before_fields, after_fields in cases:
        resp = _compare_fields_direct(before_fields, after_fields)
        assert resp["status"] == 200, f"before={before_fields!r} after={after_fields!r} 실패: {resp}"
        data = resp["body"]["data"]
        ic = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1")
        assert ic["beforeFields"] == before_fields, f"beforeFields 불일치: {ic['beforeFields']!r} vs {before_fields!r}"
        assert ic["afterFields"] == after_fields, f"afterFields 불일치: {ic['afterFields']!r} vs {after_fields!r}"
        assert ic["changedFields"] == _changed_expected(before_fields, after_fields), (
            f"changedFields 불일치: {ic['changedFields']!r} vs {_changed_expected(before_fields, after_fields)!r}"
        )
        if before_fields == after_fields:
            assert ic["changedFields"] == [], f"동일 조합인데 changedFields={ic['changedFields']!r}"
        else:
            assert ic["changedFields"] == ["amountKrw"], f"변경 조합인데 changedFields={ic['changedFields']!r}"


def test_요청_누락_null_0_응답에_자동추가_안됨() -> None:
    """after fields를 {}로 보내면 응답 afterFields도 {}다. null/0이 자동 추가되지 않는다."""
    before_fields = {"amountKrw": 50000}
    after_fields: Dict[str, Any] = {}
    resp = _compare_fields_direct(before_fields, after_fields)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    ic = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1")
    assert ic["afterFields"] == after_fields, f"afterFields가 자동 추가됨: {ic['afterFields']!r}"
    assert ic["changedFields"] == ["amountKrw"]


def test_null과_0은_다른_전후_변경으로_잡힘() -> None:
    """null과 0은 서로 다른 상태로 변경되어 changedFields에 잡힌다."""
    before_fields = {"amountKrw": None}
    after_fields = {"amountKrw": 0}
    resp = _compare_fields_direct(before_fields, after_fields)
    assert resp["status"] == 200
    data = resp["body"]["data"]
    ic = next(ic for ic in data["itemChanges"] if ic["beforeItemId"] == "b1")
    assert ic["changedFields"] == ["amountKrw"]
    assert ic["beforeFields"] == before_fields
    assert ic["afterFields"] == after_fields


# ---------------------------------------------------------------------------
# 18) 출처 검증 거절: 빈 sourceId / page 0 / excerpt 501자
# ---------------------------------------------------------------------------

def test_빈_sourceId_거절() -> None:
    bad = Item.model_construct(id="b1", key="식대", sourceRefs=[{"sourceId": "   ", "locator": {}}])
    before = _payload(items=[bad])
    after = _payload(items=[_item("a1", "식대", amount=50000)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 400
    assert any(e.get("field", "").endswith(".sourceId") for e in resp["body"]["error"]["fieldErrors"])


def test_출처_page_0_거절() -> None:
    bad = Item.model_construct(id="b1", key="식대", sourceRefs=[{"sourceId": "s1", "locator": {"page": 0}}])
    before = _payload(items=[bad])
    after = _payload(items=[_item("a1", "식대", amount=50000)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 400
    assert any(e.get("field", "").endswith(".locator.page") for e in resp["body"]["error"]["fieldErrors"])


def test_출처_excerpt_501자_거절() -> None:
    bad = Item.model_construct(id="b1", key="식대", sourceRefs=[{"sourceId": "s1", "locator": {"excerpt": "x" * 501}}])
    before = _payload(items=[bad])
    after = _payload(items=[_item("a1", "식대", amount=50000)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 400
    assert any(e.get("field", "").endswith(".locator.excerpt") for e in resp["body"]["error"]["fieldErrors"])


# ---------------------------------------------------------------------------
# 19) 요청 바이트 / 항목 수 / 문자열 길이 / Cache-Control
# ---------------------------------------------------------------------------

def _raw_body_status(body: bytes) -> dict[str, Any]:
    """urllib으로 raw 바이트를 POST하고 상태/헤더/응답 본문을 반환한다."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    req = urllib.request.Request(BASE_URL + "/api/compare", data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            raw = resp.read().decode("utf-8")
            return {"status": resp.status, "headers": dict(resp.headers), "body": json.loads(raw)}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return {"status": exc.code, "headers": dict(exc.headers), "body": json.loads(raw)}
        except json.JSONDecodeError:
            return {"status": exc.code, "headers": dict(exc.headers), "body": {"raw": raw}}


def _make_compare_body(
    *,
    before_items: Any = None,
    after_items: Any = None,
    before_extra: Any = None,
    after_extra: Any = None,
    overrides: Any = None,
    target_length: int | None = None,
) -> bytes:
    """POST /api/compare로 보낼 bytes를 만든다.

    - ``before_items``/``after_items``는 each item dict.
    - 필요하면 ``before_extra``/``after_extra``로 센션/문서 필드를 덧댄다.
    - ``overrides``로 전체 payload를 직접 덮어쓸 수 있다.
    - ``target_length``를 주면 JSON 본문 뒤에 공백을 채워 정확히 해당 바이트로 만든다.
    """
    import uuid

    def _item_dict(id, key, *, amount=None, position=1, label=None, text=None, sourceRefs=None):
        obj: Any = {
            "id": id,
            "key": key,
            "position": position,
            "fields": {"amountKrw": amount},
            "sourceRefs": sourceRefs if sourceRefs is not None else [],
        }
        if label is not None:
            obj["label"] = label
        if text is not None:
            obj["fields"]["text"] = text
        return obj

    def _doc(items, *, documentId="d1", employmentKey="e1", revisionKey="r1"):
        return {
            "documentId": documentId,
            "employmentKey": employmentKey,
            "period": {"start": "2026-09-01", "end": "2026-09-30"},
            "revisionKey": revisionKey,
            "sections": [{"key": "급여", "items": items}],
        }

    if overrides is not None:
        body = dict(overrides)
    else:
        body = {
            "schemaVersion": 1,
            "requestId": str(uuid.uuid4()),
            "versionKey": "v1",
            "payload": {
                "mode": "revision",
                "before": _doc(before_items if before_items is not None else [_item_dict("b1", "식대", amount=50000)]),
                "after": _doc(after_items if after_items is not None else [_item_dict("a1", "식대", amount=50000)]),
                "confirmedMappings": [{"beforeItemId": "b1", "afterItemId": "a1"}],
            },
        }
    if before_extra is not None:
        body["payload"]["before"].update(before_extra)
    if after_extra is not None:
        body["payload"]["after"].update(after_extra)
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if target_length is not None and len(payload) < target_length:
        payload = payload + b" " * (target_length - len(payload))
    return payload


def test_요청_바이트_524288_허용_524289_거절() -> None:
    """실제 읽은 바이트 524288 이하는 허용, 524289는 413/TOO_LARGE.

    정상 JSON 본문 뒤에 공백을 붙여 정확히 524288/524289바이트로 맞춘다.
    """
    body_ok = _make_compare_body(target_length=524288)
    assert len(body_ok) == 524288, f"예상 크기 524288, 실제 {len(body_ok)}"
    r_ok = _raw_body_status(body_ok)
    assert r_ok["status"] == 200, f"524288 허용 실패: {r_ok}"

    body_oversize = body_ok + b" "
    assert len(body_oversize) == 524289, f"예상 크기 524289, 실제 {len(body_oversize)}"
    r_oversize = _raw_body_status(body_oversize)
    assert r_oversize["status"] == 413, f"524289 거절 실패: {r_oversize}"
    assert r_oversize["body"]["error"]["code"] == "TOO_LARGE"


def _make_items(amount, n, *, key=None, label=None, text=None, id_prefix="i"):
    """동일 항목 n개 리스트(항목 수 제한 검사용)."""
    return [
        _item(f"{id_prefix}{i:03d}", key or "식대", amount=amount, position=i, text=text)
        for i in range(1, n + 1)
    ]


def test_항목_수_200_허용_201_거절() -> None:
    """before/after 각각 모든 섹션 합쳐 200개 이하는 허용, 201은 413.

    한도 검사는 confirmedMappings 없이 보내고, before/after 항목 id가
    겹치지 않게 id_prefix를 분리한다.
    """
    before200 = _payload(items=_make_items(1000, 200, id_prefix="b"))
    after200 = _payload(items=_make_items(1000, 200, id_prefix="a"))
    req = make_req("v1", before200, after200, mappings=[])
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200, f"before=200 after=200 허용 실패: {resp}"

    before201 = _payload(items=_make_items(1000, 201, id_prefix="b"))
    after201 = _payload(items=_make_items(1000, 201, id_prefix="a"))
    req = make_req("v1", before201, after201, mappings=[])
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 413, f"before=201 after=201 거절 실패: {resp}"
    assert resp["body"]["error"]["code"] == "TOO_LARGE"


def test_항목_수_여러_섹션_분산_합계_기준() -> None:
    """여러 섹션에 나눠 넣어도 합계가 201이면 413, 200이면 허용.

    문서 안에서 before/after 각각 id가 겹치지 않게 id_prefix를 분리하고,
    한도 검사는 confirmedMappings 없이 보낸다.
    """
    def _플릿(amount: int, *section_counts: int, id_prefix: str) -> list[Section]:
        """section_counts 각각에 해당하는 항목 수를 가진 섹션 리스트를 만든다.

        문서 안에서 섹션 간 id가 겹치지 않게 섹션마다 id_prefix 접미사를 붙인다.
        """
        out: list[Section] = []
        for i, count in enumerate(section_counts):
            items = _make_items(amount, count, key="식대", id_prefix=f"{id_prefix}{i}")
            out.append(Section(key=f"섹션{i+1}", items=items))
        return out

    before200 = _payload(items=[])
    before200.sections = _플릿(1000, 100, 100, id_prefix="b")
    after200 = _payload(items=[])
    after200.sections = _플릿(1000, 100, 100, id_prefix="a")
    req = make_req("v1", before200, after200, mappings=[])
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200, f"분산 200 허용 실패: {resp}"

    before201 = _payload(items=[])
    before201.sections = _플릿(1000, 100, 101, id_prefix="b")
    after201 = _payload(items=[])
    after201.sections = _플릿(1000, 100, 101, id_prefix="a")
    req = make_req("v1", before201, after201, mappings=[])
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 413, f"분산 201 거절 실패: {resp}"
    assert resp["body"]["error"]["code"] == "TOO_LARGE"


def test_before_200_후_200_허용() -> None:
    """before 200 + after 200 조합은 허용.

    한도 검사는 confirmedMappings 없이 보내고, before/after 항목 id가
    겹치지 않게 id_prefix를 분리한다.
    """
    before = _payload(items=_make_items(1000, 200, id_prefix="b"))
    after = _payload(items=_make_items(1000, 200, id_prefix="a"))
    req = make_req("v1", before, after, mappings=[])
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200, f"before=200/after=200 허용 실패: {resp}"


def test_label_text_2000_허용_2001_거절() -> None:
    """item.label, fields.text는 각각 최대 2000자. 한글 경계도 동일."""
    label_ok = "가" * 2000
    text_ok = "나" * 2000
    before = _payload(items=[_item("b1", "식대", amount=50000, position=1, text=text_ok)])
    before.sections[0].items[0].label = label_ok
    after = _payload(items=[_item("a1", "식대", amount=50000, position=1)])
    mappings = [ConfirmedMapping(beforeItemId="b1", afterItemId="a1")]
    req = make_req("v1", before, after, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 200, f"label=2000/text=2000 허용 실패: {resp}"

    label_over = "가" * 2001
    text_over = "나" * 2001
    before_bad = _payload(items=[_item("b1", "식대", amount=50000, position=1)])
    before_bad.sections[0].items[0].label = label_over
    before_bad.sections[0].items[0].fields.text = text_over
    after_bad = _payload(items=[_item("a1", "식대", amount=50000, position=1)])
    req = make_req("v1", before_bad, after_bad, mappings)
    resp = _http_json("POST", "/api/compare", req.model_dump(), request_id=req.requestId)
    assert resp["status"] == 413, f"label=2001/text=2001 거절 실패: {resp}"
    assert resp["body"]["error"]["code"] == "TOO_LARGE"


def test_Cache_Control_no_store_전체_응답() -> None:
    """정상/검증오류/한도초과/404/405 응답에 Cache-Control: no-store."""
    def _header_for(method, path, body=None):
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        req = urllib.request.Request(BASE_URL + path, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                raw_h = dict(resp.headers)
                norm = {k.lower(): v for k, v in raw_h.items()}
                return resp.status, norm
        except urllib.error.HTTPError as exc:
            raw_h = dict(exc.headers)
            norm = {k.lower(): v for k, v in raw_h.items()}
            return exc.code, norm

    status, headers = _header_for("GET", "/api/health")
    assert status == 200
    assert headers.get("cache-control", "").lower() == "no-store", f"GET /api/health: {headers}"

    status, headers = _header_for("POST", "/api/compare", body=_make_compare_body(target_length=524288))
    assert status == 200
    assert headers.get("cache-control", "").lower() == "no-store"

    bad = _make_compare_body(overrides={"schemaVersion": 99})
    status, headers = _header_for("POST", "/api/compare", body=bad)
    assert status == 400
    assert headers.get("cache-control", "").lower() == "no-store"

    oversize = _make_compare_body(target_length=524288)
    assert len(oversize) == 524288
    oversize = oversize + b" "
    assert len(oversize) == 524289
    status, headers = _header_for("POST", "/api/compare", body=oversize)
    assert status == 413
    assert headers.get("cache-control", "").lower() == "no-store"

    status, headers = _header_for("GET", "/api/compare")
    assert status == 404 or status == 405
    assert headers.get("cache-control", "").lower() == "no-store", f"GET /api/compare: {headers}"

    status, headers = _header_for("DELETE", "/api/compare")
    assert status == 404 or status == 405
    assert headers.get("cache-control", "").lower() == "no-store", f"DELETE /api/compare: {headers}"


if __name__ == "__main__":
    import sys

    _start_server()
    try:
        tests = [
            test_health,
            test_동일_자료,
            test_순수_이동,
            test_이동과_추가_동시,
            test_금액_변경,
            test_내용_변경_이동_동시,
            test_대응_모호_unresolved,
            test_중복_id_거절,
            test_잘못된_mapping_거절,
            test_다른_일자리_거절,
            test_다른_기간_거절,
            test_지원하지_않는_mode_거절,
            test_입력_한도_초과_거절,
            test_누락_null_0_구분,
            test_식대_50000_60000_70000_연속,
            test_잘못된_uuid_요청_거절,
            test_출처_요청에서_응답까지_보존,
            test_출처_없으면_빈배열_유지,
            test_출처_모르면_null_유지,
            test_이동에서_전후_출처_보존,
            test_추회에서_출처_보존,
            test_삭제에서_출처_보존,
            test_보류_unresolved에서_출처_보존,
            test_필드러운드트립_3케이스,
            test_요청_누락_null_0_응답에_자동추가_안됨,
            test_null과_0은_다른_전후_변경으로_잡힘,
            test_빈_sourceId_거절,
            test_출처_page_0_거절,
            test_출처_excerpt_501자_거절,
            test_요청_바이트_524288_허용_524289_거절,
            test_항목_수_200_허용_201_거절,
            test_항목_수_여러_섹션_분산_합계_기준,
            test_before_200_후_200_허용,
            test_label_text_2000_허용_2001_거절,
            test_Cache_Control_no_store_전체_응답,
        ]
        failed = []
        for t in tests:
            try:
                t()
                print(f"ok: {t.__name__}")
            except AssertionError as e:
                print(f"FAIL: {t.__name__} - {e}")
                failed.append(t.__name__)
            except Exception as e:
                print(f"ERROR: {t.__name__} - {e}")
                failed.append(t.__name__)

        if failed:
            print(f"\n{len(failed)}개 실패: {failed}")
            sys.exit(1)
        print(f"\n모두 통과: {len(tests)}개")
        sys.exit(0)
    finally:
        _stop_server()
        if _SHUTDOWN_FAILED.is_set():
            print("서버 종료 실패")
            sys.exit(1)
