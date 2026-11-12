# Implementation Plan — Natural-Language Reminder Agent

**Version:** 1.0.0 · **Date:** 2026-11-12 · **Status:** Approved (reviewed 2026-11-13)
**Implements:** `.speckit/spec.md` v1.0.0 · **Contracts:** `.speckit/contracts/*.schema.json`

---

## 1. Summary

A pipeline in which an LLM only **extracts** (intent + verbatim spans) and deterministic code does everything that must be correct: date/time arithmetic, clarification policy, reminder mutation, invariants, and sanitisation. This split lets 100% of the date logic, policy, and safety rules be tested without a model (replay mode), while the model-dependent quality is measured separately by the eval harness (live mode).

```
message ─► Guard ─► ExtractionPort(LLM) ─► ExtractionValidator ─► Resolver ─► Policy ─► Store ─► ResponseBuilder ─► InvariantChecker ─► AgentResponse
            │            │ (≤1 repair retry)        (schema+INV-3)   (pure)      (pure)   (only writer)                    (INV-1,2,5,7…)
            └─ input_invalid (no LLM call)                                                     └─ rollback on failure
```

## 2. Technical Context

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.13 (Part-1A ran 3.13; code kept 3.11+ compatible) | Consistency with Part-1A. |
| Models / validation | Pydantic v2 for internal types; `jsonschema` (Draft 2020-12) for the **authoritative contract check** | The JSON Schema files are the contract (INV-1), so they are enforced directly, not re-derived. |
| Time | stdlib `zoneinfo` + **`tzdata`** (required dependency) | Verified: Windows Python here has no system tz database, so `ZoneInfo("America/New_York")` fails without `tzdata`. |
| Date parsing | **Own rule engine** (spec assumption 7), no `dateparser` | `dateparser` guesses silently, and spec forbids silent guessing (SAF-4); every rule DT-n must map to one auditable function. |
| LLM | `anthropic` SDK behind `ExtractionPort`; model id from env `REMINDER_LLM_MODEL` (default `claude-haiku-5-5`, pinned in eval reports); `temperature=0`; JSON-only output, **no tools** (SAF-1) | Extraction is a small task: cheap/fast model; pinned for reproducibility. |
| CLI | Typer | Same as Part-1A; entry point is `handle()` (FR-8). |
| Store | In-memory + atomic JSON file behind a `ReminderStore` Protocol | FR-7. |
| Tests | pytest, pytest-cov, **hypothesis** (properties), `jsonschema` | Spec §7. |
| Quality | ruff, mypy `--strict`, bandit, pip-audit, detect-secrets | Inherited (see §3). |
| Task runner | `Makefile` with `verify`, `eval-replay`, `eval-live` | Gate per command. |

## 3. Constitution Check

Part-1B has **no constitution file** (open question 5 in the spec was not answered). This plan assumes **inheriting Part-1A's Articles II–X unchanged**, with Article I (stack) replaced by §2 above. T001 writes `.speckit/constitution.md` recording this, so it can be amended later via Article X. If you want different rules, the plan changes, not the code.

| Article | Requirement | How the plan complies |
|---|---|---|
| II Modularity | Layered, DI, no business logic in interfaces, smart features isolated | §4 layout; LLM adapter and Resolver are separate packages behind ports; CLI calls only `handle()`. Architecture test T014. |
| III Clean code | ≤25-line functions, complexity ≤10, strict typing, no magic values | Resolver split into one function per DT-n; enums for intents/assumptions/reasons. ruff `C901`, mypy strict. |
| IV Test-first | Failing tests before code; coverage ≥90% (domain+services ≥95%) | Every implementation task is preceded by its test task (§8). |
| V Lint guard | ruff/mypy zero warnings; pre-commit | T002, T003. |
| VI Security | Hostile input, no leaks, secrets in env, dependency audit | SAF-1…SAF-13 mapped in §7; `tests/security/`. Part-1A's API-hardening clause is N/A (no HTTP API). |
| VII Self-healing harness | `make verify`, bounded 3 repairs, anti-cheating | T004 reuses the Part-1A harness design; **plus** an LLM-specific rule: the harness may never edit `evals/dataset.json` or loosen a threshold to get green (dataset hash gate). |
| VIII/IX Workflow / DoD | Spec-first, traceability, docs | `tasks.md` traces every task to FR/AC; DoD checklist in §10. |

**Deviation table**

| Deviation | Justification |
|---|---|
| Constitution not yet authored | Created in T001 as inherited text; flagged for user confirmation. |
| Art. IV "no network in tests" vs. live eval | Live eval is a separate opt-in command (`make eval-live`), never part of `make verify`. |

