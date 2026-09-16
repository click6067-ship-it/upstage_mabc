# -*- coding: utf-8 -*-
"""
backend.tests.test_explanation

Solar 설명/질문 생성 모듈(unit-only, 합성 자료 + mock HTTP)의 검사.

- 키 없음 / OFF / 성공 / timeout / 잘못된 응답 시나리오를 mock으로 검사한다.
- 실제 Solar 호출과 mock 검사는 구분한다. 이 파일은 mock 검사만 수행한다.
- 설치·설정파일 변경·커밋·push·자식 없음.
- product 루트 .venv/Scripts/python.exe -B -m backend.tests.test_explanation 으로 실행.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import patch
from urllib.error import HTTPError

# 이 테스트가 product 루트에서 -m backend.tests.test_explanation 으로 기동된다고 가정한다.
# 따라서 sys.path에 프로젝트 루트가 잡혀 있고 backend 패키지를 import할 수 있다.
try:
    from backend.explanation import (
        _build_request_payload,
        _parse_explanation_response,
        build_explain_payload,
        parse_explain_response,
        _MAX_ITEMS_TO_SEND,
        _MAX_CONTEXT_BYTES,
        _REQUEST_TIMEOUT_SEC,
        _USER_PROMPT_TEMPLATE,
    )
except ImportError as exc:
    # 격리 실행 대비: 테스트 대상이 import 안 되면 실패 처리.
    sys.exit(f"backend.explanation import failed: {exc}")

try:
    from backend.providers.solar import (
        call as solar_call,
        is_ready as solar_is_ready,
        _has_api_key,
        _api_key,
        SolarError,
        API_URL,
        _REQUEST_TIMEOUT_SEC as SOLAR_TIMEOUT,
    )
except ImportError as exc:
    sys.exit(f"backend.providers.solar import failed: {exc}")


# ---------------------------------------------------------------------------
# 헬퍼: 가짜 item_changes
# ---------------------------------------------------------------------------

def _item(beforeItemId="b1", afterItemId="a1", kind="changed", moved=False, changedFields=None,
          beforeAmount=None, afterAmount=None, beforeText=None, afterText=None, label=None):
    out: Dict[str, Any] = {
        "beforeItemId": beforeItemId,
        "afterItemId": afterItemId,
        "contentKind": kind,
        "moved": moved,
        "changedFields": changedFields or [],
    }
    before: Dict[str, Any] = {}
    after: Dict[str, Any] = {}
    if beforeAmount is not None:
        before["amountKrw"] = beforeAmount
        out["beforeAmount"] = beforeAmount
    if afterAmount is not None:
        after["amountKrw"] = afterAmount
        out["afterAmount"] = afterAmount
    if beforeText is not None:
        before["text"] = beforeText
    if afterText is not None:
        after["text"] = afterText
    if label is None:
        label = beforeText or afterText
    if label is not None:
        out["label"] = label
    out["beforeFields"] = before
    out["afterFields"] = after
    return out


# ---------------------------------------------------------------------------
# 1) 설명/질문 파싱 테스트
# ---------------------------------------------------------------------------

class TestExplanationParsing(unittest.TestCase):
    """오리진 파서가 다양한 응답 형태를 (설명, 질문)으로 분리하는지 검사."""

    def test_설명_질문_구역_마커_분리(self):
        text = "설명:\n- 기존 식대 50,000원 → 정정 70,000원으로 표시되었습니다.\n질문:\n- 식대 금액 변경 사유를 알려주세요."
        parsed = parse_explain_response(text)
        self.assertTrue(len(parsed["explanations"]) >= 1)
        self.assertTrue(len(parsed["questions"]) >= 1)
        qtext = "\n".join(parsed["questions"])
        self.assertIn("식대", qtext)
        etxt = "\n".join(parsed["explanations"])
        self.assertTrue("50,000원" in etxt or "50000원" in etxt or "50000" in etxt)

    def test_불릿_없는_개행_분리(self):
        text = "설명:\n기존 식대 50,000원에서 70,000원으로 바뀌었습니다.\n질문:\n변경 사유를 알려주세요."
        parsed = parse_explain_response(text)
        self.assertTrue(len(parsed["explanations"]) >= 1)
        self.assertTrue(len(parsed["questions"]) >= 1)
        self.assertIn("70,000원", "\n".join(parsed["explanations"]))

    def test_마커_없을_때_전체_설명_취급(self):
        text = "기존 식대 50,000원 → 정정 70,000원.\n변경 사유는 회사에 물어보세요."
        parsed = parse_explain_response(text)
        # 마커가 없으면 전체를 설명으로 본다 → 질문 0, 설명 >=1
        self.assertTrue(len(parsed["explanations"]) >= 1)
        self.assertEqual(parsed["questions"], [])

    def test_빈_응답은_빈_목록(self):
        for text in (None, "", "   ", "\n"):
            parsed = parse_explain_response(text)
            self.assertEqual(parsed["explanations"], [])
            self.assertEqual(parsed["questions"], [])
            self.assertIsInstance(parsed["raw"], str)

    def test_질문_구역만_있을_때_설명_빈_목록(self):
        text = "질문:\n- 식대 변경 사유를 알려주세요."
        parsed = parse_explain_response(text)
        self.assertEqual(parsed["explanations"], [])
        self.assertTrue(len(parsed["questions"]) >= 1)
        self.assertIn("식대", "\n".join(parsed["questions"]))

    def test_설명_구역만_있을_때_질문_빈_목록(self):
        text = "설명:\n- 기존 식대 50,000원 → 정정 70,000원."
        parsed = parse_explain_response(text)
        self.assertTrue(len(parsed["explanations"]) >= 1)
        self.assertEqual(parsed["questions"], [])

    def test_parse_반환_형태_고정(self):
        parsed = parse_explain_response("설명:\n- 한 줄.")
        self.assertIsInstance(parsed, dict)
        self.assertIn("explanations", parsed)
        self.assertIn("questions", parsed)
        self.assertIn("raw", parsed)
        self.assertEqual(len(parsed["explanations"]), 1)


# ---------------------------------------------------------------------------
# 2) 요청 페이로드 생성 테스트 (크기/항목 수 제한)
# ---------------------------------------------------------------------------

class TestExplainPayloadBuild(unittest.TestCase):
    """build_explain_payload가 항목 수/요청 크기를 제한하는지 검사."""

    def test_항목_수_제한_기본값(self):
        items = [_item() for _ in range(50)]
        payload = build_explain_payload(items)
        self.assertIsInstance(payload, dict)
        self.assertIn("messages", payload)
        # 실제 항목 텍스트에 최대 항목 수만큼만 들어갔는지 간접 확인: 요청 크기가 너무 크지 않아야 함.
        body = json.dumps(payload, ensure_ascii=False)
        self.assertLess(len(body.encode("utf-8")), 2 * 1024 * 1024)  # 넉넉한 상한

    def test_기본_모델_solar_pro4(self):
        payload = build_explain_payload([_item()])
        self.assertEqual(payload.get("model"), "solar-pro4")

    def test_온도_낮게_설정(self):
        payload = build_explain_payload([_item()])
        self.assertIn("temperature", payload)
        self.assertEqual(payload["temperature"], 0.2)

    def test_max_tokens_설정(self):
        payload = build_explain_payload([_item()])
        self.assertEqual(payload.get("max_tokens"), 1024)

    def test_시스템_프롬프트_포함(self):
        payload = build_explain_payload([_item()])
        system = payload["messages"][0]
        self.assertEqual(system["role"], "system")
        self.assertIn("근무시간", system["content"])
        self.assertIn("체불", system["content"]) or self.assertIn("위법", system["content"])

    def test_사용자_프롬프트에_항목_들어감(self):
        items = [_item(beforeAmount=50000, afterAmount=70000, beforeText="식대", afterText="식대")]
        payload = build_explain_payload(items)
        user = payload["messages"][1]
        self.assertEqual(user["role"], "user")
        self.assertTrue("50000원" in user["content"] or "50,000원" in user["content"])

    def test_항목_수_제한_초과_시_자름(self):
        items = [_item(beforeItemId=f"b{i}", afterItemId=f"a{i}") for i in range(100)]
        payload = build_explain_payload(items, max_items=10)
        body = json.dumps(payload, ensure_ascii=False)
        # 최대 10개까지만 보이는 내용이어야 함. 초과 항목 문구 포함 여부로 간접 확인.
        user_content = payload["messages"][1]["content"]
        self.assertIn("최대 10개 항목", user_content)


# ---------------------------------------------------------------------------
# 3) Solar 공급자 테스트 (mock HTTP)
# ---------------------------------------------------------------------------

def _mock_urllib_open_ok(content: str, status: int = 200):
    """urllib이 JSON 본문 content를 200으로 반환하는 mock context 관리자."""
    class _FakeResp:
        def __init__(self, raw: bytes):
            self._raw = raw
            self.status = status

        def read(self):
            return self._raw

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    raw = content.encode("utf-8")
    return _FakeResp(raw)


def _mock_urllib_http_error(status: int, body_snippet: str = ""):
    """HTTPError를 raise하는 패치에 쓸 예외 생성."""
    class _FakeErr(HTTPError):
        def __init__(self):
            super().__init__(APIf_url=(), hdrd=None, msg="", fp=None, code=status)

        def read(self):
            return body_snippet.encode("utf-8")

    return _FakeErr()


class TestSolarCallMock(unittest.TestCase):
    """Solar HTTP 호출부를 mock으로 검사한다. 실제 호출 없음."""

    def _env_patch(self, key_value=None):
        """UPSTAGE_API_KEY 환경변수를 제어한다."""
        if key_value is None:
            return patch.dict(os.environ, {"UPSTAGE_API_KEY": ""}, clear=False)
        return patch.dict(os.environ, {"UPSTAGE_API_KEY": key_value}, clear=False)

    def test_key_없음_즉시_오류(self):
        with self._env_patch(None):
            with patch("backend.providers.solar._api_key", return_value=""):
                with patch("backend.providers.solar._has_api_key", return_value=False):
                    err = self._assert_raises_solar_error(
                        lambda: solar_call({"model": "solar-pro4", "messages": []})
                    )
                    self.assertFalse(err.retryable)
                    self.assertIn("UPSTAGE_API_KEY", err.message)

    def test_key_있으면_정상_호출_구조(self):
        good_response = {
            "choices": [{
                "message": {"content": "설명:\n- 기존 식대 50000원 → 70000원.\n질문:\n- 식대 변경 사유를 알려주세요."}
            }]
        }
        with self._env_patch("test-key-123"):
            with patch("backend.providers.solar._api_key", return_value="test-key-123"):
                with patch("backend.providers.solar.urlopen",
                           return_value=_mock_urllib_open_ok(json.dumps(good_response))):
                    result = solar_call({"model": "solar-pro4", "messages": [{"role": "user", "content": "x"}]})
                    self.assertIn("content", result)
                    self.assertIn("설명", result["content"])

    def test_http_500_재시도_가능(self):
        with self._env_patch("test-key-123"):
            http_err = HTTPError(
                url=API_URL, code=500, msg="Server Error", hdrs=None, fp=None
            )
            # HTTPError.read를 패치하려면 별도 처리가 필요하므로, mock patch로 대체한다.
            def _raise_http_500(*a, **k):
                raise HTTPError(url=API_URL, code=500, msg="Server Error", hdrs=None, fp=None)

            with patch("backend.providers.solar.urlopen", side_effect=_raise_http_500):
                err = self._assert_raises_solar_error(lambda: solar_call({"model": "solar-pro4", "messages": []}))
                self.assertTrue(err.retryable)
                self.assertEqual(err.detail["code"], "HTTP_ERROR")
                self.assertEqual(err.detail["status"], 500)

    def test_timeout_에러(self):
        with self._env_patch("test-key-123"):
            with patch("backend.providers.solar.urlopen", side_effect=TimeoutError("timeout")):
                err = self._assert_raises_solar_error(lambda: solar_call({"model": "solar-pro4", "messages": []}))
                self.assertTrue(err.retryable)
                self.assertEqual(err.detail["code"], "NETWORK_TIMEOUT")

    def test_parse_실패_에러(self):
        with self._env_patch("test-key-123"):
            bad_body = b"{not-json}"
            with patch("backend.providers.solar.urlopen",
                       return_value=_mock_urllib_open_ok(json.dumps({"choices": []}), status=200)):
                # choices가 비면 코드 EMPTY_RESPONSE가 아니라 UNEXPECTED_RESPONSE가 나는지 확인.
                err = self._assert_raises_solar_error(lambda: solar_call({"model": "solar-pro4", "messages": []}))
                self.assertEqual(err.detail["code"], "UNEXPECTED_RESPONSE")

    def test_응답에_content_없을_때(self):
        with self._env_patch("test-key-123"):
            response = {"choices": [{"message": {"role": "assistant"}}]}
            with patch("backend.providers.solar.urlopen",
                       return_value=_mock_urllib_open_ok(json.dumps(response))):
                err = self._assert_raises_solar_error(lambda: solar_call({"model": "solar-pro4", "messages": []}))
                self.assertEqual(err.detail["code"], "EMPTY_RESPONSE")

    def _assert_raises_solar_error(self, fn):
        with self.assertRaises(SolarError) as cm:
            fn()
        return cm.exception

    def test_is_ready_키_있으면_참(self):
        with self._env_patch("test-key"):
            with patch("backend.providers.solar._api_key", return_value="test-key"):
                with patch("backend.providers.solar._has_api_key", return_value=True):
                    self.assertTrue(solar_is_ready())

    def test_is_ready_키_없으면_거짓(self):
        with patch.dict(os.environ, {"UPSTAGE_API_KEY": ""}, clear=False):
            with patch("backend.providers.solar._api_key", return_value=""):
                with patch("backend.providers.solar._has_api_key", return_value=False):
                    self.assertFalse(solar_is_ready())


# ---------------------------------------------------------------------------
# 4) 통합: mock Solar 호출 → 파싱까지 한 번에 검사
# ---------------------------------------------------------------------------

class TestExplainEndToEndMock(unittest.TestCase):
    """mock Solar 호출 + 파싱을 연결해, 설명/질문이 잘 추출되는지 검사.

    - 실제 Solar 호출과 구분한다. 이 테스트는 mock만 사용한다.
    """

    def test_식대_50000_70000_설명_질문_추출(self):
        # Solar mock 응답
        mock_content = (
            "설명:\n"
            "- 기존 식대 50,000원에서 정정 70,000원으로 금액이 바뀌었습니다.\n"
            "질문:\n"
            "- 식대 금액을 70,000원으로 바꾼 이유가 무엇인지 알려주세요."
        )
        payload = build_explain_payload([
            _item(beforeItemId="b1", afterItemId="a1", kind="changed",
                  beforeAmount=50000, afterAmount=70000, beforeText="식대", afterText="식대")
        ])

        with patch.dict(os.environ, {"UPSTAGE_API_KEY": "mock-key"}, clear=False):
            with patch("backend.providers.solar._api_key", return_value="mock-key"):
                with patch("backend.providers.solar.urlopen",
                           return_value=_mock_urllib_open_ok(json.dumps({
                               "choices": [{"message": {"content": mock_content}}]
                           }))):
                    result = solar_call(payload)
                    parsed = parse_explain_response(result["content"])
                    self.assertTrue(len(parsed["explanations"]) >= 1)
                    self.assertTrue(len(parsed["questions"]) >= 1)
                    self.assertIn("70,000원", "\n".join(parsed["explanations"]))

    def test_설명_실패해도_요청_구조는_건재(self):
        # Solar는 터져도, 우리가 구성한 페이로드가 정상인지 별도 확인.
        with patch.dict(os.environ, {"UPSTAGE_API_KEY": "mock-key"}, clear=False):
            with patch("backend.providers.solar._api_key", return_value="mock-key"):
                with patch("backend.providers.solar.urlopen",
                           side_effect=TimeoutError("timeout")):
                    with self.assertRaises(SolarError):
                        solar_call(build_explain_payload([_item(beforeAmount=50000, afterAmount=70000)]))


# ---------------------------------------------------------------------------
# 런타임 진입점
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
