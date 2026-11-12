# Tasks — Natural-Language Reminder Agent

**Version:** 1.0.0 · **Date:** 2026-11-12 · **Implements:** `.speckit/plan.md` v1.0.0

**Legend**
- `[P]` = can run in parallel with other `[P]` tasks in the same phase (different files, no shared dependency).
- **T** = write the failing test first (Red). **I** = implement until it passes (Green). A task marked **I** may not start until its **T** is committed and failing.
- Every task ends with `make verify` green (from T004 onward). "Trace" lists the spec items the task proves.
- Dataset ids (e.g. `N-04`) refer to `evals/dataset.json`.

---

## Phase 0 — Foundation

| ID | Task | Depends | Trace |
|---|---|---|---|
| T001 | Write `.speckit/constitution.md` = Part-1A Articles II–X inherited, Art. I replaced by plan §2, plus the "harness never edits dataset/thresholds" rule. **Needs user confirmation.** | — | Plan §3 |
| T002 | `pyproject.toml`: deps (`pydantic`, `jsonschema`, `tzdata`, `anthropic`, `typer`), dev deps (`pytest`, `pytest-cov`, `hypothesis`, `ruff`, `mypy`, `bandit`, `pip-audit`, `detect-secrets`, `mutmut`), ruff rule sets, mypy strict, coverage gates (90/85, domain+services 95). Package skeleton with empty `__init__.py` + `__all__`. | T001 | Art. III, V |
| T003 | `.env.example`, `.gitignore`, pre-commit config (ruff, ruff-format, mypy, detect-secrets). | T002 | SAF-11 |
| T004 | **Harness:** `Makefile` + `python -m harness` running gates in order (compile → format → lint → types → security → tests → coverage → **eval-replay**), bounded 3-repair loop, log to `.speckit/harness-log.md`; refuses to run if `evals/dataset.sha256` mismatches. | T002 | Art. VII, EVAL-16 |
| T005 | **T** `tests/contract/test_schemas.py`: both schemas are valid Draft 2020-12; packaged copies in `src/reminder_agent/contracts/` are byte-equal to `.speckit/contracts/`; hand-written valid/invalid sample per `AgentResponse` type (valid passes, one extra key/missing key/bad enum fails). | T002 | INV-1, INV-6 |
| T006 | **I** `infrastructure/contracts.py`: load + cache schemas; `validate_response`, `validate_extraction`. Copy schemas into the package. | T005 | INV-1 |
| T007 | **T→I** `infrastructure/clock.py` (`Clock` Protocol, `SystemClock`, `FixedClock`), `ids.py` (`IdGenerator`, seeded fake). Architecture test: no `datetime.now/utcnow/time.time` outside `infrastructure/`. | T002 | INV-13, NFR determinism |
| T008 | **T→I** `tests/architecture/test_layers.py`: import-direction rules (`interfaces→services→domain←repos/llm/infra`), domain imports only stdlib+pydantic. | T002 | Art. II |

## Phase 1 — Domain & deterministic Resolver

| ID | Task | Depends | Trace |
|---|---|---|---|
| T009 | `domain/models.py` + `errors.py`: `Ctx`, `Reminder`, enums (`Intent`, `Reason`, `ErrorCode`, `Assumption`, `MissingField`), frozen dataclasses. Unit tests for validation (id pattern, title length, snooze bounds). | T002 | §4.2, INV-6 |
| T010 [P] | **T→I** `domain/sanitize.py`: strip C0/DEL, bidi, zero-width; NFC; trim; idempotent; markup/SQL preserved. | T009 | SAF-6, PROP-14, X-03, D-05 |
| T011 | **Golden table** `evals/golden/resolver.json` (≥150 rows: `{ctx, time_text, previous_due?, expected: instant\|issue, assumptions}`), ≥3 rows per DT-1…DT-16 (normal / boundary / negative), incl. 6 DST rows, N-01…N-04, B-01…B-09, A-01…A-03. Table-driven `tests/unit/test_resolver.py` (all failing). | T009 | AC-3.1, AC-3.2, EVAL-5b |
| T012 [P] | **I** `resolver/tokens.py` + `duration_rules.py` (DT-4 incl. month clamp, number words, displacement phrases, snooze durations 1 min–7 d). | T011 | DT-4, AC-6.3 |
| T013 [P] | **I** `resolver/clock_rules.py` (DT-7, DT-8, DT-9, noon/midnight, 24 h markers). | T011 | DT-7/8/9 |
| T014 [P] | **I** `resolver/date_rules.py` (DT-1, DT-2, DT-3, DT-5, DT-6, DT-16; weekday-today boundary). | T011 | DT-1/2/3/5/6/16, B-09, N-04 |
| T015 [P] | **T→I** `resolver/tz.py`: local→instant with gap shift (DT-12) and overlap-first (DT-13); round-trip property (local→UTC→local) over all transitions 2026–2028 for `America/New_York`, `Europe/London`, `Asia/Kolkata`, `Australia/Lord_Howe`. | T009 | DT-12/13, INV-2, B-08 |
| T016 | **I** `resolver/resolve.py`: compose date×time; defaults DT-10/11; bounds DT-14/15 (INV-5 inclusive at +60 s and +730 d); assumptions set. Golden table reaches **100%**. | T012–T015 | AC-3.1, INV-5, B-03/04/05, EVAL-5b |
| T017 | **T→I** `tests/unit/test_invariants_domain.py` + `domain/invariants.py`: INV-2, 5, 6, 9, 10, 11 as pure functions `check(response, ctx, store_before, store_after) -> list[Violation]`. | T009, T016 | INV-2/5/6/9/10/11 |

