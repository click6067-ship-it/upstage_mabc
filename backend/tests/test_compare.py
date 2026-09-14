#!/usr/bin/env python3
"""
문서 비교 테스트

번호 항목 매칭:
- 같은 번호 + 같은 정규화 텍스트 → same_unmoved (변경 없음)
- 번호가 다른데 정규화 텍스트 같으면 순서 변경 (변경 미계수)
- 번호가 같은데 정규화 텍스트 다르면 변경
- 새 문서에만 있는 번호 → 추가
- 구 문서에만 있는 번호 → 삭제

반례 중심 테스트:
- 이동 표기는 구번호 → 신번호 방향이어야 함
- "답변 기록 보관 기간 7일 → 14일"처럼 응답 의무 키워드가 본문에 있어도
  의무 추정 문구를 붙이면 안 됨 (원문 차이만 표시)
- 항목 이동 + 일반 문단 변경이 함께 있으면 둘 다 보고해야 함
- 같은 신항목을 이동과 변경에 중복 대응하면 안 됨
"""

import os
import re
import sys
import subprocess
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
COMPARE_SCRIPT = BACKEND_ROOT / "doc_compare" / "compare_docs.py"

PY = sys.executable


def run(doc_a: str, doc_b: str) -> tuple:
    proc = subprocess.run(
        [PY, "-B", str(COMPARE_SCRIPT), doc_a, doc_b],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def write_doc(content: str, suffix: str = ".md") -> Path:
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="dc_")
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return Path(path)


# ---------------------------------------------------------------------------
# Helper: assert changed/added/deleted/order counts from stdout
# ---------------------------------------------------------------------------

def parse_counts(stdout: str):
    changed_items = 0
    added_items = 0
    deleted_items = 0
    order_cnt = 0
    changed_sec = 0
    added_sec = 0
    deleted_sec = 0
    for line in stdout.splitlines():
        line_strip = line.strip()
        if line_strip.startswith("추가: 섹션") and "항목" in line_strip:
            m = re.search(r"추가:\s*섹션\s+(\d+)건,\s*항목\s+(\d+)건", line_strip)
            if m:
                added_sec = int(m.group(1))
                added_items = int(m.group(2))
        elif line_strip.startswith("삭제: 섹션") and "항목" in line_strip:
            m = re.search(r"삭제:\s*섹션\s+(\d+)건,\s*항목\s+(\d+)건", line_strip)
            if m:
                deleted_sec = int(m.group(1))
                deleted_items = int(m.group(2))
        elif line_strip.startswith("변경: 섹션") and "항목" in line_strip:
            m = re.search(r"변경:\s*섹션\s+(\d+)건,\s*항목\s+(\d+)건", line_strip)
            if m:
                changed_sec = int(m.group(1))
                changed_items = int(m.group(2))
        elif line_strip.startswith("순서 변경:"):
            m = re.search(r"순서 변경:\s*(\d+)건", line_strip)
            if m:
                order_cnt = int(m.group(1))

    return {
        "added_sec": added_sec,
        "added_items": added_items,
        "deleted_sec": deleted_sec,
        "deleted_items": deleted_items,
        "changed_sec": changed_sec,
        "changed_items": changed_items,
        "order_cnt": order_cnt,
    }


def parse_order_moves(stdout: str):
    """[순서 변경 (변경으로 미계수)] 블록에서 (sec, old_num, new_num) 목록을 뽑는다."""
    moves = []
    in_block = False
    for line in stdout.splitlines():
        line_strip = line.strip()
        if line_strip.startswith("[순서 변경 (변경으로 미계수)]"):
            in_block = True
            continue
        if in_block:
            if line_strip.startswith("[") and "순서 변경" not in line_strip:
                in_block = False
                continue
            # 실제 출력 예: "섹션 A: 1항 → 2항 위치로 이동 (내용 동일, 변경 미계수)"
            m = re.search(r"^\s*(.+?):\s*(\d+)항\s*→\s*(\d+)항\s+위치로\s+이동", line_strip)
            if m:
                sec = m.group(1).strip()
                old_num = int(m.group(2))
                new_num = int(m.group(3))
                moves.append((sec, old_num, new_num))
    return moves


