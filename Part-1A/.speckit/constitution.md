# Constitution — Part-1A: Smart Todo & Task CLI/API

**Version:** 1.0.0 · **Ratified:** 2026-11-12 · **Status:** Active

This constitution is the non-negotiable set of engineering rules for the Smart Todo & Task CLI/API. Every spec, plan, task list, and line of code produced under Spec-Driven Development (`/speckit.specify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`) MUST comply. Where a plan conflicts with this document, the plan changes — not the constitution (amend via Article X).

Key words MUST / MUST NOT / SHOULD follow RFC 2119.

---

## Article I — Technology Stack (Fixed)

| Concern | Choice |
|---|---|
| Language | Python 3.11+ |
| CLI | Typer |
| API | FastAPI + Pydantic v2 |
| Persistence | SQLite via SQLAlchemy (repository pattern; swappable) |
| Tests | pytest, pytest-cov, hypothesis (property tests where useful) |
| Lint / format | ruff (lint + format), mypy (strict) |
| Security | bandit, pip-audit, detect-secrets |
| Task runner | `Makefile` (or `tasks.py`) exposing one command per gate |

> Assumption: the stack was not specified; Python was chosen for a combined CLI/API project. Changing it requires an amendment (Article X).

---

## Article II — Strict Modularity

1. **Layered architecture, one-way dependencies:**
   `interfaces (cli, api)  →  services  →  domain  ←  repositories/infrastructure`
   - `domain/`: pure entities, value objects, and rules (Task, Priority, Status, due-date logic). No I/O, no framework imports.
   - `services/`: use-case orchestration (create/update/complete/search/prioritise tasks). Depends only on domain and repository *interfaces*.
   - `repositories/`: persistence behind abstract interfaces (`Protocol`/ABC). Only layer allowed to touch the database.
   - `interfaces/cli` and `interfaces/api`: thin adapters — parse input, call a service, format output. **No business logic.**
2. **CLI and API share the same services.** Any feature MUST be implemented once in `services/` and exposed through both interfaces; duplicating logic is a violation.
3. **No circular imports; no cross-layer shortcuts** (e.g., API handler importing SQLAlchemy). Enforce with `ruff` import rules and an architecture test (`tests/architecture/`).
4. **Dependency injection** for repositories, clock, and ID generation — no hidden globals or singletons. This makes time-dependent "smart" features (due dates, overdue detection) deterministic in tests.
5. **Module limits:** a module SHOULD stay under 300 lines; a module with a single clear responsibility; public API of each package declared in `__init__.py` via `__all__`.
6. **Smart features are isolated:** prioritisation/suggestion/NLP-style date parsing live in their own package (`domain/smart/` or `services/smart/`) behind an interface so they can be replaced or disabled without touching core CRUD.

---

## Article III — Clean Code Practices

1. **Naming & intent:** descriptive, domain-aligned names; no abbreviations except universally known ones. Code reads like the spec.
2. **Small units:** functions do one thing, SHOULD be ≤ 25 lines, cyclomatic complexity ≤ 10 (enforced by ruff `C901`), ≤ 4 parameters (group into dataclasses/Pydantic models otherwise).
3. **Full type hints** on all public and private functions; `mypy --strict` MUST pass. No untyped `Any` without a justifying comment.
4. **No magic values:** constants and enums for statuses, priorities, limits, and messages.
5. **Explicit errors:** a domain exception hierarchy (`TodoError` → `TaskNotFoundError`, `ValidationError`, …). Never use bare `except:`; never swallow exceptions silently. Interfaces map domain errors to CLI exit codes / HTTP status codes in one place.
6. **Docstrings** (Google style) on every public module, class, and function describing behaviour, not restating the code. Comments explain *why*.
7. **Immutability by default:** prefer frozen dataclasses / value objects; no mutable default arguments.
8. **DRY, but not at the cost of clarity;** YAGNI — implement only what the current spec requires.
9. **No dead code, commented-out code, or unresolved `TODO`s** in merged work (a TODO must reference a task ID).
10. **Deterministic behaviour:** time, randomness, and UUIDs are injected, never called directly in domain/service code.