## 4. Project Layout

```
Part-1B/
├─ .speckit/            constitution.md  spec.md  plan.md  tasks.md  contracts/  harness-log.md
├─ pyproject.toml  Makefile  .env.example  README.md
├─ src/reminder_agent/
│  ├─ domain/                       (pure, no I/O)
│  │   models.py                    Reminder, ResolvedTime, Ctx, Session, Intent/Status/Reason/Assumption enums
│  │   errors.py  sanitize.py  invariants.py
│  │   resolver/  tokens.py  clock_rules.py  date_rules.py  duration_rules.py  tz.py  resolve.py
│  ├─ services/
│  │   ports.py                     ExtractionPort, ReminderStore, Clock, IdGenerator
│  │   guard.py  extraction_validator.py  policy.py  target_resolver.py
│  │   create.py  reschedule.py  snooze.py  session.py  responses.py  agent.py   (handle())
│  ├─ llm/                          anthropic_client.py  replay_client.py  prompt.py
│  ├─ repositories/                 memory.py  json_file.py
│  ├─ infrastructure/               clock.py  ids.py  logging.py  contracts.py (loads schemas)
│  ├─ contracts/                    *.schema.json  (packaged copy; byte-equality test vs .speckit/contracts)
│  └─ interfaces/cli/               main.py
├─ tests/  unit/ property/ contract/ security/ architecture/ fault/ conftest.py
└─ evals/  dataset.json  dataset.sha256  golden/resolver.json  run_eval.py  scoring.py  reports/
```

Dependency rule: `interfaces → services → domain ← repositories/llm/infrastructure`. `domain` imports nothing outside stdlib + pydantic.

## 5. Component Design

### 5.1 Guard (`services/guard.py`) — FR-1.4, SAF-9
Trim; reject empty or > 1000 chars (`input_invalid`) **before** any LLM call. Reject lone surrogates. Normalise to NFC. Returns the normalised message that all span offsets refer to (INV-3 operates on this string).