def assert_equal(a, b, msg):
    if a != b:
        raise AssertionError(f"{msg}: 기대 {b!r}, 실제 {a!r}")


# ===========================================================================
# 1. 내용 그대로 순서만 바뀌면 이동이지 실질 변경 아님
# ===========================================================================

def test_order_change_not_counted_as_change():
    old = """## 섹션 A
1. 서울
2. 부산
3. 제주
"""
    new = """## 섹션 A
1. 제주
2. 서울
3. 부산
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["changed_items"], 0, "순서만 바뀐 경우 변경 0건")
    assert_equal(c["changed_sec"], 0, "순서만 바뀐 경우 섹션 본문 변경 0건")
    assert_equal(c["order_cnt"], 3, "순서 변경 3건 기록")
    assert "순서 변경 (변경으로 미계수)" in out
    moves = parse_order_moves(out)
    assert len(moves) == 3, f"순서 변경 3건이어야 함, 실제 {moves}"
    assert ("섹션 A", 1, 2) in moves, "구1 서울 -> 신2 서울"
    assert ("섹션 A", 2, 3) in moves, "구2 부산 -> 신3 부산"
    assert ("섹션 A", 3, 1) in moves, "구3 제주 -> 신1 제주"
    assert "실제 변경 건수 (순서 변경 제외): 0건" in out


# ===========================================================================
# 2. 번호만 바뀐 같은 항목을 추가/삭제로 중복 계산 ㄴㄴ
# ===========================================================================

def test_same_content_different_numbers_is_order_not_add_delete():
    old = """## 조항
1. 정기점검은 매월 실시한다.
"""
    new = """## 조항
2. 정기점검은 매월 실시한다.
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["added_items"], 0, "번호만 다른 동일 항목은 추가 아님")
    assert_equal(c["deleted_items"], 0, "번호만 다른 동일 항목은 삭제 아님")
    assert_equal(c["order_cnt"], 1, "순서 변경 1건으로 기록")
    assert c["changed_items"] == 0, "변경도 아님"
    assert_equal(c["changed_sec"], 0, "본문 변경도 아님")
    assert "실제 변경 건수 (순서 변경 제외): 0건" in out
    moves = parse_order_moves(out)
    assert moves == [("조항", 1, 2)], f"1 -> 2 이동만 있어야 함, 실제 {moves}"


# ===========================================================================
# 3. 회신 의무 추정 금지: 원문 차이만 보여줘야 함
#    "답변 기록 보관 기간 7일 -> 14일"처럼 응답 의무 키워드가 본문에 있어도
#    회신 의무 신설로 표시하면 안 됨
# ===========================================================================

def test_reply_obligation_must_not_be_inferred():
    old = """## 답변 기록
1. 답변 기록 보관 기간 7일
"""
    new = """## 답변 기록
1. 답변 기록 보관 기간 14일
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    # 의무 추정 문구가 들어가면 안 됨
    assert "회신 의무" not in out, "응답 의무 키워드 있다고 회신 의무로 추정하면 안 됨"
    assert "14일 이내 회신 의무 신설" not in out
    assert "구: 답변 기록 보관 기간 7일" in out
    assert "신: 답변 기록 보관 기간 14일" in out

    # 원문 차이만 보여준다는 점 확인: 실제 변경된 항목으로 분류되어야 함
    c = parse_counts(out)
    assert_equal(c["changed_items"], 1, "기간 변경은 텍스트 변경으로 분류")


# ===========================================================================
# 4. 항목 이동 + 일반 문단 변경이 함께 있으면 둘 다 보고해야 함
# ===========================================================================

def test_order_change_and_body_change_both_reported():
    old = """## 급여
1. 식대: 50,000원
2. 교통비: 20,000원

지급일 10일
"""
    new = """## 급여
1. 교통비: 20,000원
2. 식대: 50,000원

지급일 20일
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")

    c = parse_counts(out)
    # 항목 이동 2건
    assert_equal(c["order_cnt"], 2, "식대/교통비 이동 2건")
    # 일반 문단 변경 1건 (지급일 10일 -> 20일)
    assert_equal(c["changed_sec"], 1, "지급일 문단 변경 1건")
    assert "지급일 10일" in out
    assert "지급일 20일" in out

    moves = parse_order_moves(out)
    assert ("급여", 1, 2) in moves, "구1 식대 -> 신2 식대 이동"
    assert ("급여", 2, 1) in moves, "구2 교통비 -> 신1 교통비 이동"

    # 실제 변경 건수: 본문 변경 1건 (순서 변경은 미계수)
    assert "실제 변경 건수 (순서 변경 제외): 1건" in out