---

## Article IV — Robust Unit Testing (Test-First)

1. **Test-first workflow:** for each task, write failing tests derived from the spec's acceptance criteria *before* implementation (Red → Green → Refactor). Tests are committed alongside or before the code they cover.
2. **Coverage gates:** overall ≥ **90%** line and ≥ **85%** branch coverage; `domain/` and `services/` ≥ **95%**. A drop below the gate fails the build.
3. **Test pyramid:**
   - *Unit* (majority): fast, isolated, no I/O; repositories replaced with in-memory fakes.
   - *Integration*: real SQLite (temp/in-memory) for repositories.
   - *Contract/E2E*: API via FastAPI `TestClient`; CLI via Typer `CliRunner`. Both MUST exercise the same scenarios to prove parity.
4. **Test quality:** one behaviour per test; Arrange-Act-Assert; names like `test_<unit>_<condition>_<expected>`; no test interdependence or order reliance; no sleeping — use an injected fake clock.
5. **Edge cases are mandatory:** empty/whitespace titles, oversize input, past/invalid due dates, duplicate tasks, unknown IDs, boundary priorities, Unicode, concurrent updates, empty database.
6. **Bug rule:** every defect fix MUST begin with a failing regression test that reproduces it.
7. **Quality of tests is checked:** mutation testing (`mutmut`) SHOULD be run on `domain/` and `services/` before release; surviving mutants are triaged.
8. Tests MUST NOT call real network services or depend on the developer's machine state.

---

## Article V — Syntax & Lint Guard

1. **Tools:** `ruff check`, `ruff format --check`, and `mypy --strict` are the single source of style truth. Configuration lives in `pyproject.toml`; no per-file ignores without a written justification.
2. **Required ruff rule sets:** `E, F, W, I, N, UP, B, C4, C90, SIM, PL, RUF, S, D, ANN, PT, T20` (no stray `print` outside the CLI output layer).
3. **Zero warnings policy:** lint, format, and type checks MUST pass with **no errors and no warnings**.
4. **Enforcement points (defence in depth):**
   - Editor: format/lint on save.
   - **Pre-commit hook:** ruff, ruff-format, mypy, detect-secrets. Commits that fail are rejected.
   - **CI / `make check`:** identical gates re-run; hooks cannot be the only line of defence.
5. **Syntax guard:** before any generated or edited file is accepted, it MUST compile (`python -m compileall`) and pass lint. AI-generated code is held to the same gate as human code — no exceptions.

---

## Article VI — Security Guard

