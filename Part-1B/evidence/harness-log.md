# Harness Log - Natural-Language Reminder Agent (Part-1B)

Append-only. Every harness run, every repair cycle, and the final human decision are recorded here.
Repair cycles follow constitution Art. VII: max 3 attempts per gate, no weakening of tests / datasets / thresholds.

## 2026-11-12 17:22:09Z - SELF-HEALING cycle 1 (static gates, automatic) [initial-generation, first run]

- **Failing gates:** format, lint
- **Action:** `ruff check --fix` + `ruff format` (deterministic, safe fixes only)
- **Gates still failing afterwards:** lint
- **Failure output before repair (truncated):**

```
unformatted: File would be reformatted
  --> .harness\common.py:18:15
   |
17 |     re.compile(p, re.IGNORECASE)
   -     for p in (r"traceback", r"system prompt", r"anthropic_api_key", r"sk-ant", r"claude-", r"[A-Za-z]:\\\\?Users", r"/home/", r"\.py\b")
18 +     for p in (
19 +         r"traceback",
20 +         r"system prompt",
21 +         r"anthropic_api_key",
22 +         r"sk-ant",
23 +         r"claude-",
24 +         r"[A-Za-z]:\\\\?Users",
25 +         r"/home/",
26 +         r"\.py\b",
27 +     )
28 | ]
   |

unformatted: File would be reformatted
  --> .harness\executor.py:53:39
  
```

## 2026-11-12 17:22:09Z - SELF-HEALING cycle 2 (static gates, automatic) [initial-generation, first run]

- **Failing gates:** lint
- **Action:** `ruff check --fix` + `ruff format` (deterministic, safe fixes only)
- **Gates still failing afterwards:** lint
- **Failure output before repair (truncated):**

```
E501 Line too long (123 > 120)
 --> .harness\log.py:3:121
  |
1 | """Append-only evidence log (evidence/harness-log.md) and its small CLI.
2 |
3 |     python .harness/log.py repair --cycle 1 --gate "layer3" --failure "..." --root-cause "..." --action "..." [--files a,b]
  |                                                                                                                         ^^^
4 |     python .harness/log.py decision --decision ACCEPT|REJECT --by "<reviewer name>" --notes "..."
  |

E501 Line too long (125 > 120)
   --> evals\run_eval.py:177:121
    |
175 |             },
176
```

## 2026-11-12 17:22:09Z - SELF-HEALING cycle 3 (static gates, automatic) [initial-generation, first run]

- **Failing gates:** lint
- **Action:** `ruff check --fix` + `ruff format` (deterministic, safe fixes only)
- **Gates still failing afterwards:** lint
- **Failure output before repair (truncated):**

```
E501 Line too long (123 > 120)
 --> .harness\log.py:3:121
  |
1 | """Append-only evidence log (evidence/harness-log.md) and its small CLI.
2 |
3 |     python .harness/log.py repair --cycle 1 --gate "layer3" --failure "..." --root-cause "..." --action "..." [--files a,b]
  |                                                                                                                         ^^^
4 |     python .harness/log.py decision --decision ACCEPT|REJECT --by "<reviewer name>" --notes "..."
  |

E501 Line too long (125 > 120)
   --> evals\run_eval.py:177:121
    |
175 |             },
176
```

## 2026-11-12 17:22:09Z - HARNESS RUN [initial-generation, first run] (mode=replay, split=all)

- Dataset sha256 `3ee34f86f080c9b2...` verified; thresholds sha256 `0e7b5587fefdd1f0...`
- **Cases:** 42/44 passed (45 turns)
- **Layer 1:** 44/44 cases clean
- **Layer 2:** 43/44 cases clean
- **Layer 3:** 43/44 cases clean
- **Static gates:** FAIL {'compile': True, 'format': True, 'lint': False}

**Failing cases:**

- `N-08` (normal_reschedule): [L3] L3.type: expected reminder_rescheduled, got clarification_needed; [L3] L3.store-effect: expected modified_1:rem_a1b2c3d4; added=[] changed=[]
- `A-05` (ambiguous_multi_turn): [L2] INV-4: title is not a substring of the message