# ===========================================================================
# 5. 동일/추가/삭제/금액 변경 정상 사례
# ===========================================================================

def test_identical_documents_no_change():
    doc = """## 안내
1. 신청인 확인
2. 서류 제출
"""
    a = write_doc(doc)
    b = write_doc(doc)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["changed_items"], 0, "동일 문서 변경 0건")
    assert_equal(c["added_items"], 0, "추가 0건")
    assert_equal(c["deleted_items"], 0, "삭제 0건")
    assert_equal(c["order_cnt"], 0, "순서 변경 0건")
    assert "변경 0건" in out


def test_added_item():
    old = """## 안내
1. 신청인 확인
"""
    new = """## 안내
1. 신청인 확인
2. 서류 제출
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["added_items"], 1, "추가 항목 1건")
    assert_equal(c["changed_items"], 0, "변경 0건")
    assert_equal(c["deleted_items"], 0, "삭제 0건")
    assert "서류 제출" in out


def test_deleted_item():
    old = """## 안내
1. 신청인 확인
2. 서류 제출
"""
    new = """## 안내
1. 신청인 확인
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["deleted_items"], 1, "삭제 항목 1건")
    assert_equal(c["added_items"], 0, "추가 0건")
    assert_equal(c["changed_items"], 0, "변경 0건")


def test_changed_item():
    old = """## 안내
1. 신청인 확인
"""
    new = """## 안내
1. 신청인 확인 및 서명
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["changed_items"], 1, "변경 항목 1건")
    assert_equal(c["added_items"], 0, "추가 0건")
    assert "구: 신청인 확인" in out
    assert "신: 신청인 확인 및 서명" in out


def test_amount_change_is_detected():
    old = """## 급여
1. 기본 지급액: 1,000,000원
2. 연장 수당: 200,000원
"""
    new = """## 급여
1. 기본 지급액: 1,200,000원
2. 연장 수당: 200,000원
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["changed_items"], 1, "금액 변경 검출 1건")
    assert_equal(c["added_items"], 0, "추가 0건")
    assert_equal(c["deleted_items"], 0, "삭제 0건")
    assert "기본 지급액: 1,000,000원" in out
    assert "기본 지급액: 1,200,000원" in out


# ===========================================================================
# 6. 이름이 비슷하거나 금액이 같다고 같은 항목으로 합치지 않고
#    모호하면 확인 필요로 남김 — 기존 비교 기능과 원문 정보 유지
# ===========================================================================

def test_similar_names_not_merged():
    old = """## 명단
1. 김민수 관리자
2. 김민수 대리
"""
    new = """## 명단
1. 김민수 관리자
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["deleted_items"], 1, "유사 이름이지만 다른 항목 → 삭제 1건")
    assert_equal(c["changed_items"], 0, "번호 같고 텍스트 같은 항목은 변경 아님")
    assert "김민수 대리" in out


def test_same_amount_different_items_not_merged():
    old = """## 정산
1. 식대: 50,000원
2. 교통비: 50,000원
"""
    new = """## 정산
1. 식대: 50,000원
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["deleted_items"], 1, "금액 같다고 항목 합치기가 아님")
    assert "교통비: 50,000원" in out


def test_ambiguous_case_preserves_original_info():
    old = """## 정산
1. 오전 수당: 100,000원
2. 현장 수당: 100,000원
"""
    new = """## 정산
2. 오전 수당: 100,000원
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    # 구1 오전수당 -> 신2 오전수당 이동
    # 구2 현장수당 삭제 (신버전에 없음)
    assert_equal(c["order_cnt"], 1, "이동 1건")
    assert_equal(c["deleted_items"], 1, "현장수당 삭제 1건")
    moves = parse_order_moves(out)
    assert moves == [("정산", 1, 2)], f"구1 오전수당 -> 신2 오전수당 이동만 있어야 함, 실제 {moves}"
    assert "오전 수당: 100,000원" in out, "원문 정보 보존"
    assert "현장 수당: 100,000원" in out, "원문 정보 보존"


def test_item_and_body_change_both_reported():
    old = """## 급여
