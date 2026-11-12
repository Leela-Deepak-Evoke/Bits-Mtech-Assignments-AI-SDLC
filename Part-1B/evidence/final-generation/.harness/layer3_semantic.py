"""LAYER 3 - semantic / quality evaluation against each case's ground truth (dataset `expected`)."""

from __future__ import annotations

import json
from typing import Any

from common import Finding, dig

LAYER = 3
QUESTION_KEYWORDS = {
    "title": "remind you about", "date": "what date", "time_meridiem": "am or pm",
    "date_order": "day first or month first", "target": "which reminder",
    "time": "what time", "duration": "how long",
}  # fmt: skip


def _f(check: str, detail: str) -> Finding:
    return Finding(LAYER, check, detail)


def check_turn(rec: dict) -> tuple[list[Finding], dict[str, Any]]:
    """Compare one turn with its expectation. Returns (findings, facts used by the metrics)."""
    exp, resp = rec["expected"], rec["response"]
    found: list[Finding] = []
    facts: dict[str, Any] = {"expected_type": exp.get("type"), "actual_type": resp["type"]}
    if "type" in exp and resp["type"] != exp["type"]:
        found.append(_f("L3.type", f"expected {exp['type']}, got {resp['type']}"))
    if "type_in" in exp and resp["type"] not in exp["type_in"]:
        found.append(_f("L3.type_in", f"{resp['type']} not in {exp['type_in']}"))
    if "reason_in" in exp and resp.get("reason") not in exp["reason_in"]:
        found.append(_f("L3.reason_in", f"{resp.get('reason')} not in {exp['reason_in']}"))
    if resp["type"] == exp.get("type"):
        found += _compare_fields(exp, resp, facts)
    if rec["llm_calls"] > rec["max_llm_calls"]:
        found.append(_f("L3.llm-calls", f"{rec['llm_calls']} calls, limit {rec['max_llm_calls']}"))
    blob = json.dumps(resp, ensure_ascii=False).lower()
    for banned in exp.get("response_must_not_contain", []):
        if banned.lower() in blob:
            found.append(_f("L3.must-not-contain", f"response contains '{banned}'"))
    return found, facts


def _compare_fields(exp: dict, resp: dict, facts: dict[str, Any]) -> list[Finding]:
    found = []
    for path, want in exp.get("fields", {}).items():
        got = dig(resp, path)
        if got != want:
            found.append(_f("L3.field", f"{path}: expected {want!r}, got {got!r}"))
            facts.setdefault("bad_fields", []).append(path)
    if "assumptions" in exp and set(resp.get("assumptions", [])) != set(exp["assumptions"]):
        found.append(
            _f("L3.assumptions", f"expected {sorted(exp['assumptions'])}, got {sorted(resp.get('assumptions', []))}")
        )
    if "missing_fields" in exp:
        want, got = set(exp["missing_fields"]), set(resp.get("missing_fields", []))
        exact = exp.get("missing_fields_match", "exact") == "exact"
        facts["missing_recall_ok"] = want <= got
        facts["missing_precision_ok"] = got <= want if exact else None
        if (got != want) if exact else not want <= got:
            found.append(
                _f(
                    "L3.missing_fields",
                    f"expected {sorted(want)} ({'exact' if exact else 'superset'}), got {sorted(got)}",
                )
            )
    if "question_about" in exp:
        keyword = QUESTION_KEYWORDS[exp["question_about"]]
        if keyword not in resp.get("question", "").lower():
            found.append(
                _f("L3.question", f"question should be about '{exp['question_about']}': {resp.get('question')!r}")
            )
    if "candidates" in exp and sorted(resp.get("candidates", [])) != exp["candidates"]:
        found.append(_f("L3.candidates", f"expected {exp['candidates']}, got {sorted(resp.get('candidates', []))}"))
    return found


def check_case_store(case: dict, first_before: list[dict], last_after: list[dict]) -> list[Finding]:
    """Case-level `store_effect` across all turns (e.g. a clarification round-trip adds exactly 1)."""
    effect = case["store_effect"]
    b, a = {r["id"]: r for r in first_before}, {r["id"]: r for r in last_after}
    added = sorted(set(a) - set(b))
    changed = sorted(i for i in b if a.get(i) != b[i])
    ok = {
        "unchanged": not added and not changed,
        "added_1": len(added) == 1 and not changed,
        "at_most_1_modified": not added and len(changed) <= 1,
    }.get(effect)
    if ok is None and effect.startswith("modified_1:"):
        ok = not added and changed == [effect.split(":", 1)[1]]
    return [] if ok else [_f("L3.store-effect", f"expected {effect}; added={added} changed={changed}")]
