# Part-1A — Final Acceptance Record & Known Limitations

## Human decision

| Field | Value |
|---|---|
| Decision | **ACCEPT** |
| Reviewer | Subalari Leela Deepak (Roll No. 2026NS93073) |
| Date | 2026-11-13 |
| Notes | Harness PASS (162 tests, ~92% coverage). Accepted with the known limitations listed below: single-process file access, and the constitution says SQLite while the code uses a JSON file. |

> The harness result below is evidence for the reviewer, not the decision itself.

## Evidence summary (from `.harness/harness-log.md` and `evidence/`)

| Item | Result |
|---|---|
| Harness (lint, security, tests) | PASS |
| Tests | 162 passed, ~92% branch coverage (target ≥ 90%) |
| Static checks | ruff, ruff format, mypy --strict, bandit, forbidden-constructs scan, detect-secrets, pip-audit |
| First AI generation | Preserved in `evidence/initial-generation/` (SHA-256 in `evidence/initial-generation.sha256`) |
| First-run outcome | Tests 162/162 and mypy passed; ruff reported 23 findings, fixed by formatting and safe lint fixes with no assertion loosened |
| Final passing state | `evidence/final-generation/` + `evidence/harness-log.md` |

## Known limitations

1. **Single process only.** Writes are atomic (the file is never half-written) but two processes writing at once can lose an update (last write wins). No file locking.
2. **Storage is a JSON file**, not SQLite. The constitution (Article I) lists SQLite/SQLAlchemy, but the spec and plan chose a JSON file for v1; the repository interface keeps storage swappable. This deviation has not been formally amended in the constitution.
3. **Out of scope for v1:** multiple users, sub-tasks, recurring tasks, reminders, a web UI, other import/export formats.
4. A few edge branches are uncovered (for example the `__main__` API launcher and some CLI error paths), see the coverage table in the harness log.
5. The AC-traceability check is informational and does not fail the harness.
6. Human review of the spec, plan and tasks is recorded by this file; they were marked Approved on 2026-11-13.