1. 식대: 50,000원

지급일 10일
"""
    new = """## 급여
1. 식대: 60,000원

지급일 20일
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["changed_items"], 1, "식대 금액 변경 1건")
    assert_equal(c["changed_sec"], 1, "지급일 본문 변경 1건")
    assert "식대: 50,000원" in out
    assert "식대: 60,000원" in out
    assert "지급일 10일" in out
    assert "지급일 20일" in out
    assert "실제 변경 건수 (순서 변경 제외): 2건" in out


def test_move_only_items_not_detected_as_body_change():
    old = """## 급여
1. 식대: 50,000원
2. 교통비: 20,000원
"""
    new = """## 급여
1. 교통비: 20,000원
2. 식대: 50,000원
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["changed_items"], 0, "이동만 있고 변경 없음")
    assert_equal(c["deleted_items"], 0, "삭제 없음")
    assert_equal(c["added_items"], 0, "추가 없음")
    assert_equal(c["order_cnt"], 2, "순서 변경 2건")
    assert_equal(c["changed_sec"], 0, "본문 변경 0건")
    assert "실제 변경 건수 (순서 변경 제외): 0건" in out


def test_move_with_new_item_in_place():
    old = """## 급여
1. 식대: 50,000원
"""
    new = """## 급여
1. 교통비: 20,000원
2. 식대: 50,000원
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["added_items"], 1, "교통비 추가 1건")
    assert_equal(c["changed_items"], 0, "변경 없음")
    assert_equal(c["deleted_items"], 0, "식대는 이동이므로 삭제 아님")
    assert_equal(c["order_cnt"], 1, "구1 식대 -> 신2 식대 이동 1건")
    assert "실제 변경 건수 (순서 변경 제외): 1건" in out
    moves = parse_order_moves(out)
    assert moves == [("급여", 1, 2)], f"구1 식대 -> 신2 식대 이동만 있어야 함, 실제 {moves}"
    assert "교통비: 20,000원" in out, "교통비 추가 확인"
    assert "식대: 50,000원" in out, "식대 이동 확인"


def test_item_change_without_ignoring_body():
    old = """## 안내
1. 신청인 확인
지급 마감 10일 이내
"""
    new = """## 안내
1. 신청인 확인 및 서명
지급 마감 10일 이내
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["changed_items"], 1, "항목 변경 1건")
    assert_equal(c["changed_sec"], 0, "본문 변경 없음")
    assert_equal(c["order_cnt"], 0, "이동 없음")
    assert "실제 변경 건수 (순서 변경 제외): 1건" in out


# ===========================================================================
# 7. 같은 신항목을 이동/변경에 중복 대응 ㄴㄴ
#    구1 오전수당10만원/구2 현장수당10만원 -> 신2 오전수당10만원
#    = 오전수당 이동 + 현장수당 삭제
# ===========================================================================

def test_same_new_item_not_matched_to_both_move_and_change():
    old = """## 정산
1. 오전 수당: 100,000원
2. 현장 수당: 100,000원
"""
    new = """## 정산
2. 오전 수당: 100,000원
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    # 오전수당은 이동, 현장수당은 삭제
    assert_equal(c["order_cnt"], 1, "이동 1건")
    assert_equal(c["deleted_items"], 1, "현장수당 삭제 1건")
    assert_equal(c["changed_items"], 0, "변경 0건 (새 항목과 구 항목을 변경으로 중복 매칭하면 안 됨)")
    assert "현장 수당: 100,000원" in out
    assert "오전 수당: 100,000원" in out


def test_move_only_same_item_different_number():
    old = """## 급여
1. 식대: 50,000원
"""
    new = """## 급여
2. 식대: 50,000원
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["changed_items"], 0, "항목 변경 없음")
    assert_equal(c["added_items"], 0, "추가 없음")
    assert_equal(c["deleted_items"], 0, "삭제 없음")
    assert_equal(c["changed_sec"], 0, "본문 변경 없음")
    assert_equal(c["order_cnt"], 1, "순서 변경 1건")
    assert "실제 변경 건수 (순서 변경 제외): 0건" in out
    moves = parse_order_moves(out)
    assert moves == [("급여", 1, 2)], f"구1 식대 -> 신2 식대 이동만 있어야 함, 실제 {moves}"


def test_move_and_add():
    old = """## 급여
