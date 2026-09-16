# -*- coding: utf-8 -*-
"""
요청/응답 계약 (Pydantic v2).
- 요청 본문, 결과, 키, 개인정보는 로그로 남기지 않는다.
- 필드 오류는 code/messageKey/fieldErrors 형태로만 반환한다.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def _uuid4() -> str:
    return str(uuid4())


# ---------------------------------------------------------------------------
# 공통
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    code: str
    messageKey: str
    retryable: bool = False
    fieldErrors: List[Dict[str, Any]] = []


class ErrorBody(BaseModel):
    requestId: str
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = "ok"
    buildId: str = "dev"
    engineVersion: str = "1.0.0"
    paidFeaturesEnabled: bool = False


class ExplainRequest(BaseModel):
    """POST /api/explain 요청 계약."""

    requestId: str
    versionKey: str = "explain-v1"
    items: List[Dict[str, Any]] = []
    maxItems: int = 30

    @field_validator("requestId")
    @classmethod
    def _request_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("REQUEST_ID_REQUIRED")
        return v

    @field_validator("items")
    @classmethod
    def _items_list(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(v, list):
            raise ValueError("ITEMS_NOT_LIST")
        return v

    @field_validator("maxItems")
    @classmethod
    def _max_items_range(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("MAX_ITEMS_OUT_OF_RANGE")
        return v


class ExplainResponse(BaseModel):
    """POST /api/explain 성공 응답."""

    requestId: str
    versionKey: str
    explanations: List[str] = []
    questions: List[str] = []
    error: Dict[str, Any] | None = None


class ExplainErrorBody(BaseModel):
    requestId: str
    error: ErrorDetail


# ---------------------------------------------------------------------------
# 출처(locators)
# ---------------------------------------------------------------------------

class SourceLocator(BaseModel):
    """문서 내 위치 정보.

    항목을 식별할 수 있는 최소 위치만 담는다. 모르는 값은 null로 두고,
    필드를 삭제하지 않는다(누락과 모름은 다름).
    """

    page: Optional[int] = None
    itemId: Optional[str] = None
    excerpt: Optional[str] = None

    @field_validator("page")
    @classmethod
    def _page_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (not isinstance(v, int) or v < 1):
            raise ValueError("PAGE_INVALID")
        return v

    @field_validator("itemId")
    @classmethod
    def _item_id_or_null(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not isinstance(v, str) or not v.strip()):
            raise ValueError("ITEM_ID_INVALID")
        return v

    @field_validator("excerpt")
    @classmethod
    def _excerpt_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not isinstance(v, str):
                raise ValueError("EXCERPT_INVALID")
            if len(v) > 500:
                raise ValueError("EXCERPT_TOO_LONG")
        return v


# ---------------------------------------------------------------------------
# 문서 모델
# ---------------------------------------------------------------------------

class Period(BaseModel):
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def _date_ymd(cls, v: str) -> str:
        if len(v) != 10:
            raise ValueError("DATE_FORMAT")
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("DATE_FORMAT")
        return v

    @field_validator("start", "end")
    @classmethod
    def _date_ordered(cls, v: str) -> str:
        # start <= end는 상위 검증에서 검사
        return v


class FieldValue(BaseModel):
    amountKrw: Optional[int] = None
    minutes: Optional[int] = None
    rateKrw: Optional[int] = None
    text: Optional[str] = None

    def model_dump(self, mode: str = "python", **kwargs) -> Dict[str, Any]:
        data = super().model_dump(mode=mode, exclude_none=False, **kwargs)
        return {k: v for k, v in data.items() if k in self.model_fields_set}


class SourceRef(BaseModel):
    """문서 항목의 원문 출처 참조.

    요청/응답 양쪽에서 형태를 유지한다.
    - sourceId: 비빈 문자열만 허용(빈값 거절).
    - locator.page: 있으면 1 이상 정수, 모르면 null.
    - locator.itemId: 비빈 문자열 또는 null.
    - locator.excerpt: 최대 500자 문자열 또는 null.
    - 출처가 없으면 [].
    - id/type/location/note는 더 이상 사용하지 않는다.
    """

    sourceId: str = Field(..., min_length=1)
    locator: SourceLocator = Field(default_factory=SourceLocator)

    @field_validator("sourceId")
    @classmethod
    def _source_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("SOURCE_ID_REQUIRED")
        return v


class Item(BaseModel):
    id: str
    key: Optional[str] = None
    label: Optional[str] = None
    position: Optional[int] = None
    fields: FieldValue = FieldValue()
    sourceRefs: List[SourceRef] = []

    def model_dump(self, mode: str = "python", **kwargs) -> Dict[str, Any]:
        data = super().model_dump(mode=mode, **kwargs)
        if "fields" in data and isinstance(data["fields"], dict):
            data["fields"] = self.fields.model_dump(mode=mode, **kwargs)
        return data


class Section(BaseModel):
    key: str
    items: List[Item] = []


class DocumentPayload(BaseModel):
    documentId: str
    employmentKey: str
    period: Period
    revisionKey: str
    sections: List[Section] = []


class ConfirmedMapping(BaseModel):
    beforeItemId: str
    afterItemId: str


class ComparePayload(BaseModel):
    """POST /api/compare의 payload 안쪽."""

    mode: str = Field(default="revision")
    before: Optional[DocumentPayload] = None
    after: Optional[DocumentPayload] = None
    confirmedMappings: List[ConfirmedMapping] = []


class CompareRequest(BaseModel):
    """POST /api/compare 요청 계약.

    - schemaVersion: 현재는 1만 허용.
    - requestId: 클라이언트가 주는 UUID 문자열.
    - versionKey: 문서 버전 식별자.
    - payload: mode, before, after, confirmedMappings 포함.
    """
    schemaVersion: int = Field(default=1, ge=1, le=1)
    requestId: str = Field(default_factory=_uuid4)
    versionKey: str
    payload: ComparePayload


# ---------------------------------------------------------------------------
# 응답 모델
# ---------------------------------------------------------------------------

class ItemChangeResult(BaseModel):
    contentKind: str
    moved: bool
    beforeItemId: Optional[str] = None
    afterItemId: Optional[str] = None
    beforeFields: Optional[FieldValue] = None
    afterFields: Optional[FieldValue] = None
    beforeSourceRefs: Optional[List[SourceRef]] = None
    afterSourceRefs: Optional[List[SourceRef]] = None
    changedFields: List[str] = []
    reasonCode: Optional[str] = None

    def model_dump(self, mode: str = "python", **kwargs) -> Dict[str, Any]:
        data = super().model_dump(mode=mode, **kwargs)
        if data.get("beforeFields") is not None and isinstance(data["beforeFields"], dict):
            f = self.beforeFields
            data["beforeFields"] = f.model_dump(mode=mode, **kwargs) if f is not None else None
        if data.get("afterFields") is not None and isinstance(data["afterFields"], dict):
            f = self.afterFields
            data["afterFields"] = f.model_dump(mode=mode, **kwargs) if f is not None else None
        return data


class CompareResultData(BaseModel):
    """POST /api/compare 성공 시 data 필드."""

    comparisonKind: str = "revision"
    sameEmployment: bool = True
    samePeriod: bool = True
    summary: Dict[str, Any] = {}
    itemChanges: List[ItemChangeResult] = []
    warnings: List[str] = []

    def model_dump(self, mode: str = "python", **kwargs) -> Dict[str, Any]:
        data = super().model_dump(mode=mode, **kwargs)
        data["itemChanges"] = [
            ic.model_dump(mode=mode, **kwargs) if isinstance(ic, ItemChangeResult) else ic
            for ic in self.itemChanges
        ]
        return data