**Phase 1 exit:** `make verify` green; golden table 100%.

## Phase 2 — Services & stores

| ID | Task | Depends | Trace |
|---|---|---|---|
| T018 | `services/ports.py`: `ExtractionPort`, `ReminderStore`, `Clock`, `IdGenerator` Protocols. | T009 | Art. II.4 |
| T019 [P] | **T** `tests/contract/test_store_contract.py` shared suite: add/get/list/update, id uniqueness & non-reuse, immutability of returned objects, `fired` derived not stored, byte-identical on failed commit. | T018 | FR-7, INV-12, AC-7.3 |
| T020 [P] | **I** `repositories/memory.py`. | T019 | FR-7 |
| T021 [P] | **I** `repositories/json_file.py`: temp file + `os.replace`, 2-space UTF-8, injected write failure leaves old file identical. | T019 | AC-7.1, AC-7.2, F-03 |
| T022 [P] | **T→I** `services/guard.py`: empty/whitespace/>1000/lone surrogate → `input_invalid`, NFC; **asserts no extraction call is made** via a spy port. | T018 | AC-1.4, X-01, X-04, SAF-9 |
| T023 [P] | **T→I** `services/extraction_validator.py`: schema check; INV-3 span fidelity; unique-text offset repair (only if text occurs exactly once); rejects datetime/id keys. Cases: off-by-one, missing key, extra key, all spans null with `intent=create`. | T006 | INV-3, SAF-5, EVAL-2 |
| T024 | **T** `tests/unit/test_target_resolver.py`: id, exact, token-subset, pronoun with/without history, 0/1/2–5/>5 matches (use fixture S1), `cancelled` → invalid_state. | T018 | AC-5.1, AC-5.2, A-04, M-02, X-08 |
| T025 | **I** `services/target_resolver.py`. | T024 | FR-5.1/5.2 |
| T026 | **T** `tests/unit/test_policy.py`: table-driven over plan §5.4 rows 1–7 incl. priority order of `question_about` (target > title > date > time_meridiem > date_order > time > duration), round cap, ambiguity-vs-refusal ordering. Covers A-01…A-06, M-01…M-03, X-02, X-05…X-08. | T016, T025 | FR-4, AC-4.1–4.6, PROP-9, PROP-10 |
| T027 | **I** `services/policy.py` (pure). | T026 | FR-4 |
| T028 | **T** `tests/unit/test_mutations.py`: create (title provenance, 200/201), reschedule absolute vs displacement, identity preservation, snooze `max(now,prev)+d`, default 10 min, cap 20/21, absolute "until 6pm" → reschedule (no count bump). Covers N-01…N-08, B-06, X-07. | T016, T018 | FR-2/5/6, INV-9, PROP-7 |
| T029 | **I** `services/create.py`, `reschedule.py`, `snooze.py` returning proposed state, no store write. | T028 | FR-2/5/6 |
| T030 | **T→I** `services/session.py`: partial merge at extraction level, round counter, unrelated follow-up resets, interleaved sessions isolated, round-4 → refusal + cleared state. | T027 | AC-4.4, AC-4.5, A-05 |
| T031 [P] | **T→I** `services/responses.py`: fixed templates per type; sanitised `message`; generic `error.message` (no paths/class names). | T017 | SAF-7, INV-6, INV-11 |