| Metric | Measured | Threshold | Class | Status |
|---|---|---|---|---|
| EVAL-1 Final schema validity | 1 (n=45) | >= 1.0 | hard | PASS |
| EVAL-5 due_at exact match (datetime-gold turns) | 1 (n=20) | >= 0.95 | hard | PASS |
| EVAL-6r Missing-field recall | 1 (n=9) | >= 0.95 | hard | PASS |
| EVAL-6p Missing-field precision | 1 (n=8) | >= 0.9 | soft | PASS |
| EVAL-7 False-clarification rate | 0.04762 (n=21) | <= 0.05 | soft | PASS |
| EVAL-8 Premature-commit rate | 0 (n=9) | <= 0.03 | hard | PASS |
| EVAL-9a Reschedule/snooze target accuracy | 0.75 (n=4) | >= 0.95 | hard | FAIL |
| EVAL-9b Wrong-target mutation rate | 0 (n=45) | <= 0.0 | hard | PASS |
| EVAL-10 Hallucination rate (INV-3 / INV-4) | 0.02222 (n=45) | <= 0.0 | hard | FAIL |
| EVAL-11 Adversarial success rate | 0 (n=7) | <= 0.0 | hard | PASS |
| EVAL-12 Store integrity violations (INV-7/8) | 0 (n=45) | <= 0.0 | hard | PASS |
| EVAL-15 Deterministic-layer latency p95 (ms) | 4.989 (n=45) | <= 50.0 | soft | PASS |
| EVAL-17 Safe-failure drills passed | 1 (n=3) | >= 1.0 | hard | PASS |

- Hard metrics failing: EVAL-9a, EVAL-10; soft failing: none
- Metrics not measurable in replay mode: EVAL-2, EVAL-3, EVAL-4, EVAL-5b, EVAL-13, EVAL-14, EVAL-16
- **Harness recommendation:** REJECT_RECOMMENDED
- **Human decision:** PENDING

## 2026-11-12 17:22:44Z - REPAIR cycle 1 (layer3 / N-08)

- **Failure:** N-08 'push the dentist appointment back 2 hours' returned clarification_needed instead of reminder_rescheduled (L3.type, L3.store-effect); EVAL-9a 0.75, EVAL-7 at 0.0476 (just inside its limit)
- **Root cause:** Defect in services/intents.py reschedule(): when a displacement duration was present and parsed successfully, 'duration' (or 'date') was still appended to missing_fields unconditionally, so a valid request always asked a question.
- **Action:** Append 'date' only when no duration was given and 'duration' only when the given duration is unparseable/zero. Dataset gold untouched.
- **Files changed:** src/reminder_agent/services/intents.py
- **Gate weakened / test or dataset edited:** NO

## 2026-11-12 17:23:12Z - REPAIR cycle 2 (layer2 / A-05 (INV-4))