1. **Input is hostile:** all external input (CLI args, API bodies, query params, files) is validated by Pydantic models with explicit length, type, and range limits at the interface boundary.
2. **No injection:** all DB access uses parameterised queries / ORM; no string-built SQL; no `eval`, `exec`, `pickle` of untrusted data, `shell=True`, or `yaml.load` (use `safe_load`).
3. **Secrets:** no credentials, tokens, or keys in source, tests, fixtures, or logs. Configuration via environment variables / `.env` (git-ignored) with a committed `.env.example`. `detect-secrets` runs in pre-commit and CI.
4. **API hardening:** authentication on all non-public endpoints, per-user data isolation (a user can never read/modify another user's tasks), rate limiting, request size limits, strict CORS allow-list, and secure HTTP headers.
5. **Safe errors & logging:** responses never leak stack traces, SQL, or file paths; logs never contain secrets or personal data; structured logging with correlation IDs.
6. **Dependencies:** pinned versions (lock file), minimal footprint, `pip-audit` MUST report no known high/critical vulnerabilities; new dependencies require justification in the plan.
7. **Static security scan:** `bandit -r src` MUST pass with no medium/high findings; any suppressed finding needs an inline `# nosec` plus reason.
8. **Least privilege & safe defaults:** local DB file created with restrictive permissions; API binds to localhost by default; destructive operations require explicit confirmation (CLI `--yes`) or explicit intent in the API.
9. **Security tests:** a dedicated `tests/security/` suite covers injection payloads, oversize/malformed input, authz boundary violations, and error-leak checks.

---

## Article VII — Self-Healing Harness

A single automated harness (`make verify` / `python -m harness`) runs every gate and attempts bounded, safe recovery when one fails.

**Gate order (fail-fast with full report):**
1. Syntax/compile → 2. Format → 3. Lint → 4. Type check → 5. Security scan (bandit, pip-audit, detect-secrets) → 6. Unit tests → 7. Integration/contract tests → 8. Coverage gate.

**Self-healing loop:**
1. **Detect:** run the gates; capture structured results (gate, file, line, rule, message).
2. **Classify** each failure:
   - *Auto-fixable, deterministic* (formatting, import order, safe ruff fixes): apply `ruff format` and `ruff check --fix` automatically.
   - *Needs reasoning* (type errors, failing tests, security findings, coverage gaps): feed the precise failure output back to the implementing agent/developer to repair the **code under test or the code at fault**.
3. **Re-run** the failed gate and all earlier gates (a fix must not regress them).
4. **Bound the loop:** maximum **3** repair attempts per gate. If still failing, STOP and escalate with a clear report (what failed, what was tried, suspected cause). Never loop indefinitely.
5. **Record:** every run and repair appends to `.speckit/harness-log.md` (timestamp, gate, failure, action, outcome) for traceability.

**Hard safety rules for healing (anti-cheating):**
- MUST NOT weaken the gate to get green: no deleting/skipping/`xfail`-ing tests, no lowering coverage thresholds, no adding blanket `# noqa` / `# type: ignore` / `# nosec`, no loosening lint or security config.
- MUST NOT alter tests to match buggy behaviour; a test changes only when the **spec** changes.
- MUST NOT touch files outside the failing scope without stating why; auto-fixes limited to the working tree (no destructive git operations, no deleting user data).
- A repair that changes behaviour requires a spec/plan reference.
- Runtime resilience (product-level self-healing): the app SHOULD detect and recover from a missing/corrupt DB file (re-initialise schema, back up the corrupt file), apply schema migrations idempotently, and retry transient DB locks with bounded backoff.

---

## Article VIII — Spec-Driven Workflow Rules

1. **Spec first:** no code without a spec section and acceptance criteria; every task in `/speckit.tasks` traces to a requirement, and every test traces to an acceptance criterion.
2. **Plan must pass a constitution check** (gates Articles II–VII) before tasks are generated; violations require documented justification in a "Complexity/Deviation" table.
3. **Small, reviewable increments:** each task is independently buildable and testable; `make verify` MUST be green at the end of every task.
4. **CLI/API parity:** each user story states both CLI and API behaviour, or explicitly marks one as out of scope.
5. **Documentation is part of done:** README usage, API docs (OpenAPI auto-generated and accurate), CLI `--help` text, and spec updated with the change.

---

## Article IX — Definition of Done

A task is done only when ALL hold:
- [ ] Acceptance criteria met and traceable to tests
- [ ] Tests written first, passing, coverage gates satisfied
- [ ] `ruff`, `ruff format`, `mypy --strict` clean
- [ ] `bandit`, `pip-audit`, `detect-secrets` clean
- [ ] Layering/architecture tests pass; no business logic in interfaces
- [ ] Self-healing harness (`make verify`) reports green with no gate weakened
- [ ] Docs/help text updated

---

## Article X — Governance & Amendment

1. This constitution supersedes all other practices for Part-1A.
2. Amendments require: a written rationale, impact on existing specs/plans, a version bump (semver: MAJOR = removed/reversed principle, MINOR = new/expanded rule, PATCH = clarification), and an updated "Last amended" date.
3. Every `/speckit.plan` and `/speckit.analyze` run MUST check compliance; unjustified violations block progress.

**Last amended:** 2026-11-12