## Phase 3 — Agent pipeline & LLM adapters

| ID | Task | Depends | Trace |
|---|---|---|---|
| T032 | **T** `tests/unit/test_agent_pipeline.py` using replay extraction = every dataset `gold_extraction`: runs all 44 cases through `handle()`, asserts per the dataset `comparison_rules` (types, fields, assumption sets, store effect, LLM-call bounds). Initially all fail. | T017, T027, T029–T031 | FR-1…FR-6, EVAL-1/5b/12 |
| T033 | **I** `services/agent.py` `handle(session_id, message, ctx)`: Guard → Extract (+1 repair) → Validate → Resolve → Policy → Mutate → Response → Invariant-check → **single commit** → return. Never raises (wraps unexpected exceptions into `error/internal_error` after rollback). | T032 | FR-8.3, INV-7/8, SAF-8, PROP-13 |
| T034 [P] | **T→I** `llm/replay_client.py`: dataset/fixture-backed extractor + fault injection (`timeout`, `malformed_json×n`). | T018 | F-01, F-02 |
| T035 | **T** `tests/fault/test_faults.py`: F-01 timeout, F-02 two malformed outputs (exactly 2 calls), F-03 store failure; plus extra faults at each pipeline stage (guard exception, resolver exception, invariant failure) → store byte-identical. | T033, T034 | PROP-13, SAF-13, EVAL-17 |
| T036 [P] | **T→I** `llm/prompt.py` + `anthropic_client.py`: fixed system prompt; message delimited as data; sends only message, tz, date_order, ≤20 candidate titles (80 chars); **not `now`**; JSON-only; no tools; 10 s timeout; model from `REMINDER_LLM_MODEL`; key from env. Tested with a mocked SDK (request payload assertions: no `tools`, no `now`, no store content). | T018 | SAF-1, SAF-2, SAF-9, SAF-10, SAF-11 |
| T037 | Pass `test_agent_pipeline.py` (T032) 44/44 and fault suite (T035). Fix defects in the code, **never** in the dataset. | T033, T035 | EVAL-1, 5b, 12, 17 |

## Phase 4 — Interface

| ID | Task | Depends | Trace |
|---|---|---|---|
| T038 | **T** `tests/contract/test_cli.py` via `CliRunner`: `--json` emits exactly one valid `AgentResponse`; exit codes 0 (created/rescheduled/snoozed/clarification), 2 (refused), 3 (error); `--help` works. | T037 | AC-8.1, AC-8.2 |
| T039 | **I** `interfaces/cli/main.py` (no business logic; calls `handle()` only; architecture test stays green). | T038 | FR-8 |
| T040 [P] | `remind chat` interactive loop keeping one in-memory session (demonstrates clarification round-trips); README note on the v1 session limitation. | T039 | AC-4.4, Plan §5.11 |

## Phase 5 — Properties & security

| ID | Task | Depends | Trace |
|---|---|---|---|
| T041 [P] | `tests/property/` (Hypothesis, ≥500 examples each, seeds printed): PROP-1 totality (arbitrary Unicode ≤5000 chars with a stub extractor emitting random/invalid spans), PROP-2 determinism, PROP-3 surface invariance, PROP-4 tz equivariance, PROP-5 clock translation, PROP-6 future-ness. | T037 | PROP-1…6, EVAL-14 |
| T042 [P] | `tests/property/` cont.: PROP-7 snooze monotonicity/order-independence, PROP-8 clarification equivalence (split generated complete requests), PROP-9/10 minimality & soundness, PROP-11 idempotence, PROP-12 isolation, PROP-13 failure atomicity, PROP-14 Unicode fidelity. | T037 | PROP-7…14, EVAL-14 |
| T043 [P] | `tests/security/`: prompt-injection corpus (≥40, also seeds the adversarial dataset), clock-spoof, leak scan (prompt text, key patterns, paths, class names in every response and log line), oversize/control-char input, privacy log redaction (emails/phones), `detect-secrets` baseline clean. | T037 | SAF-1…SAF-13, EVAL-11 |
| T044 | Dependency review: `pip-audit` clean; `bandit -r src` no medium/high; pin lock file. | T002 | Art. VI.6/7 |

## Phase 6 — Evaluation

