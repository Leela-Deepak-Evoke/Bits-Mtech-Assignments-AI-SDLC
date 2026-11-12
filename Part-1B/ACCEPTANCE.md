# Part-1B — Final Acceptance Record & Known Limitations

## Human decision

| Field | Value |
|---|---|
| Decision | **ACCEPT (conditional)** |
| Reviewer | Subalari Leela Deepak (Roll No. 2026NS93073) |
| Date | 2026-11-13 |
| Notes | Deterministic pipeline accepted: 44 of 44 cases pass, with the failure and repair history preserved. Live model (Groq gpt-oss-120b) accepted as a prototype only: it miscounts title positions (INV-3) and is 90% stable across runs. See known limitations. |

Record it in the log too, from the `Part-1B` folder:

```bash
python .harness/log.py decision --decision ACCEPT --by "<your name>" --notes "<why>"
```

> The harness recommendation is evidence for the reviewer, not the decision itself.

## Evidence summary (from `evidence/`)

| Item | Result |
|---|---|
| Evaluation cases | 44 cases, 45 turns (requirement: at least 15) |
| Deterministic pipeline (`evals/run_eval.py`, replay) | 44/44 cases pass on all 3 layers, all hard metrics pass |
| First run | Failed: static lint gate, EVAL-9a (target accuracy 0.75), EVAL-10 (hallucination 0.022) |
| Repairs | 5 repair cycles logged (cases N-08, A-05, lint, unit test "at noon"); no dataset or threshold edited |
| After repair | All measured metrics pass; log in `evidence/harness-log.md` |
| Unit tests | 91 passed |
| Non-deterministic pipeline (`evals/run_live_eval.py`) | Run live against Groq: 41 cases x 3 runs. See limitation 1 |
| Generation snapshots | `evidence/initial-generation*` and `evidence/final-generation*` with SHA-256 files |

## Known limitations

1. **Live results exist, but the model is not perfect.** Real run on 2026-11-12 with Groq `openai/gpt-oss-120b`, 41 cases x 3 runs
   (the 3 fault-injection drills are skipped), saved in `evidence/live-eval-results.json`:

   | Metric | Measured |
   |---|---|
   | EVAL-2 first-pass extraction validity | 0.857 (n=126) |
   | EVAL-3 intent accuracy | 1.0 (n=120) |
   | EVAL-4 title-span accuracy | 0.913 (n=69) |
   | EVAL-13 run-to-run stability | 0.902 (n=41); unstable cases: N-06, N-07, B-06, X-07 |
   | Final response type equals expected | 115 of 123 (93.5%) |
   | Layer 2 safety findings | 65, all INV-3: the model's span offsets (`start`/`end`) do not match `message[start:end]` |

   Cause of the INV-3 findings: the model writes the right text but miscounts character offsets. These live numbers are reported as measured.
   No threshold or dataset was changed. Intermittent `error` responses in the unstable cases are from API failures or invalid first output;
   they were not investigated further. Possible fix for the reviewer to decide: have the code compute offsets from the returned text
   (a spec change, so not done here).
2. The Anthropic adapter has only been unit-tested with a stub client. The live run used the Groq adapter (`llm/groq_client.py`), a different model family from the spec's default `claude-haiku-5-5`.
3. Replay results prove the deterministic pipeline (resolver, policy, store, guardrails) and not the language model.
4. Not yet measured: EVAL-5b (resolver golden table of 150+ rows), EVAL-14 (property suite), EVAL-16 (no baseline exists yet).
5. Out of scope: recurring reminders, cancel/delete, bulk operations, notification delivery, multi-user, non-English dates, voice.
6. Session state (pending clarifications) is in memory per session and is not kept across processes.
7. The spec, plan and tasks were marked Approved by the reviewer on 2026-11-13 (this record).
