#!/usr/bin/env python3
"""verify_wage_cases.py — tests/fixtures/wage-cases.json 검산.

표준라이브러리만 사용.
- 정상 실행: python -B tests/verify_wage_cases.py → exit 0
- --negative-test: F의 기대 rounded_won을 메모리에서만 166으로 바꿔 → exit 1
- --c3-override: C3의 실제 수령액을 메모리에서만 120001로 바꿔 → exit 1
- --empty-list: cases를 빈 목록으로 메모리에서만 바꿔 → exit 1
- --missing-f: F를 메모리에서 제거 → exit 1
- --dup-a: A를 하나 더 넣어 중복 → exit 1
- --short-b-expected: B expected.stages를 4개로 줄여서 → exit 1
- --mutate-b-expected: B expected 합계/변화량/상태를 변조 → exit 1
원본 JSON은 변조하지 않는다.
"""
import copy
import json
import sys
from pathlib import Path


def round_won(n: int) -> int:
    """양수 합산분자만 가정. (n + 30) // 60. Python round()는 사사오입이 아니므로 사용 안 함."""
    if n < 0:
        raise ValueError("negative numerator not supported")
    return (n + 30) // 60


def load_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"]


def fail(case_id: str, msg: str) -> None:
    raise AssertionError(f"FAIL [{case_id}]: {msg}")


# ---------------------------------------------------------------------------
# 공통 구조 검사
# ---------------------------------------------------------------------------

EXPECTED_IDS = ["A", "B", "C1", "C2", "C3", "C4", "D", "E", "F"]

def check_case_ids(cases: list[dict]) -> None:
    """run 전: 각 ID가 정확히 1개씩 있는지 확인. 빈 목록/누락/중복은 실패."""
    if len(cases) == 0:
        fail("STRUCTURE", "cases is empty")
    ids = [c["id"] for c in cases]
    seen = set()
    for cid in ids:
        if cid in seen:
            fail("STRUCTURE", f"duplicate case id: {cid}")
        seen.add(cid)
    for cid in EXPECTED_IDS:
        if cid not in seen:
            fail("STRUCTURE", f"missing case id: {cid}")


# ---------------------------------------------------------------------------
# 사례별 검증
# ---------------------------------------------------------------------------

def verify_A(case: dict) -> None:
    inp, exp = case["input"], case["expected"]
    pm, cm = inp["previous_month"], inp["current_month"]

    def chk(key: str, got: int) -> None:
        if got != exp[key]:
            fail("A", f"{key}: got {got}, expected {exp[key]}")

    chk("monthly_change_total_payment", cm["total_payment"] - pm["total_payment"])
    chk("monthly_change_deduction", cm["deduction"] - pm["deduction"])
    chk(
        "monthly_change_statement_actual_payment",
        cm["statement_actual_payment"] - pm["statement_actual_payment"],
    )
    chk(
        "monthly_change_linked_payment_confirmed",
        cm["linked_payment_confirmed"] - pm["linked_payment_confirmed"],
    )
    prev_diff = pm["statement_actual_payment"] - pm["linked_payment_confirmed"]
    cur_diff = cm["statement_actual_payment"] - cm["linked_payment_confirmed"]
    chk("statement_minus_linked_previous", prev_diff)
    chk("statement_minus_linked_current", cur_diff)
    chk("statement_minus_linked_change", cur_diff - prev_diff)


def b_calc_stage(st: dict, hr: int, other: int, ded: int) -> dict:
    sm = st["statement_base_minutes"]
    cb = st.get("confirmed_base_minutes")
    numerator = sm * hr
    stmt_base = round_won(numerator)
    total = stmt_base + other - ded
    pd = total - st["actual_payment"]
    if cb is None:
        bref = None
    else:
        cb_base = round_won(cb * hr)
        bref = cb_base - stmt_base
    return {
        "name": st["name"],
        "stmt_base": stmt_base,
        "total": total,
        "actual_payment": st["actual_payment"],
        "pd": pd,
        "bref": bref,
        "cb": cb,
        "corrected": st.get("statement_is_corrected", False),
    }