1. 식대: 50,000원
"""
    new = """## 급여
1. 교통비: 20,000원
2. 식대: 50,000원
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["changed_items"], 0, "항목 변경 없음")
    assert_equal(c["added_items"], 1, "교통비 추가 1건")
    assert_equal(c["deleted_items"], 0, "삭제 없음")
    assert_equal(c["changed_sec"], 0, "본문 변경 없음")
    assert_equal(c["order_cnt"], 1, "구1 식대 -> 신2 식대 이동 1건")
    assert "실제 변경 건수 (순서 변경 제외): 1건" in out
    moves = parse_order_moves(out)
    assert moves == [("급여", 1, 2)], f"구1 식대 -> 신2 식대 이동만 있어야 함, 실제 {moves}"
    assert "교통비: 20,000원" in out, "교통비 추가 확인"
    assert "식대: 50,000원" in out, "식대 이동 확인"


def test_item_change_and_body_change():
    old = """## 급여
1. 식대: 50,000원

지급일 10일
"""
    new = """## 급여
1. 식대: 60,000원

지급일 20일
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["changed_items"], 1, "식대 금액 변경 1건")
    assert_equal(c["added_items"], 0, "추가 없음")
    assert_equal(c["deleted_items"], 0, "삭제 없음")
    assert_equal(c["changed_sec"], 1, "본문 변경 1건")
    assert_equal(c["order_cnt"], 0, "이동 없음")
    assert "실제 변경 건수 (순서 변경 제외): 2건" in out
    assert "식대: 50,000원" in out
    assert "식대: 60,000원" in out
    assert "지급일 10일" in out
    assert "지급일 20일" in out


def test_pure_move_all_zero():
    old = """## 안내
1. 서울
2. 부산
3. 제주
"""
    new = """## 안내
3. 서울
1. 부산
2. 제주
"""
    a = write_doc(old)
    b = write_doc(new)
    rc, out, err = run(str(a), str(b))
    os.unlink(a)
    os.unlink(b)
    assert_equal(rc, 0, "종료코드")
    c = parse_counts(out)
    assert_equal(c["changed_items"], 0, "항목 변경 0")
    assert_equal(c["added_items"], 0, "추가 0")
    assert_equal(c["deleted_items"], 0, "삭제 0")
    assert_equal(c["changed_sec"], 0, "섹션 변경 0")
    assert_equal(c["order_cnt"], 3, "순서 변경 3건")
    assert "실제 변경 건수 (순서 변경 제외): 0건" in out


# ===========================================================================
# 진입점
# ===========================================================================

def main():
    tests = [
        test_order_change_not_counted_as_change,
        test_same_content_different_numbers_is_order_not_add_delete,
        test_reply_obligation_must_not_be_inferred,
        test_order_change_and_body_change_both_reported,
        test_identical_documents_no_change,
        test_added_item,
        test_deleted_item,
        test_changed_item,
        test_amount_change_is_detected,
        test_similar_names_not_merged,
        test_same_amount_different_items_not_merged,
        test_ambiguous_case_preserves_original_info,
        test_same_new_item_not_matched_to_both_move_and_change,
        test_move_only_same_item_different_number,
        test_move_and_add,
        test_item_change_and_body_change,
        test_pure_move_all_zero,
        test_move_only_items_not_detected_as_body_change,
        test_move_with_new_item_in_place,
        test_item_change_without_ignoring_body,
    ]
    failed = []
    for t in tests:
        try:
            t()
            print(f"ok: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__} — {e}")
            failed.append(t.__name__)
        except Exception as e:
            print(f"ERROR: {t.__name__} — {e}")
            failed.append(t.__name__)

    if failed:
        print(f"\n{n}개 실패: {failed}" if (n := len(failed)) else "실패 없음")
        sys.exit(1)
    print(f"\n모두 통과: {len(tests)}개")
    sys.exit(0)


if __name__ == "__main__":
    main()
