# Constitution — Part-1B: Natural-Language Reminder Agent

**Version:** 1.0.0 · **Ratified:** 2026-11-12 · **Status:** Active (confirmed by reviewer 2026-11-13)

Part-1B inherits **Articles II–X of the Part-1A constitution** (`../../Part-1A/.speckit/constitution.md`) unchanged,
except where this document says otherwise. Where a plan conflicts with this document, the plan changes.
Key words MUST / MUST NOT / SHOULD follow RFC 2119.

## Article I — Technology Stack (replaces Part-1A Article I)

| Concern | Choice |
|---|---|
| Language | Python 3.11+ |
| Contract validation | `jsonschema` against the JSON Schema files in `.speckit/contracts/` (they are authoritative) |
| Time zones | stdlib `zoneinfo` + `tzdata` |
| LLM | Anthropic SDK behind an `Extractor` port; `temperature=0`; JSON-only output; **no tools** |
| Store | In-memory + atomic JSON file behind a store interface |
| Tests / quality | pytest, ruff, mypy, bandit, pip-audit, detect-secrets |

## Additional rules specific to an LLM component

1. **The LLM only extracts.** It returns intent and verbatim text spans. It MUST NOT compute dates, durations or ids;
   deterministic code does that.
2. **No guessing.** Missing or ambiguous information MUST produce a clarification question (max 3 rounds), never a silent default
   that is not disclosed as an assumption.
3. **Model output is untrusted data.** It is validated against the extraction schema; user text is never treated as instructions.
4. **Anti-gaming.** The harness MUST NOT edit `evals/dataset.json` (hash-gated) or loosen `.harness/thresholds.json` to turn a run green.
5. **Two evaluation pipelines are kept apart.**
   - Deterministic: `evals/run_eval.py` replays recorded gold extractions through the real agent (CI-safe, no network).
   - Non-deterministic: `evals/run_live_eval.py` calls the real model, repeats each case, and reports accuracy and stability.
     It is opt-in and never part of the default verify step.
6. **Secrets.** API keys come only from the environment (`ANTHROPIC_API_KEY`) and MUST NOT be committed.
7. **Human decision.** A harness recommendation is not an acceptance. A named human records ACCEPT or REJECT
   (`python .harness/log.py decision ...`) and the known limitations (see `../ACCEPTANCE.md`).

## Governance

Amendments follow Part-1A Article X (written rationale, semver bump, updated date).

**Last amended:** 2026-11-12
