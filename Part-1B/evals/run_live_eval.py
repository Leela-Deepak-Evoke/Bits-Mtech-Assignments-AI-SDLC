"""NON-DETERMINISTIC evaluation pipeline: dataset -> real Claude extractor -> agent -> 3-layer harness.

    export GROQ_API_KEY=...               # or ANTHROPIC_API_KEY with --provider anthropic; never commit it
    python evals/run_live_eval.py [--runs 3] [--split all|dev|test] [--limit N] [--label TEXT]
    python evals/run_live_eval.py --stub-client      # offline smoke test of this pipeline, NOT live evidence

Unlike ``run_eval.py`` (replay of gold extractions), here the language model does the extraction, so results can
differ run to run. Each case is repeated ``--runs`` times and we report:
  * EVAL-2  first-pass extraction validity   * EVAL-3  intent accuracy   * EVAL-4  title-span accuracy
  * EVAL-13 run-to-run stability (same final response type across runs)
  * Layer 1/2 findings (schema + safety invariants) - these must be zero even with a non-deterministic model.
Cases with injected faults (LLM timeout etc.) are skipped: they are deterministic drills covered by run_eval.py.
Output: evidence/live-eval-results.json (stub runs write evidence/live-eval-results.stub.json) and a log entry.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".harness"))
sys.path.insert(0, str(ROOT / "src"))

import executor  # noqa: E402
import layer1_structural as l1  # noqa: E402
import layer2_invariants as l2  # noqa: E402
import layer3_semantic as l3  # noqa: E402
import log  # noqa: E402

from reminder_agent.llm.anthropic_client import AnthropicExtractor  # noqa: E402
from reminder_agent.llm.groq_client import GroqExtractor  # noqa: E402

DATASET = ROOT / "evals" / "dataset.json"
EVIDENCE = ROOT / "evidence"


def load_dotenv() -> None:
    """Load KEY=VALUE lines from a git-ignored .env (repo root or Part-1B) without overriding the real environment."""
    for folder in (ROOT, ROOT.parent):
        path = folder / ".env"
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


class StubClient:
    """Offline stand-in for the Anthropic SDK: answers with the dataset's gold extraction. Smoke test only."""

    def __init__(self, recorded: dict[str, dict]) -> None:
        self.messages = self
        self._recorded = recorded

    def create(self, **request: object) -> SimpleNamespace:
        body = request["messages"][0]["content"]  # type: ignore[index]
        message = body.split("<message>", 1)[1].split("</message>", 1)[0]
        payload = self._recorded.get(message, {})
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload))])


def first_extraction(record: dict) -> dict | None:
    """Parse the model's first raw output for this turn, or None if it was not valid JSON."""
    if not record["extractions"]:
        return None
    raw = record["extractions"][0]
    try:
        return raw if isinstance(raw, dict) else json.loads(raw)
    except json.JSONDecodeError:
        return None


def score_turn(record: dict, gold: dict | None) -> dict:
    parsed = first_extraction(record)
    valid = parsed is not None and not l1.check_extraction(parsed)
    row = {"extraction_valid": valid, "intent_ok": None, "title_ok": None}
    if gold and parsed:
        row["intent_ok"] = parsed.get("intent") == gold.get("intent")
        if gold.get("title"):
            got = (parsed.get("title") or {}).get("text", "")
            row["title_ok"] = got.strip().lower() == gold["title"]["text"].strip().lower()
    return row