def b_expected_from_input(inp: dict) -> dict:
    """B의 expected 합계/변화량/상태 수치를 input에서 계산한 값."""
    hr = inp["hourly_rate_per_hour"]
    other = inp["other"]
    ded = inp["deduction"]
    stages = inp["stages"]

    calc = [b_calc_stage(st, hr, other, ded) for st in stages]

    s1 = calc[0]
    s5 = calc[4]

    return {
        "corrected_statement_minus_actual": s5["total"] - s5["actual_payment"],
        "base_pay_change": s5["stmt_base"] - s1["stmt_base"],
        "statement_total_change": s5["total"] - s1["total"],
        "actual_payment_change": s5["actual_payment"] - s1["actual_payment"],
        "stages": [
            {
                "statement_total": calc[i]["total"],
                "payment_diff_available": calc[i]["pd"] is not None,
                "base_pay_ref_available": calc[i]["bref"] is not None,
            }
            for i in range(5)
        ],
    }


def verify_B(case: dict) -> None:
    """B: 시급은 시간당 원. 모든 산술은 (minutes * hourly_rate_per_hour + 30) // 60."""
    inp, exp = case["input"], case["expected"]
    hr = inp["hourly_rate_per_hour"]  # won per hour
    other = inp["other"]
    ded = inp["deduction"]
    stages = inp["stages"]
    exp_stages = exp["stages"]

    # 입력/기대 단계 개수
    if len(stages) != 5:
        fail("B", f"input stages count should be 5, got {len(stages)}")
    if len(exp_stages) != 5:
        fail("B", f"expected stages count should be 5, got {len(exp_stages)}")

    calc = [b_calc_stage(st, hr, other, ded) for st in stages]

    # expected의 명세서 합계/최종 차이/변화량/상태를 입력에서 계산해서 대조
    expected_calc = b_expected_from_input(inp)

    if exp["corrected_statement_minus_actual"] != expected_calc["corrected_statement_minus_actual"]:
        fail("B", f"corrected_statement_minus_actual: got {exp['corrected_statement_minus_actual']}, expected {expected_calc['corrected_statement_minus_actual']}")
    if exp["base_pay_change"] != expected_calc["base_pay_change"]:
        fail("B", f"base_pay_change: got {exp['base_pay_change']}, expected {expected_calc['base_pay_change']}")
    if exp["statement_total_change"] != expected_calc["statement_total_change"]:
        fail("B", f"statement_total_change: got {exp['statement_total_change']}, expected {expected_calc['statement_total_change']}")
    if exp["actual_payment_change"] != expected_calc["actual_payment_change"]:
        fail("B", f"actual_payment_change: got {exp['actual_payment_change']}, expected {expected_calc['actual_payment_change']}")

    for i, (es, ec) in enumerate(zip(exp_stages, expected_calc["stages"])):
        if es["statement_total"] != ec["statement_total"]:
            fail(es["name"], f"statement_total: got {es['statement_total']}, expected {ec['statement_total']}")
        if es.get("payment_diff_available") != ec["payment_diff_available"]:
            fail(es["name"], f"payment_diff_available: got {es.get('payment_diff_available')}, expected {ec['payment_diff_available']}")
        if es.get("base_pay_ref_available") != ec["base_pay_ref_available"]:
            fail(es["name"], f"base_pay_ref_available: got {es.get('base_pay_ref_available')}, expected {ec['base_pay_ref_available']}")

    # 단계별 기대 대조
    for cs, es in zip(calc, exp_stages):
        if cs["stmt_base"] != es["statement_base_pay"]:
            fail(cs["name"], f"stmt_base: got {cs['stmt_base']}, expected {es['statement_base_pay']}")
        if cs["pd"] != es["payment_difference"]:
            fail(cs["name"], f"payment_difference: got {cs['pd']}, expected {es['payment_difference']}")
        if cs["bref"] != es["base_pay_reference_diff"]:
            fail(cs["name"], f"base_pay_reference_diff: got {cs['bref']}, expected {es['base_pay_reference_diff']}")

        # 산술별 계산가능/보류 상태 검증
        stage_name = cs["name"]
        pd_ok = (cs["pd"] is not None)
        bref_ok = (cs["bref"] is not None)
        if es.get("payment_diff_available") is not pd_ok:
            fail(stage_name, f"payment_diff_available: got {pd_ok}, expected {es.get('payment_diff_available')}")
        if es.get("base_pay_ref_available") is not bref_ok:
            fail(stage_name, f"base_pay_ref_available: got {bref_ok}, expected {es.get('base_pay_ref_available')}")

    # B의 핵심 점검: 수정본 적용 여부와 산술별 확인/보류를 실제 입력으로 검사
    if calc[0]["pd"] != 20000 or calc[0]["bref"] is not None:
        fail("B", f"stage1 should be (20000, null), got ({calc[0]['pd']}, {calc[0]['bref']})")
    if calc[1]["pd"] != 0 or calc[1]["bref"] is not None:
        fail("B", f"stage2 should be (0, null), got ({calc[1]['pd']}, {calc[1]['bref']})")
    if calc[2]["pd"] != 0 or calc[2]["bref"] != 96000:
        fail("B", f"stage3 should be (0, 96000), got ({calc[2]['pd']}, {calc[2]['bref']})")
    if calc[3]["pd"] != 0 or calc[3]["bref"] != 72000:
        fail("B", f"stage4 should be (0, 72000), got ({calc[3]['pd']}, {calc[3]['bref']})")
    if calc[4]["pd"] != 72000 or calc[4]["bref"] != 0:
        fail("B", f"stage5 should be (72000, 0), got ({calc[4]['pd']}, {calc[4]['bref']})")

    # 확인된 기본시간이 stage별로 맞게 들어 있는지 (입력에서 계산)
    if calc[0]["cb"] is not None:
        fail("B", "stage1 confirmed_base_minutes should be null")
    if calc[1]["cb"] is not None:
        fail("B", "stage2 confirmed_base_minutes should be null")
    if calc[2]["cb"] != 9600:
        fail("B", f"stage3 confirmed_base_minutes should be 9600, got {calc[2]['cb']}")
    if calc[3]["cb"] != 9480:
        fail("B", f"stage4 confirmed_base_minutes should be 9480, got {calc[3]['cb']}")
    if calc[4]["cb"] != 9480:
        fail("B", f"stage5 confirmed_base_minutes should be 9480, got {calc[4]['cb']}")

    # 수정 명세서 적용은 stage5에서만 true (입력의 statement_is_corrected 기준)
    if not calc[4]["corrected"]:
        fail("B", "stage5 statement_is_corrected should be True")
    for i in range(4):
        if calc[i]["corrected"]:
            fail("B", f"stage{i+1} statement_is_corrected should be False")

    # 정정은 5단계에서만 적용된다는 기대를 입력 기반으로 확인
    if not exp.get("correction_applied_only_at_stage5"):
        fail("B", "correction_applied_only_at_stage5 should be True")


