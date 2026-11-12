"""Evaluation runner: dataset -> agent -> 3-layer harness -> evidence/eval-results.json + evidence/harness-log.md.

    python evals/run_eval.py [--mode replay] [--split all|dev|test] [--label TEXT] [--skip-static]

Exit code 0 = every case passed and every measured HARD metric passed; 1 otherwise.
Replay mode feeds each case's recorded gold extraction to the real agent, so it tests the deterministic
pipeline (resolver, policy, store, guardrails), NOT the language model. Live mode is not implemented here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".harness"))

import executor  # noqa: E402
import layer1_structural as l1  # noqa: E402
import layer2_invariants as l2  # noqa: E402
import layer3_semantic as l3  # noqa: E402
import log  # noqa: E402
import metrics  # noqa: E402
import static_gate  # noqa: E402
from common import SUCCESS_TYPES  # noqa: E402

DATASET = ROOT / "evals" / "dataset.json"
DATASET_HASH = ROOT / "evals" / "dataset.sha256"
THRESHOLDS = ROOT / ".harness" / "thresholds.json"
RESULTS = ROOT / "evidence" / "eval-results.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_dataset() -> str:
    """Anti-gaming gate: the dataset must match its recorded hash (constitution Art. VII)."""
    actual, recorded = sha256(DATASET), DATASET_HASH.read_text().split()[0]
    if actual != recorded:
        sys.exit(f"ABORT: evals/dataset.json hash {actual[:12]} != recorded {recorded[:12]}. The dataset was modified.")
    return actual


def run_static(label: str) -> dict:
    report = static_gate.run()
    for cycle in report["cycles"]:
        log.append(
            f"## {log.stamp()} - SELF-HEALING cycle {cycle['attempt']} (static gates, automatic) [{label}]\n\n"
            f"- **Failing gates:** {', '.join(cycle['gates'])}\n"
            f"- **Action:** `ruff check --fix` + `ruff format` (deterministic, safe fixes only)\n"
            f"- **Gates still failing afterwards:** {', '.join(cycle['after_failing']) or 'none'}\n"
            f"- **Failure output before repair (truncated):**\n\n```\n{next(iter(cycle['before'].values()))[:900]}\n```"
        )
    return report


def evaluate_case(case: dict, dataset: dict) -> tuple[dict, list[dict]]:
    records = executor.run_case(case, dataset)
    case_findings = []
    for turn in case["turns"]:
        if turn["gold_extraction"]:
            case_findings += l1.check_extraction(turn["gold_extraction"])
    turn_rows = []
    for rec in records:
        f1 = l1.check_response(rec["response"])
        f2 = l2.check_turn(rec) if not f1 else []
        f3, facts = l3.check_turn(rec)
        turn_rows.append(
            {
                **rec,
                "facts": facts,
                "expected_type": facts["expected_type"],
                "layer1_ok": not f1,
                "layer1": [f.as_dict() for f in f1],
                "layer2": [f.as_dict() for f in f2],
                "layer3": [f.as_dict() for f in f3],
            }
        )
    case_store = l3.check_case_store(case, records[0]["store_before"], records[-1]["store_after"])
    gold = [f.as_dict() for f in case_findings + case_store]
    findings = [f for row in turn_rows for key in ("layer1", "layer2", "layer3") for f in row[key]] + gold
    summary = {
        "id": case["id"],
        "category": case["category"],
        "split": case["split"],
        "difficulty": case["difficulty"],
        "passed": not findings,
        "findings": findings,
        "layers": {n: not any(f["layer"] == n for f in findings) for n in (1, 2, 3)},
    }
    return summary, turn_rows


def render(case: dict, summary: dict, rows: list[dict]) -> dict:
    return {
        **summary,
        "description": case["description"],
        "turns": [
            {
                "message": r["message"][:300],
                "expected": r["expected"],
                "response": r["response"],
                "llm_calls": r["llm_calls"],
                "latency_ms": r["latency_ms"],
                "findings": r["layer1"] + r["layer2"] + r["layer3"],
            }
            for r in rows
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["replay"], default="replay")
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all")
    parser.add_argument("--label", default="run")
    parser.add_argument("--skip-static", action="store_true")
    args = parser.parse_args()

    dataset_sha = verify_dataset()
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    static = None if args.skip_static else run_static(args.label)

    global_findings = [f.as_dict() for f in l1.contract_sync() + l2.inv13_clock_sourcing()]
    cases = [c for c in dataset["cases"] if args.split == "all" or c["split"] == args.split]
    summaries, rendered, all_turns = [], [], []
    for case in cases:
        summary, rows = evaluate_case(case, dataset)
        summaries.append(summary)
        rendered.append(render(case, summary, rows))
        all_turns += rows

    values = metrics.compute(all_turns, summaries)
    table = metrics.judge(values, thresholds["metrics"])
    failed_cases = [s for s in summaries if not s["passed"]]
    hard_fail = [m for m in table if m["class"] == "hard" and m["status"] == "FAIL"]
    soft_fail = [m for m in table if m["class"] == "soft" and m["status"] == "FAIL"]
    static_ok = static is None or static["ok"]
    clean = not (failed_cases or hard_fail or global_findings) and static_ok
    recommendation = "ACCEPT_RECOMMENDED (replay scope only)" if clean else "REJECT_RECOMMENDED"
    layer_stats = {
        str(n): {"cases_passing": sum(s["layers"][n] for s in summaries), "cases": len(summaries)} for n in (1, 2, 3)
    }

    result = {
        "meta": {
            "mode": args.mode,
            "split": args.split,
            "label": args.label,
            "python": platform.python_version(),
            "timestamp": log.stamp(),
            "dataset_sha256": dataset_sha,
            "thresholds_sha256": sha256(THRESHOLDS),
            "extractor": "replay of dataset gold_extraction (no language model was called)",
        },
        "summary": {
            "cases": len(summaries),
            "cases_passed": len(summaries) - len(failed_cases),
            "turns": len(all_turns),
            "success_responses": sum(t["response"]["type"] in SUCCESS_TYPES for t in all_turns),
            "layers": layer_stats,
            "global_findings": global_findings,
            "static_gates": None
            if static is None
            else {
                "ok": static["ok"],
                "repair_cycles": len(static["cycles"]),
                "final": {g: v["ok"] for g, v in static["final"].items()},
            },
            "recommendation": recommendation,
            "human_decision": (
                "PENDING - record with `python .harness/log.py decision --decision ACCEPT|REJECT --by <name>`"
            ),
        },
        "metrics": table,
        "not_measured_in_replay": thresholds["not_measured_in_replay"],
        "cases": rendered,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    log.append(format_log(args, result, failed_cases, hard_fail, soft_fail, static))
    print_summary(result, failed_cases, hard_fail, soft_fail)
    return 0 if clean else 1


def format_log(
    args: argparse.Namespace, result: dict, failed: list[dict], hard: list[dict], soft: list[dict], static: dict | None
) -> str:
    s = result["summary"]
    lines = [
        f"## {result['meta']['timestamp']} - HARNESS RUN [{args.label}] (mode={args.mode}, split={args.split})",
        "",
        f"- Dataset sha256 `{result['meta']['dataset_sha256'][:16]}...` verified; "
        f"thresholds sha256 `{result['meta']['thresholds_sha256'][:16]}...`",
        f"- **Cases:** {s['cases_passed']}/{s['cases']} passed ({s['turns']} turns)",
        *[f"- **Layer {n}:** {v['cases_passing']}/{v['cases']} cases clean" for n, v in s["layers"].items()],
    ]
    if static is not None:
        lines.append(
            f"- **Static gates:** {'PASS' if static['ok'] else 'FAIL'} "
            + str({g: v["ok"] for g, v in static["final"].items()})
        )
    for finding in s["global_findings"]:
        lines.append(f"- GLOBAL FINDING: {finding['check']}: {finding['detail']}")
    if failed:
        lines += ["", "**Failing cases:**", ""]
        for c in failed:
            lines.append(
                f"- `{c['id']}` ({c['category']}): "
                + "; ".join(f"[L{f['layer']}] {f['check']}: {f['detail']}" for f in c["findings"][:3])
            )
    lines += ["", "| Metric | Measured | Threshold | Class | Status |", "|---|---|---|---|---|"]
    for m in result["metrics"]:
        value = "n/a" if m["measured"] is None else f"{m['measured']:.4g} (n={m['n']})"
        lines.append(f"| {m['id']} {m['name']} | {value} | {m['op']} {m['value']} | {m['class']} | {m['status']} |")
    lines += [
        "",
        f"- Hard metrics failing: {', '.join(m['id'] for m in hard) or 'none'}; "
        f"soft failing: {', '.join(m['id'] for m in soft) or 'none'}",
        f"- Metrics not measurable in replay mode: {', '.join(result['not_measured_in_replay'])}",
        f"- **Harness recommendation:** {s['recommendation']}",
        "- **Human decision:** PENDING",
    ]
    return "\n".join(lines)


def print_summary(result: dict, failed: list[dict], hard: list[dict], soft: list[dict]) -> None:
    s = result["summary"]
    print(f"cases {s['cases_passed']}/{s['cases']} | layers {s['layers']} | {s['recommendation']}")
    for c in failed:
        print(f"  FAIL {c['id']}: " + " | ".join(f"{f['check']}: {f['detail']}" for f in c["findings"][:2]))
    for m in hard + soft:
        print(f"  METRIC {m['id']} {m['status']} {m['measured']} ({m['class']})")
    for finding in s["global_findings"]:
        print("  GLOBAL", finding)


if __name__ == "__main__":
    sys.exit(main())