### 5.2 ExtractionPort + adapters — SAF-1, SAF-8, SAF-9
- `Protocol.extract(message, ctx, candidate_titles) -> dict`.
- **Anthropic adapter:** system prompt fixed in `prompt.py`; the user message is placed inside delimiters as data; instructs "return only JSON per schema"; 10 s timeout → `LlmTimeout`. Only message, `ctx` (tz, date_order — **not** `now`, so the model can't do date math), and ≤ 20 candidate titles (80 chars) are sent (SAF-10).
- **Replay adapter:** serves `gold_extraction` from the dataset or recorded fixtures keyed by `(message_hash)`; supports fault injection (`timeout`, `malformed_json × n`) for F-01/F-02.
- **Validator** (`extraction_validator.py`): JSON-Schema check + INV-3 span fidelity. On failure `agent.py` re-calls **once** with the error text appended; second failure → `error/llm_schema_violation` (SAF-8).

### 5.3 Resolver (pure) — FR-3
Input: the `time` and `duration` span texts, `Ctx`, optional `previous_due`. Output: `Resolved(date?, time?, instant?, assumptions, issues)` where `issues` ∈ {`MISSING_DATE`, `MISSING_TIME_MERIDIEM`, `AMBIGUOUS_DATE_ORDER`, `VAGUE_DATE`, `PAST`, `OUT_OF_RANGE`}.

| Module | Rules |
|---|---|
| `tokens.py` | Case-fold, whitespace collapse, ordinal strip (`1st`), number words (`a`, `an`, `one`…`ten`). |
| `date_rules.py` | DT-1, DT-2, DT-3, DT-5, DT-6, DT-16 (one function each, ordered first-match chain). |
| `clock_rules.py` | DT-7, DT-8, DT-9; sets `time_meridiem` issue. |
| `duration_rules.py` | DT-4 (incl. month clamp), snooze durations, displacement ("back 2 hours"). |
| `tz.py` | DT-12 gap shift, DT-13 overlap fold, offset computation. Local→instant uses `zoneinfo` with explicit gap/overlap detection (round-trip test). |
| `resolve.py` | Composes date × time, applies DT-10/DT-11 defaults, then DT-14/15 bounds. |

Design points:
- A rule that does not match returns `None`; the chain order is documented. Unknown text → `VAGUE_DATE` (ask), never a guess.
- Clock access is only through `ctx.now` (INV-13); an architecture test greps for `datetime.now`/`utcnow`/`time.time`.
- Golden table (`evals/golden/resolver.json`, ≥150 rows) drives `tests/unit/test_resolver.py` — **100%** gate (EVAL-5b).

### 5.4 Policy (`services/policy.py`) — FR-4, SAF-4
A pure decision function: `decide(intent, extraction, resolved, target_match, session, store_view) -> Decision`. Decision table (evaluated top-down, first match wins):

| # | Condition | Decision |
|---|---|---|
| 1 | `intent=unsupported` | `refused/unsupported_intent` |
| 2 | `intent=unknown` | clarify `intent=unknown`, missing ⊇ {title, date} |
| 3 | Required fields missing or issue ∈ {MISSING_*, AMBIGUOUS_*, VAGUE_*, invalid duration} | clarify; `missing_fields` = all blockers; `question` for the highest-priority one (§4.3 order) |
| 4 | `round` would exceed 3 | `refused/max_clarifications_exceeded` |
| 5 | Issue PAST / OUT_OF_RANGE / title > 200 | matching `refused` |
| 6 | Target not found / cancelled / snooze cap | `refused/*` |
| 7 | Otherwise | commit |

Priority order of rows 3 vs 5: **ambiguity before refusal** only when the ambiguity changes the outcome (e.g. unresolved date can't be judged "past"); otherwise refuse (X-05).

### 5.5 Target resolution (`target_resolver.py`) — FR-5.1/5.2
Ordered strategies: id → exact title → case-insensitive token-subset → pronoun (`it/that/last one` = `session.last_touched`). Returns `Match(none | one | many)`; `many` truncates to 5 most-recently-updated. Only `scheduled`/derived-`fired` reminders are candidates; `cancelled` → `invalid_state`.

### 5.6 Mutation services — FR-2, FR-5, FR-6
- `create`: title = NFC(sanitize(trim(span))); length check; `id` from injected generator; stored via `store.add`.
- `reschedule`: new instant from resolver; displacement uses `previous_due`; preserves `id/title/created_at`; `updated_at = ctx.now`.
- `snooze`: `new = max(now, prev) + d`; `snooze_count += 1`; cap 20; absolute "until 6pm" is routed to reschedule (AC-6.6).
- All three return a **proposed new Reminder**; the single `store.commit` call happens in `agent.py` after the invariant checker passes (INV-8, PROP-13).

### 5.7 Session (`session.py`) — AC-4.4/4.5
In-memory dict `session_id → {partial, intent, round, last_touched, pending_since}`. A follow-up is merged with `partial` if the new extraction's intent is `create/unknown/same-intent` and supplies a missing field; otherwise state is discarded and the message is treated as a new request. Merge happens at the **extraction level** (spans from both turns), so the Resolver sees ordinary spans — which is what makes PROP-8 hold by construction.

### 5.8 Sanitiser (`sanitize.py`) — SAF-6
Strips C0/DEL, bidi controls (U+202A–E, U+2066–9), zero-width (U+200B–D, U+2060, U+FEFF); never alters markup/SQL. Applied to titles and to every `message` string.

### 5.9 Response builder + Invariant checker — INV-*
`responses.py` produces dicts from typed decisions with fixed user-facing templates (no free LLM text reaches the response → SAF-7 by construction). `invariants.py` runs INV-1 (jsonschema), INV-2, INV-5, INV-6, INV-9, INV-10, INV-11 on the candidate response **before** commit; any failure → `error/internal_error`, no write.

### 5.10 Stores — FR-7
`ReminderStore`: `add, get, list, update, commit(changes)`. `JsonFileStore` writes temp-file + `os.replace`, 2-space UTF-8; `fired` is never persisted. A shared contract test-suite runs against both implementations.

### 5.11 CLI — FR-8
`remind "<text>" [--json] [--session S] [--tz TZ] [--date-order DMY|MDY|unset]` → `handle()`; exit 0/2/3 per AC-8.2. Session default is a per-process id; `--session` plus the JSON store lets clarification span invocations only if the session is persisted — **v1 keeps sessions in memory**, so multi-turn is demonstrated through the Python API and an interactive `remind chat` loop (T040).

## 6. Evaluation Harness (`evals/`)

- `run_eval.py --mode replay|live [--split test|dev|all]` loads `evals/dataset.json`, verifies `dataset.sha256`, builds the store from `store_fixtures`, injects the fixture clock, runs each turn through `handle()`, and compares using the `comparison_rules` block in the dataset.
- `scoring.py` computes EVAL-1…EVAL-17 (point estimate, n, Wilson 95% interval), applies hard/soft gates, writes `evals/reports/<timestamp>-<mode>.json` + a Markdown summary, and diffs against `evals/reports/baseline.json` (EVAL-16).
- **Live mode** runs each case 3× (EVAL-13), records model id, prompt hash, and temperature in the report.
- **Replay mode is part of `make verify`**; live mode is not (Art. IV.8).
- **Metric ↔ dataset tag**: each case lists the `evidence` EVAL ids it feeds, so metrics are computed from the cases that declare them.
- Anti-gaming: dev/test split is fixed in the dataset; prompt tuning may read only `split=dev` results; `make eval-live` prints test-split numbers only in the release report.

## 7. Safety Mapping

| Rule | Mechanism | Test |
|---|---|---|
| SAF-1 | No tools; message delimited as data; LLM output restricted to schema | D-01, D-04, `test_prompt_injection.py` |
| SAF-2 | `now`/`tz` never read from text; `now` is not sent to the LLM | D-02 |
| SAF-3 | Policy: exactly one target; bulk → refuse | D-06, D-07 |
| SAF-4 | Policy table row 3; assumptions closed enum | A-*, M-*, N-03/04, INV-10 |
| SAF-5 | Schema forbids datetime/id in extraction (`additionalProperties:false`) | extraction-schema tests |
| SAF-6 | `sanitize.py` | X-03, D-05 |
| SAF-7 | Templated responses; generic `error.message`; leak scan in runner | D-03, global check |
| SAF-8/9/13 | Single retry, timeout, input cap, rollback | F-01…F-03, X-01, X-04 |
| SAF-10 | Prompt builder allow-list; log redaction filter | `test_privacy.py` |
| SAF-11 | env-only key; `detect-secrets` | gate |
| SAF-12 | Intent allow-list → refusal for off-topic | D-03 |

## 8. Phases & Ordering

Each phase ends with `make verify` green. Test tasks precede implementation tasks (Art. IV.1).

| Phase | Outcome | Depends on |
|---|---|---|
| 0 Foundation | Constitution, repo skeleton, tooling, harness, contracts loader | — |
| 1 Domain & Resolver | All DT-n rules, tz handling, sanitiser, golden table | 0 |
| 2 Services & stores | Guard, validator, policy, target resolver, create/reschedule/snooze, session, stores | 1 |
| 3 Agent pipeline | `handle()`, invariants, LLM adapters (replay first), fault paths | 2 |
| 4 Interfaces | CLI | 3 |
| 5 Properties & security | Hypothesis suite, injection/privacy tests | 3 |
| 6 Evaluation | Runner, scoring, replay gate, grow dataset to §9.2, live run, baseline | 3 (replay), 5 |
| 7 Hardening & docs | Coverage, mutation check on resolver/policy, README, release report | all |

Critical path: Resolver (1) → Policy/Services (2) → `handle()` (3) → eval gates (6). Resolver and stores can proceed in parallel; the replay adapter lets phases 2–5 proceed without any API key.

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Rule engine misses phrasings the LLM-extracted span contains | False clarifications (EVAL-7) | Default is *ask*, never guess; grow the golden table from eval failures; add phrases via tests first. |
| LLM span offsets are wrong (off-by-one) | INV-3 rejects valid intent | Validator may repair by unique `text` search **only when the text occurs exactly once**; otherwise counts as invalid. Measured in EVAL-2. |
| DST/timezone bugs | Wrong time silently | `tz.py` isolated; round-trip property test (local→UTC→local); B-07/B-08 + 6 DST golden rows. |
| Live eval variance / model drift | Flaky release gate | Pinned model id, temperature 0, 3 runs, consistency metric, baseline diff. |
| Eval overfitting | Inflated scores | Frozen hash, dev/test split, test numbers only in release report. |
| Small dataset ⇒ wide intervals | Weak evidence | Intervals reported; T045 grows to spec §9.2 volumes. |
| Windows missing tz database | Crashes on Windows | `tzdata` is a hard dependency; startup self-check. |
| Session state lost between CLI calls | Clarification can't continue | Documented v1 limitation; `remind chat` loop and API cover it. |

## 10. Definition of Done (per task / release)

- [ ] Acceptance criteria traced to passing tests (see `tasks.md` trace column)
- [ ] `make verify`: ruff, ruff format, mypy --strict, bandit, pip-audit, detect-secrets, unit + property + contract + security tests, coverage gate, **eval-replay hard gates**
- [ ] No hard-threshold waiver; soft misses recorded in the release report
- [ ] Contract schemas byte-identical to the packaged copy; dataset hash verified
- [ ] README: usage, config (`REMINDER_LLM_MODEL`, `ANTHROPIC_API_KEY`), limitations
