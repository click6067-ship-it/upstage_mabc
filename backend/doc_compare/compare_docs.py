#!/usr/bin/env python3
"""
문서 비교 스크립트 (매칭 중심 개정판)

|- ## 헤딩으로 섹션 분할
|- 각 섹션 내에서 번호 항목(1. 2. ...)과 일반 문단을 구분
|- 번호 항목 비교:
  * 정규화 텍스트가 같으면 내용 동일 → 순서 변경 가능 (내용 변경 아님)
  * 번호가 같은데 정규화 텍스트가 다르면 변경
  * 번호가 다른데 정규화 텍스트가 같으면 순서 변경
  * 새 문서에만 있는 번호 → 추가
  * 구 문서에만 있는 번호 → 삭제
|- 번호 항목이 없는 섹션은 정규화 본문 텍스트로 비교
|- 마지막에 추가·삭제·변경·순서 변경 건수와 "변경 0건" 명시
|- 파일 없음/폴더/UTF-8 오류는 traceback 없이 짧게 안내하고 종료 코드 2
"""

import re
import sys
from collections import OrderedDict
from typing import List, Tuple, Optional, Dict, Set


# ---------- 정규화 ----------

def normalize_text(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n+", "\n", t)
    return t.strip()


# ---------- 파싱 ----------

def parse_sections(path: str) -> OrderedDict:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    sections: OrderedDict = OrderedDict()
    current_section: Optional[str] = None
    current_items: List[Tuple[Optional[int], str]] = []
    current_body: List[str] = []

    heading_re = re.compile(r"^##\s+(.+)$")
    item_re = re.compile(r"^\s*(\d+)\.\s+(.+)$")

    def flush():
        nonlocal current_section, current_items, current_body
        if current_section is not None:
            sections[current_section] = {
                "raw_title": current_section,
                "items": list(current_items),
                "body_lines": list(current_body),
            }

    for line in lines:
        stripped = line.rstrip("\n\r")
        m_heading = heading_re.match(stripped)
        if m_heading:
            flush()
            current_section = m_heading.group(1).strip()
            current_items = []
            current_body = []
            continue
        if current_section is None:
            continue
        m_item = item_re.match(stripped)
        if m_item:
            num = int(m_item.group(1))
            text = m_item.group(2).strip()
            current_items.append((num, text))
        else:
            current_body.append(stripped)

    flush()
    return sections


# ---------- 번호 항목 매칭 ----------

def match_numbered_items(
    old_items: List[Tuple[Optional[int], str]],
    new_items: List[Tuple[Optional[int], str]],
) -> Dict:
    """
    구/신 항목에서 매칭된 항목을 각각 제외한 뒤 남은 항목끼리
    변경/추가/삭제를 분류한다. 같은 항목을 두 번 사용하지 않는다.
    본문 비교와 무관하게 번호 항목만 처리한다.
    """
    old = {num: text for num, text in old_items if num is not None}
    new = {num: text for num, text in new_items if num is not None}

    old_norm = {num: normalize_text(text) for num, text in old.items()}
    new_norm = {num: normalize_text(text) for num, text in new.items()}

    old_nums = set(old_norm)
    new_nums = set(new_norm)

    # 1. 같은 번호 + 같은 정규화 텍스트 → same_unmoved (변경도 이동도 아님)
    same_unmoved: Set[int] = set()
    for num in sorted(old_nums & new_nums):
        if old_norm[num] == new_norm[num]:
            same_unmoved.add(num)

    # 매칭에 소모된 번호 집합
    used_old: Set[int] = set(same_unmoved)
    used_new: Set[int] = set(same_unmoved)

    # 2. 정규화 텍스트가 같은 구/신 항목을 짝지어 순서 변경(이동)으로 처리
    #    (같은 내용을 두 번 쓰지 않도록 구/신에서 각각 소모)
    #    여러 후보가 있으면 번호 오름차순 쌍으로 묶어 일관되게 이동만 만든다.
    old_nums_by_norm: Dict[str, List[int]] = {}
    for num in old_nums - used_old:
        old_nums_by_norm.setdefault(old_norm[num], []).append(num)
    new_nums_by_norm: Dict[str, List[int]] = {}
    for num in new_nums - used_new:
        new_nums_by_norm.setdefault(new_norm[num], []).append(num)

    order_changes: List[Tuple[int, int]] = []
    for norm, old_candidates in old_nums_by_norm.items():
        new_candidates = new_nums_by_norm.get(norm, [])
        for old_num, new_num in zip(sorted(old_candidates), sorted(new_candidates)):
            order_changes.append((old_num, new_num))
            used_old.add(old_num)
            used_new.add(new_num)

    # 3. 같은 번호인데 텍스트가 다른 항목 → 변경
    changed: List[Tuple[int, str, str]] = []
    for num in sorted(old_nums & new_nums):
        if num in used_old or num in used_new:
            continue
        changed.append((num, old[num], new[num]))
        used_old.add(num)
        used_new.add(num)

    # 4. 남은 구 항목 → 삭제
    deleted: List[Tuple[int, str]] = []
    for num in sorted(old_nums - used_old):
        deleted.append((num, old[num]))

    # 5. 남은 신 항목 → 추가
    added: List[Tuple[int, str]] = []
    for num in sorted(new_nums - used_new):
        added.append((num, new[num]))

    return {
        "changed": changed,
        "added": added,
        "deleted": deleted,
        "order_changes": order_changes,
        "same_unmoved": [(num, old[num]) for num in sorted(same_unmoved)],
    }


# ---------- 섹션 비교 ----------

def compare_sections(
    old_sections: OrderedDict,
    new_sections: OrderedDict,
) -> Dict:
    old_keys = list(old_sections.keys())
    new_keys = list(new_sections.keys())

    added_sections = [k for k in new_keys if k not in old_sections]
    deleted_sections = [k for k in old_keys if k not in new_sections]
    common_sections = [k for k in old_keys if k in new_sections]

    added_items = []       # (sec, num, text)
    deleted_items = []     # (sec, num, text)
    changed_items = []     # (sec, num, old_text, new_text)
    order_changes = []     # (sec, old_num, new_num)
    changed_sections = []  # (sec, old_body_norm, new_body_norm)

    for sec in common_sections:
        old = old_sections[sec]
        new = new_sections[sec]

        old_items = old["items"]
        new_items = new["items"]

        old_body_norm = normalize_text("\n".join(old["body_lines"]))
        new_body_norm = normalize_text("\n".join(new["body_lines"]))
        body_changed = old_body_norm != new_body_norm

        match_result = match_numbered_items(old_items, new_items)

        for num, text in match_result["added"]:
            added_items.append((sec, num, text))
        for num, text in match_result["deleted"]:
            deleted_items.append((sec, num, text))
        for num, old_text, new_text in match_result["changed"]:
            changed_items.append((sec, num, old_text, new_text))
        for old_num, new_num in match_result["order_changes"]:
            order_changes.append((sec, old_num, new_num))

        if body_changed:
            changed_sections.append((sec, old_body_norm, new_body_norm))

    return {
        "added_sections": added_sections,
        "deleted_sections": deleted_sections,
        "added_items": added_items,
        "deleted_items": deleted_items,
        "changed_items": changed_items,
        "order_changes": order_changes,
        "changed_sections": changed_sections,
        "old_items_by_sec": {sec: old_sections[sec]["items"] for sec in common_sections if sec in old_sections},
        "new_items_by_sec": {sec: new_sections[sec]["items"] for sec in common_sections if sec in new_sections},
    }


# ---------- 출력 ----------

def analyze_change_note(old_text: str, new_text: str) -> str:
    notes = []
    # 괄호 신설: 구문에 괄호가 없었는데 신규 문구에 괄호가 생긴 경우
    if "(" in new_text and "(" not in old_text and ")" in new_text:
        notes.append("적용 범위 괄호 신설")
    # 기존 조정 가능 문구 삭제
    if "조정할 수 있다" in old_text and "조정할 수 있다" not in new_text:
        notes.append("기존 '조정 가능' 문구 삭제")
    return "; ".join(notes) if notes else ""


def build_report(old_path: str, new_path: str, result: Dict) -> str:
    lines = []
    lines.append(f"=== 문서 비교: {old_path} → {new_path} ===\n")

    lines.append("[추가된 섹션]")
    if not result["added_sections"]:
        lines.append("  (없음)")
    for sec in sorted(result["added_sections"]):
        lines.append(f"  {sec}")
    lines.append("")

    lines.append("[삭제된 섹션]")
    if not result["deleted_sections"]:
        lines.append("  (없음)")
    for sec in sorted(result["deleted_sections"]):
        lines.append(f"  {sec}")
    lines.append("")

    lines.append("[추가된 항목]")
    if not result["added_items"]:
        lines.append("  (없음)")
    for sec, num, text in sorted(result["added_items"]):
        short = text[:60] + ("…" if len(text) > 60 else "")
        lines.append(f"  {sec} {num}항: {short}")
    lines.append("")

    lines.append("[삭제된 항목]")
    if not result["deleted_items"]:
        lines.append("  (없음)")
    for sec, num, text in sorted(result["deleted_items"]):
        short = text[:60] + ("…" if len(text) > 60 else "")
        lines.append(f"  {sec} {num}항: {short}")
    lines.append("")

    lines.append("[변경된 항목 (번호 기준)]")
    if not result["changed_items"]:
        lines.append("  (없음)")
    for sec, num, old_text, new_text in result["changed_items"]:
        lines.append(f"  {sec} {num}항:")
        lines.append(f"    구: {old_text}")
        lines.append(f"    신: {new_text}")
    lines.append("")

    lines.append("[변경된 섹션 (본문 기준)]")
    if not result["changed_sections"]:
        lines.append("  (없음)")
    for sec, old_body, new_body in result["changed_sections"]:
        old_preview = old_body[:80] + ("…" if len(old_body) > 80 else "")
        new_preview = new_body[:80] + ("…" if len(new_body) > 80 else "")
        lines.append(f"  {sec}:")
        lines.append(f"    구 본문 일부: {old_preview}")
        lines.append(f"    신 본문 일부: {new_preview}")
    lines.append("")

    if result["order_changes"]:
        lines.append("[순서 변경 (변경으로 미계수)]")
        for sec, old_num, new_num in result["order_changes"]:
            old_text = ""
            new_text = ""
            for on, t in result["old_items_by_sec"].get(sec, []):
                if on == old_num:
                    old_text = t
                    break
            for nn, t in result["new_items_by_sec"].get(sec, []):
                if nn == new_num:
                    new_text = t
                    break
            lines.append(f"  {sec}: {old_num}항 → {new_num}항 위치로 이동 (내용 동일, 변경 미계수)")
            if old_text:
                lines.append(f"    구: {old_text}")
            if new_text:
                lines.append(f"    신: {new_text}")
        lines.append("")

    lines.append("=== 주의할 변화 요약 ===")
    idx = 1
    for sec in sorted(result["added_sections"]):
        lines.append(f"{idx}. [{sec}] — 신규 섹션 추가")
        idx += 1
    for sec, num, text in sorted(result["added_items"]):
        lines.append(f"{idx}. [{sec} {num}항] 신설: {text[:80]}")
        idx += 1
    for sec, num, old_text, new_text in result["changed_items"]:
        note = analyze_change_note(old_text, new_text)
        if note:
            lines.append(f"{idx}. [{sec} {num}항] 변경: {note}")
        else:
            lines.append(f"{idx}. [{sec} {num}항] 변경: 텍스트 변경 (구→신)")
        idx += 1
    for sec, old_body, new_body in result["changed_sections"]:
        lines.append(f"{idx}. [{sec}] 본문 변경 (구→신)")
        idx += 1
    for sec in sorted(result["deleted_sections"]):
        lines.append(f"{idx}. [{sec}] — 섹션 전체 삭제")
        idx += 1
    for sec, num, text in sorted(result["deleted_items"]):
        lines.append(f"{idx}. [{sec} {num}항] 삭제: {text[:80]}")
        idx += 1
    if idx == 1:
        lines.append("  (주의할 변화 없음)")

    added_sec_cnt = len(result["added_sections"])
    deleted_sec_cnt = len(result["deleted_sections"])
    added_item_cnt = len(result["added_items"])
    deleted_item_cnt = len(result["deleted_items"])
    changed_sec_cnt = len(result["changed_sections"])
    changed_item_cnt = len(result["changed_items"])
    order_cnt = len(result["order_changes"])

    lines.append("")
    lines.append("=== 요약 ===")
    lines.append(f"추가: 섹션 {added_sec_cnt}건, 항목 {added_item_cnt}건")
    lines.append(f"삭제: 섹션 {deleted_sec_cnt}건, 항목 {deleted_item_cnt}건")
    lines.append(f"변경: 섹션 {changed_sec_cnt}건, 항목 {changed_item_cnt}건")
    lines.append(f"순서 변경: {order_cnt}건 (변경으로 미계수)")

    total = (added_sec_cnt + deleted_sec_cnt + added_item_cnt + deleted_item_cnt
             + changed_sec_cnt + changed_item_cnt)

    if total == 0 and order_cnt == 0:
        lines.append("변경 0건 — 두 문서는 동일합니다.")
    else:
        lines.append(f"실제 변경 건수 (순서 변경 제외): {total}건")

    return "\n".join(lines)


# ---------- 메인 ----------

def safe_open(path: str) -> OrderedDict:
    try:
        return parse_sections(path)
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없음: {path}", file=sys.stderr)
        sys.exit(2)
    except IsADirectoryError:
        print(f"오류: 폴더임: {path}", file=sys.stderr)
        sys.exit(2)
    except UnicodeDecodeError as e:
        print(f"오류: UTF-8 인코딩이 아님: {path} ({e})", file=sys.stderr)
        sys.exit(2)


def main():
    if len(sys.argv) != 3:
        print("사용법: python3 compare_docs.py <구버전> <신버전>", file=sys.stderr)
        sys.exit(1)

    old_path = sys.argv[1]
    new_path = sys.argv[2]

    old_sections = safe_open(old_path)
    new_sections = safe_open(new_path)

    result = compare_sections(old_sections, new_sections)
    print(build_report(old_path, new_path, result))


if __name__ == "__main__":
    main()