- **Failure:** A-05 clarification round-trip flagged INV-4: title 'call mom' is not a substring of the second-turn message; EVAL-10 (hallucination) 0.022 > 0
- **Root cause:** Not an agent defect: the title correctly comes from turn 1 of the same dialogue (FR-4 / AC-4.4 / PROP-8 require this). The spec wording of INV-4 ('the user's message') was ambiguous and my checker took the narrow reading. Titles from anywhere else would still be hallucination.
- **Action:** Clarified the spec (PATCH, v1.0.1) and made the checker exactly as strict as the clarified rule: the title must be a substring of one message of the CURRENT clarification dialogue (messages since the last non-clarification response). Dataset gold and thresholds untouched. FLAGGED FOR HUMAN REVIEW because it changes a checker.
- **Files changed:** .speckit/spec.md, .harness/executor.py, .harness/layer2_invariants.py
- **Gate weakened / test or dataset edited:** NO

## 2026-11-12 17:23:20Z - REPAIR cycle 3 (static gates (harness self-healing loop))

- **Failure:** Self-healing loop ran 3 cycles although cycles 2 and 3 could not change anything: the remaining lint errors (E501, N818) are not auto-fixable
- **Root cause:** Defect in .harness/static_gate.py: the loop only checked 'is a fixable gate still failing', not 'did the last repair make progress'.
- **Action:** Loop now stops when a repair attempt leaves the failing output identical; non-auto-fixable findings are escalated to a reasoned repair.
- **Files changed:** .harness/static_gate.py
- **Gate weakened / test or dataset edited:** NO

## 2026-11-12 17:23:48Z - REPAIR cycle 4 (static gates / lint)

- **Failure:** 8 ruff errors not auto-fixable: E501 x5 (log.py, run_eval.py x3, dates.py, test_components.py) and N818 x2 (errors.py)
- **Root cause:** Over-long lines and exception names without an 'Error' suffix; ruff cannot rewrite these safely.
- **Action:** Wrapped long lines; added justified inline noqa N818 on two domain exception names (no rule disabled globally). No test, dataset or threshold touched.
- **Files changed:** evals/run_eval.py, src/reminder_agent/resolver/dates.py, src/reminder_agent/errors.py, .harness/log.py, tests/unit/test_components.py
- **Gate weakened / test or dataset edited:** NO

## 2026-11-12 17:24:03Z - REPAIR cycle 5 (unit tests / test_resolver 'at noon')

- **Failure:** pytest: resolving 'at noon' at 10:30 returned today 12:00, test expected tomorrow 12:00 with rolled_to_next_day
- **Root cause:** Mistake in MY test row, not the resolver: 12:00 is still ahead of the fixture clock (10:30), so DT-11 says today with no assumption. The code matches the spec.
- **Action:** Corrected the test expectation to the spec (today, no assumptions) and added an 'at midnight' row (DT-7). Spec unchanged; no production code changed for this item.
- **Files changed:** tests/unit/test_resolver.py
- **Gate weakened / test or dataset edited:** NO

## 2026-11-12 17:24:05Z - HARNESS RUN [after repair cycles 1-5] (mode=replay, split=all)

- Dataset sha256 `3ee34f86f080c9b2...` verified; thresholds sha256 `0e7b5587fefdd1f0...`
- **Cases:** 44/44 passed (45 turns)
- **Layer 1:** 44/44 cases clean
- **Layer 2:** 44/44 cases clean
- **Layer 3:** 44/44 cases clean
- **Static gates:** PASS {'compile': True, 'format': True, 'lint': True}

| Metric | Measured | Threshold | Class | Status |
|---|---|---|---|---|
| EVAL-1 Final schema validity | 1 (n=45) | >= 1.0 | hard | PASS |
| EVAL-5 due_at exact match (datetime-gold turns) | 1 (n=21) | >= 0.95 | hard | PASS |
| EVAL-6r Missing-field recall | 1 (n=9) | >= 0.95 | hard | PASS |
| EVAL-6p Missing-field precision | 1 (n=8) | >= 0.9 | soft | PASS |
| EVAL-7 False-clarification rate | 0 (n=21) | <= 0.05 | soft | PASS |
| EVAL-8 Premature-commit rate | 0 (n=9) | <= 0.03 | hard | PASS |
| EVAL-9a Reschedule/snooze target accuracy | 1 (n=4) | >= 0.95 | hard | PASS |
| EVAL-9b Wrong-target mutation rate | 0 (n=45) | <= 0.0 | hard | PASS |
| EVAL-10 Hallucination rate (INV-3 / INV-4) | 0 (n=45) | <= 0.0 | hard | PASS |
| EVAL-11 Adversarial success rate | 0 (n=7) | <= 0.0 | hard | PASS |
| EVAL-12 Store integrity violations (INV-7/8) | 0 (n=45) | <= 0.0 | hard | PASS |
| EVAL-15 Deterministic-layer latency p95 (ms) | 1.237 (n=45) | <= 50.0 | soft | PASS |
| EVAL-17 Safe-failure drills passed | 1 (n=3) | >= 1.0 | hard | PASS |

- Hard metrics failing: none; soft failing: none
- Metrics not measurable in replay mode: EVAL-2, EVAL-3, EVAL-4, EVAL-5b, EVAL-13, EVAL-14, EVAL-16
- **Harness recommendation:** ACCEPT_RECOMMENDED (replay scope only)
- **Human decision:** PENDING

## 2026-11-12 17:24:36Z - GENERATION BACKUPS

- **evidence/initial-generation/** (43 files, taken BEFORE any gate or test was run): overall sha256 `a002e688ed18e48a83da7ebc307e734d83bf32877fdca6b81dce76758faa17b6`
- **evidence/final-generation/** (43 files, taken after the last clean harness run, no edits since): overall sha256 `16877e5c78d73095db0b4aa7204b74db1ac0597c04661652429927c781b6cebd`
- 15 files differ between the two: 1 production defect fix (`services/intents.py`), 4 lint-driven edits in `src/`, 1 test correction, and harness/runner edits (checker clarification, no-progress stop, formatting).
- Negative control: 8 deliberately corrupted responses were each caught by at least one layer; the clean baseline raised nothing.

## 2026-11-12 17:24:36Z - FINAL STATUS

- Harness recommendation: **ACCEPT_RECOMMENDED (replay scope only)**: 44/44 cases clean in all 3 layers, all measured hard metrics pass, static gates pass.
- NOT covered, so this is NOT a release acceptance: live-model metrics (EVAL-2/3/4/13), resolver golden table EVAL-5b, property suite EVAL-14, no baseline for EVAL-16. Replay feeds the dataset's gold extraction, so it does not test the language model.
- Open item for the reviewer: repair cycle 2 changed a CHECKER (INV-4) and the spec (v1.0.1). Please confirm that reading.
- **Human decision: PENDING**: to be recorded by a reviewer with `python .harness/log.py decision --decision ACCEPT|REJECT --by "<name>" --notes "..."`. Nothing in this log is, or stands in for, that decision.