def verify_C(case: dict) -> None:
    """C계열: 답을 직접 적어두지 않고 input에서 계산한 숫자/보류 상태를 expected와 대조."""
    cid = case["id"]
    inp, exp = case["input"], case["expected"]
    statement = inp["statement_actual_payment"]
    receipt = inp["actual_receipt_confirmed"]  # null 또는 정수
    item_complete = inp.get("item_list_complete", True)

    if receipt is None:
        pd = None
    else:
        pd = statement - receipt

    suspended = (item_complete is False)

    if exp["statement_actual_payment"] != statement:
        fail(cid, f"statement_actual_payment: got {statement}, expected {exp['statement_actual_payment']}")
    if exp["actual_receipt"] != receipt:
        fail(cid, f"actual_receipt: got {receipt}, expected {exp['actual_receipt']}")
    if exp["payment_difference"] != pd:
        fail(cid, f"payment_difference: got {pd}, expected {exp['payment_difference']}")
    if exp["statement_preserved"] is not True:
        fail(cid, "statement_preserved should be True")

    if cid == "C2":
        if exp["internal_total_verification_suspended"] is not suspended:
            fail(cid, f"internal_total_verification_suspended: got {suspended}, expected {exp['internal_total_verification_suspended']}")
        if exp["total_payment_assessable"] is not False:
            fail(cid, "total_payment_assessable should be False")
    elif cid == "C3":
        if exp["zeroed_or_return_obligation_judgment"] is not False:
            fail(cid, "zeroed_or_return_obligation_judgment should be False")
    elif cid == "C4":
        if receipt != 0:
            fail(cid, f"actual_receipt_confirmed should be 0 (confirmed zero), got {receipt}")
        if pd != statement:
            fail(cid, f"payment_difference should be {statement} (statement - 0), got {pd}")
        if exp["total_payment_assessable"] is not False:
            fail(cid, "total_payment_assessable should be False")


