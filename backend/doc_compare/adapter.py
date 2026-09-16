# -*- coding: utf-8 -*-
"""
문서 비교 실행 어댑터.

- 기존 compare_docs.py(Task A에서 개선됨)의 매칭 원칙을 구조화된 문서 모델로 옮긴다.
- 금액/위치/키 유사성만으로 동일 항목 확정하지 않는다.
- 명시적 1:1 confirmedMappings와 동일 item.key로만 대응을 확립한다.
- 모호하면 unresolved로 남긴다.
- 중복 item.id / item.key를 dict로 덮어쓰지 않는다. 지원 불가 중복/충돌은 거절한다.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from backend.contracts import (
    CompareResultData,
    ConfirmedMapping,
    DocumentPayload,
    FieldValue,
    Item,
    ItemChangeResult,
    SourceRef,
)

_NUM_RE = re.compile(r"[ \t]+")
_NEWLINE_RE = re.compile(r"\n+")


def _norm_text(t: Optional[str]) -> str:
    if t is None:
        return ""
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = _NUM_RE.sub(" ", t)
    t = _NEWLINE_RE.sub("\n", t)
    return t.strip()


def _fields_equal(a: Optional[FieldValue], b: Optional[FieldValue]) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return (
        _field_value_equal(a.amountKrw, b.amountKrw)
        and _field_value_equal(a.minutes, b.minutes)
        and _field_value_equal(a.rateKrw, b.rateKrw)
        and _field_value_equal_str(a.text, b.text)
    )


def _field_value_equal(x: Optional[int], y: Optional[int]) -> bool:
    return x == y


def _field_value_equal_str(x: Optional[str], y: Optional[str]) -> bool:
    if x is None and y is None:
        return True
    if x is None or y is None:
        return False
    return x == y


def _changed_fields(a: Optional[FieldValue], b: Optional[FieldValue]) -> List[str]:
    if a is None and b is None:
        return []
    if a is None or b is None:
        names = []
        for name in ("amountKrw", "minutes", "rateKrw", "text"):
            av = getattr(a, name, None) if a is not None else None
            bv = getattr(b, name, None) if b is not None else None
            if av != bv:
                names.append(name)
        return sorted(names)
    out = []
    for name in ("amountKrw", "minutes", "rateKrw", "text"):
        a_set = name in a.model_fields_set
        b_set = name in b.model_fields_set
        if a_set and b_set:
            av = getattr(a, name)
            bv = getattr(b, name)
            if av != bv:
                out.append(name)
        elif a_set != b_set:
            out.append(name)
    return sorted(out)


class DuplicateItemId(Exception):
    def __init__(self, item_id: str) -> None:
        super().__init__(f"duplicate item id: {item_id}")
        self.item_id = item_id


class DuplicateItemKey(Exception):
    def __init__(self, key: Optional[str], section_key: str) -> None:
        super().__init__(f"duplicate item key in section {section_key}: {key}")
        self.key = key
        self.section_key = section_key


class MissingItemId(Exception):
    def __init__(self, item_id: str) -> None:
        super().__init__(f"missing item id: {item_id}")
        self.item_id = item_id


class _ItemIdIndex:
    def __init__(self) -> None:
        self._by_id: Dict[str, Item] = OrderedDict()
        self._by_key: Dict[Optional[str], List[Tuple[str, Item]]] = OrderedDict()

    def add(self, item: Item, section_key: str) -> None:
        if item.id in self._by_id:
            raise DuplicateItemId(item.id)
        self._by_id[item.id] = item
        key = item.key
        self._by_key.setdefault(key, []).append((section_key, item))

    @property
    def ids(self) -> Set[str]:
        return set(self._by_id.keys())

    def by_id(self, item_id: str) -> Item:
        try:
            return self._by_id[item_id]
        except KeyError:
            raise MissingItemId(item_id)

    def items_by_key(self, key: Optional[str]) -> List[Item]:
        out = []
        for _, item in self._by_key.get(key, []):
            out.append(item)
        return out


def _build_index(payload: DocumentPayload) -> _ItemIdIndex:
    idx = _ItemIdIndex()
    for sec in payload.sections:
        for item in sec.items:
            idx.add(item, sec.key)
    return idx


def _position_of(payload: DocumentPayload, item_id: str) -> Tuple[str, Optional[int]]:
    for sec in payload.sections:
        for item in sec.items:
            if item.id == item_id:
                return (sec.key, item.position)
    raise MissingItemId(item_id)


def _validate_mappings(
    before_idx: _ItemIdIndex,
    after_idx: _ItemIdIndex,
    mappings: Sequence[ConfirmedMapping],
) -> List[str]:
    errors: List[str] = []
    seen_before: Set[str] = set()
    seen_after: Set[str] = set()
    for m in mappings:
        if m.beforeItemId == m.afterItemId:
            errors.append("INVALID_INPUT")
            continue
        if m.beforeItemId in seen_before or m.afterItemId in seen_after:
            errors.append("DUPLICATE_MAPPING")
            continue
        try:
            before_idx.by_id(m.beforeItemId)
        except MissingItemId:
            errors.append("UNKNOWN_BEFORE_ID")
            continue
        try:
            after_idx.by_id(m.afterItemId)
        except MissingItemId:
            errors.append("UNKNOWN_AFTER_ID")
            continue
        seen_before.add(m.beforeItemId)
        seen_after.add(m.afterItemId)
    return errors


def compare_revision(
    before: DocumentPayload,
    after: DocumentPayload,
    mappings: Sequence[ConfirmedMapping],
) -> CompareResultData:
    try:
        before_idx = _build_index(before)
        after_idx = _build_index(after)
    except DuplicateItemId as exc:
        raise ValueError(f"duplicate item id: {exc.item_id}") from exc

    mapping_errs = _validate_mappings(before_idx, after_idx, mappings)
    if mapping_errs:
        raise ValueError("mapping validation failed")

    mapped_before: Dict[str, str] = {}
    mapped_after: Dict[str, str] = {}
    for m in mappings:
        mapped_before[m.beforeItemId] = m.afterItemId
        mapped_after[m.afterItemId] = m.beforeItemId

    item_changes: List[ItemChangeResult] = []
    warnings: List[str] = []

    for m in mappings:
        before_item = before_idx.by_id(m.beforeItemId)
        after_item = after_idx.by_id(m.afterItemId)
        before_pos = _position_of(before, m.beforeItemId)
        after_pos = _position_of(after, m.afterItemId)

        moved = (before_pos != after_pos)
        changed = _changed_fields(before_item.fields, after_item.fields)

        if not changed and not moved:
            content_kind = "unchanged"
            reason = "MAPPED"
        elif changed and not moved:
            content_kind = "changed"
            reason = "MAPPED"
        elif moved and not changed:
            content_kind = "unchanged"
            reason = "MAPPED"
        else:
            content_kind = "changed"
            reason = "MAPPED"

        item_changes.append(
            ItemChangeResult(
                contentKind=content_kind,
                moved=moved,
                beforeItemId=m.beforeItemId,
                afterItemId=m.afterItemId,
                beforeFields=before_item.fields,
                afterFields=after_item.fields,
                beforeSourceRefs=before_item.sourceRefs,
                afterSourceRefs=after_item.sourceRefs,
                changedFields=changed,
                reasonCode=reason,
            )
        )

    processed_after_ids: Set[str] = set(mapped_after.keys())
    processed_before_ids: Set[str] = set(mapped_before.keys())

    for before_id in before_idx.ids:
        if before_id in processed_before_ids:
            continue
        before_item = before_idx.by_id(before_id)
        after_matches = [a for a in after_idx.items_by_key(before_item.key) if a.id not in processed_after_ids]
        if after_matches:
            item_changes.append(
                ItemChangeResult(
                    contentKind="unresolved",
                    moved=False,
                    beforeItemId=before_id,
                    afterItemId=None,
                    beforeFields=before_item.fields,
                    afterFields=None,
                    beforeSourceRefs=before_item.sourceRefs,
                    afterSourceRefs=None,
                    changedFields=[],
                    reasonCode="KEY_ONLY_UNRESOLVED",
                )
            )
            chosen = after_matches[0]
            processed_after_ids.add(chosen.id)
            item_changes.append(
                ItemChangeResult(
                    contentKind="unresolved",
                    moved=False,
                    beforeItemId=None,
                    afterItemId=chosen.id,
                    beforeFields=None,
                    afterFields=chosen.fields,
                    beforeSourceRefs=None,
                    afterSourceRefs=chosen.sourceRefs,
                    changedFields=[],
                    reasonCode="KEY_ONLY_UNRESOLVED",
                )
            )
        else:
            item_changes.append(
                ItemChangeResult(
                    contentKind="deleted",
                    moved=False,
                    beforeItemId=before_id,
                    afterItemId=None,
                    beforeFields=before_item.fields,
                    afterFields=None,
                    beforeSourceRefs=before_item.sourceRefs,
                    afterSourceRefs=None,
                    changedFields=[],
                    reasonCode="DELETED",
                )
            )

    for after_id in after_idx.ids:
        if after_id in processed_after_ids:
            continue
        after_item = after_idx.by_id(after_id)
        item_changes.append(
            ItemChangeResult(
                contentKind="added",
                moved=False,
                beforeItemId=None,
                afterItemId=after_id,
                beforeFields=None,
                afterFields=after_item.fields,
                beforeSourceRefs=None,
                afterSourceRefs=after_item.sourceRefs,
                changedFields=[],
                reasonCode="ADDED",
            )
        )

    summary = _summarize(item_changes)
    if len(item_changes) > 1000:
        warnings.append("TOO_LARGE")

    return CompareResultData(
        comparisonKind="revision",
        sameEmployment=True,
        samePeriod=True,
        summary=summary,
        itemChanges=item_changes,
        warnings=warnings or [],
    )


def _summarize(item_changes: List[ItemChangeResult]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for kind in ("unchanged", "changed", "added", "deleted", "unresolved"):
        counts[kind] = 0
    moved_cnt = 0
    for ic in item_changes:
        counts[ic.contentKind] = counts.get(ic.contentKind, 0) + 1
        if ic.moved:
            moved_cnt += 1
    return {
        "totalBefore": 0,
        "totalAfter": 0,
        "matched": counts.get("unchanged", 0) + counts.get("changed", 0),
        "unchanged": counts.get("unchanged", 0),
        "changed": counts.get("changed", 0),
        "moved": moved_cnt,
        "added": counts.get("added", 0),
        "deleted": counts.get("deleted", 0),
        "unresolved": counts.get("unresolved", 0),
    }


def compare_documents(
    before: DocumentPayload,
    after: DocumentPayload,
    mappings: Sequence[ConfirmedMapping],
) -> CompareResultData:
    return compare_revision(before, after, mappings)