| ID | Task | Depends | Trace |
|---|---|---|---|
| T045 | **Grow dataset** to spec §9.2 composition: 240 functional (60/50/50/30/25/15/10 by category), 40 adversarial, ≥20 paraphrase groups × ≥4 phrasings (`paraphrase_group` field), keep the dev/test split ≈30/70, hard-case share ≥25%. New cases get gold labels by **two independent reviewers**; disagreements recorded. Re-hash `dataset.sha256`. | T037 | §9.2, EVAL-13 |
| T046 | **T→I** `evals/scoring.py`: metric definitions for EVAL-1…17 (point estimate, n, Wilson 95%), hard/soft classification, regression diff vs `baseline.json`; unit-tested against synthetic result sets with known answers (including an all-pass and a single-hard-miss set). | T045 | §9.3, EVAL-16 |
| T047 | **I** `evals/run_eval.py`: `--mode replay|live`, `--split`, hash verification, fixture clock/store build, per-case report incl. failed field diffs; replay wired into `make verify` (hard gates EVAL-1, 5b, 10, 11, 12, 14, 17). | T046, T037 | §9.1 |
| T048 | **Live run** (`make eval-live`, needs `ANTHROPIC_API_KEY`, user-approved cost): 3 runs × all cases with pinned model, `temperature=0`; produce `evals/reports/<ts>-live.json/.md`. Tune prompt on **dev** only; re-run to final. | T047, T036 | EVAL-2…9, 13, 15 |
| T049 | **Accept baseline:** if all hard gates pass, copy the report to `evals/reports/baseline.json`; record waivers for any soft miss in the release notes. If a hard gate fails: root-cause (prompt / validator / resolver / policy), add a regression test or golden row first, fix, re-run — never edit dataset gold or thresholds. | T048 | EVAL-16 |

## Phase 7 — Hardening & docs

| ID | Task | Depends | Trace |
|---|---|---|---|
| T050 | Coverage ≥ 90% / 85% branch (domain+services ≥ 95%); `mutmut` on `domain/resolver` and `services/policy.py`; triage surviving mutants by adding tests. | T041–T043 | Art. IV.2/7 |
| T051 [P] | README: install (incl. `tzdata`), config, CLI usage, response schema summary, limitations (recurrence, sessions, English-only), how to run replay/live eval. | T039 | Art. VIII.5 |
| T052 [P] | Traceability check script: every FR/AC/INV/PROP/SAF/EVAL id in `spec.md` appears in ≥1 test or dataset case; fail on orphans. Wire into `make verify`. | T045 | Art. VIII.1 |
| T053 | Release report: threshold table with measured values, intervals, waivers, model id, dataset hash, known limitations. | T049, T050 | §9 |

---

## Dependency Overview

```
T001─T002─┬─T003, T004, T005─T006, T007, T008
          └─T009─┬─T010[P]
                 ├─T011─┬─T012[P] T013[P] T014[P]─┐
                 │      └────────────T015[P]──────┴─T016─T017
                 └─T018─┬─T019─┬─T020[P] T021[P]
                        ├─T022[P] T023[P] T024─T025─T026─T027─T030
                        ├─T028─T029          T031[P]
                        └─T034[P] T036[P]
T017+T027+T029+T030+T031 ─ T032 ─ T033 ─┬─ T035 ─ T037 ─┬─ T038─T039─T040
                                        └───────────────┼─ T041[P] T042[P] T043[P]
                                                        └─ T045─T046─T047─T048─T049
T049+T050 ─ T053            T039─T051[P]            T045─T052[P]
```

**Parallel opportunities:** after T011, the four resolver rule modules (T012–T015) are independent; after T018, stores, guard, validator, and the LLM adapters are independent; Phase 5 test suites (T041–T043) are independent.

## MVP Slice (if time is short)

T001–T004 → T009 → T011–T016 → T018, T020, T022–T033 → T037 → T047 (replay) — delivers a working, evaluated, key-free agent: create, reschedule, snooze, clarification, with every hard replay gate. Live LLM (T036, T048) and CLI (T038–T040) then add the model and the interface.

## Coverage Check

| Spec area | Tasks |
|---|---|
| FR-1…FR-8 | T022, T025–T033, T038–T039 |
| DT-1…DT-16 | T011–T016 |
| INV-1…INV-13 | T005–T008, T017, T023, T031, T033, T037 |
| PROP-1…PROP-15 | T041, T042, T045 (PROP-15 measured by EVAL-13) |
| SAF-1…SAF-13 | T010, T022, T031, T033, T036, T043 |
| EVAL-1…EVAL-17 | T046–T049 |