def rate(values: list[bool | None]) -> dict:
    known = [v for v in values if v is not None]
    return {"n": len(known), "rate": round(sum(known) / len(known), 4) if known else None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3, help="repetitions per case (EVAL-13 needs >= 3)")
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all")
    parser.add_argument("--limit", type=int, default=0, help="only the first N cases (cheap trial)")
    parser.add_argument("--label", default="live")
    parser.add_argument("--provider", choices=["groq", "anthropic"], default="groq")
    parser.add_argument("--pause", type=float, default=0.0, help="seconds to wait between cases (rate limits)")
    parser.add_argument("--stub-client", action="store_true", help="offline smoke test; not live evidence")
    args = parser.parse_args()

    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = [c for c in dataset["cases"] if args.split == "all" or c["split"] == args.split]
    cases = [c for c in cases if not (c.get("fault") or {}).get("target")]
    if args.limit:
        cases = cases[: args.limit]

    if args.stub_client:
        recorded = {t["message"]: t["gold_extraction"] for c in dataset["cases"] for t in c["turns"] if t["gold_extraction"]}
        client = StubClient(recorded)
    else:
        load_dotenv()
        key_name = "GROQ_API_KEY" if args.provider == "groq" else "ANTHROPIC_API_KEY"
        if not os.environ.get(key_name):
            sys.exit(f"ABORT: {key_name} is not set. Export it or put it in a git-ignored .env (or use --stub-client).")
        client = None  # the adapter builds its own connection lazily

    def make_extractor() -> object:
        if args.provider == "groq" and not args.stub_client:
            return GroqExtractor()
        return AnthropicExtractor(client=client)

    valid, intent_ok, title_ok, layer_findings, per_case = [], [], [], [], []
    for case in cases:
        finals, case_findings = [], []
        for run in range(args.runs):
            records = executor.run_case(case, dataset, live_extractor=make_extractor())
            finals.append(records[-1]["response"]["type"])
            for rec, turn in zip(records, case["turns"], strict=True):
                score = score_turn(rec, turn["gold_extraction"])
                valid.append(score["extraction_valid"])
                intent_ok.append(score["intent_ok"])
                title_ok.append(score["title_ok"])
                f1 = l1.check_response(rec["response"])
                f2 = l2.check_turn(rec) if not f1 else []
                f3, _ = l3.check_turn(rec)
                case_findings += [{"run": run, "turn": rec["turn"], **f.as_dict()} for f in f1 + f2]
                case_findings += [{"run": run, "turn": rec["turn"], "soft": True, **f.as_dict()} for f in f3]
        layer_findings += [f for f in case_findings if not f.get("soft")]
        if args.pause:
            time.sleep(args.pause)
        per_case.append(
            {
                "id": case["id"],
                "final_types": finals,
                "stable": len(set(finals)) == 1,
                "expected_type": case["turns"][-1]["expected"].get("type"),
                "findings": case_findings,
            }
        )

    stability = rate([c["stable"] for c in per_case])
    result = {
        "meta": {
            "mode": "stub-client (offline smoke test, NOT live evidence)" if args.stub_client else "live",
            "model": make_extractor()._model,  # noqa: SLF001
            "provider": "stub" if args.stub_client else args.provider,
            "runs_per_case": args.runs,
            "split": args.split,
            "timestamp": log.stamp(),
            "cases": len(cases),
        },
        "metrics": {
            "EVAL-2 first-pass extraction validity": rate(valid),
            "EVAL-3 intent accuracy": rate(intent_ok),
            "EVAL-4 title-span accuracy": rate(title_ok),
            "EVAL-13 run-to-run stability": stability,
        },
        "layer1_2_safety_findings": len(layer_findings),
        "cases": per_case,
    }
    EVIDENCE.mkdir(exist_ok=True)
    out = EVIDENCE / ("live-eval-results.stub.json" if args.stub_client else "live-eval-results.json")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [f"## {log.stamp()} - LIVE EVAL [{args.label}] (mode={result['meta']['mode']}, model={result['meta']['model']})", ""]
    lines += [f"- {name}: {m['rate']} (n={m['n']})" for name, m in result["metrics"].items()]
    lines += [f"- Layer 1/2 (schema + safety) findings: {len(layer_findings)}", f"- Details: `{out.name}`"]
    log.append("\n".join(lines))
    print(json.dumps(result["metrics"], indent=2), f"\nlayer1/2 findings: {len(layer_findings)}  ->  {out}")  # noqa: T201
    return 0 if not layer_findings else 1


if __name__ == "__main__":
    sys.exit(main())