def verify_minute_rounding(case: dict) -> None:
    cid = case["id"]
    inp, exp = case["input"], case["expected"]
    records = inp["records"]
    numerator = sum(r["minutes"] * r["hourly_rate"] for r in records)
    divided = numerator / 60
    rounded = round_won(numerator)

    if exp["sum_min_times_rate"] != numerator:
        fail(cid, f"sum_min_times_rate: got {numerator}, expected {exp['sum_min_times_rate']}")
    if exp["divided_by_60"] != divided:
        fail(cid, f"divided_by_60: got {divided}, expected {exp['divided_by_60']}")
    if exp["rounded_won"] != rounded:
        fail(cid, f"rounded_won: got {rounded}, expected {exp['rounded_won']}")


VERIFIERS = {
    "A": verify_A,
    "B": verify_B,
    "C1": verify_C,
    "C2": verify_C,
    "C3": verify_C,
    "C4": verify_C,
    "D": verify_minute_rounding,
    "E": verify_minute_rounding,
    "F": verify_minute_rounding,
}


def run(cases: list[dict]) -> bool:
    """모든 사례를 검증한다. 실패가 있으면 True(실패 있음)를 반환."""
    any_fail = False
    for case in cases:
        cid = case["id"]
        fn = VERIFIERS.get(cid)
        if fn is None:
            fail(cid, f"unknown case id (no verifier)")
        try:
            fn(case)
            print(f"OK: {cid}")
        except AssertionError as e:
            print(str(e))
            any_fail = True
    return any_fail


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    path = fixture_dir / "wage-cases.json"
    if not path.is_file():
        print(f"ERROR: {path} not found")
        sys.exit(2)

    cases = load_cases(path)
    cases_hash = hash_cases(path)
    script_hash = hash_file(Path(__file__))

    mode = "normal"
    if "--negative-test" in sys.argv:
        mode = "negative-test"
        cases = copy.deepcopy(cases)
        for c in cases:
            if c["id"] == "F":
                c["expected"]["rounded_won"] = 166
                break
    elif "--c3-override" in sys.argv:
        mode = "c3-override"
        cases = copy.deepcopy(cases)
        for c in cases:
            if c["id"] == "C3":
                c["input"]["actual_receipt_confirmed"] = 120001
                break
    elif "--empty-list" in sys.argv:
        mode = "empty-list"
        cases = []
    elif "--missing-f" in sys.argv:
        mode = "missing-f"
        cases = [c for c in copy.deepcopy(cases) if c["id"] != "F"]
    elif "--dup-a" in sys.argv:
        mode = "dup-a"
        cases = copy.deepcopy(cases) + [copy.deepcopy(cases[0])]
    elif "--short-b-expected" in sys.argv:
        mode = "short-b-expected"
        cases = copy.deepcopy(cases)
        for c in cases:
            if c["id"] == "B":
                c["expected"]["stages"] = c["expected"]["stages"][:4]
                break
    elif "--mutate-b-expected" in sys.argv:
        mode = "mutate-b-expected"
        cases = copy.deepcopy(cases)
        for c in cases:
            if c["id"] == "B":
                c["expected"]["statement_total_change"] = 99999
                c["expected"]["base_pay_change"] = 88888
                c["expected"]["corrected_statement_minus_actual"] = 11111
                c["expected"]["actual_payment_change"] = 22222
                for s in c["expected"]["stages"]:
                    s["payment_diff_available"] = False
                break

    print(f"mode={mode}  cases={len(cases)}  fixture={path}")
    print(f"fixture_sha256={cases_hash}  script_sha256={script_hash}")

    try:
        check_case_ids(cases)
    except AssertionError as e:
        print(str(e))
        sys.exit(1)

    any_fail = run(cases)
    if any_fail:
        sys.exit(1)
    sys.exit(0)


def hash_cases(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    main()
