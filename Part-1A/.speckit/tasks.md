# Tasks — Smart Todo & Task CLI/API

**Version:** 1.0.0 · **Date:** 2026-11-12 · **Status:** Ready for `/speckit.implement`
**Inputs:** `constitution.md` v1.0.0 · `spec.md` v1.0.0 · `plan.md` v1.0.0

---

## How to read this file

- **Order is sequential.** Do tasks in ID order unless a task is marked `[P]` (safe to run in parallel with its neighbours in the same phase; no shared files).
- **Test-first (Constitution Art. IV.1).** Every `TEST` task is committed and seen **failing (Red)** before its paired `IMPL` task; the IMPL task's *Done when* is "paired tests Green".
- **Atomic.** One task = one concern, normally one or two files, one reviewable change.
- **Traceable.** *Traces* lists the spec acceptance criteria (AC), requirements (FR) or non-functional requirements (NFR) the task proves. Test names MUST embed the AC id (e.g. `test_ac_5_2_tag_filter_all_match`) so `.harness` can verify traceability (T068).
- **Gate.** After every task, `python .harness/run.py` (from T006 onward) MUST be green for the gates that exist so far, with no gate weakened (Art. VII).

**Task types:** `SETUP` · `TEST` · `IMPL` · `DOC` · `HARNESS`

---

## Phase 0 — Governance & Scaffolding

| ID | Type | Task | Depends | Traces | Done when |
|---|---|---|---|---|---|
| T001 | DOC | Amend `.speckit/constitution.md` to v1.1.0 per plan §1.3: persistence = JSON file behind repository interface; harness invoked as `python .harness/run.py`; replace "DB migrations/locks" with "schema version check + corrupt-file recovery". Update version + *Last amended*. | — | Plan §1.3 | Diff shows only those three changes; version = 1.1.0. |
| T002 | SETUP | Create `pyproject.toml`: project metadata (Python ≥3.11), pinned deps (typer, fastapi, uvicorn, pydantic≥2), dev deps (pytest, pytest-cov, hypothesis, ruff, mypy, bandit, pip-audit, detect-secrets, pre-commit, httpx, mutmut); `[tool.ruff]` with rule sets from Art. V.2; `[tool.mypy] strict = true`; `[tool.pytest]` (testpaths, strict markers); `[tool.coverage]` (branch = true, `fail_under = 90`); script `todo = "todo.interfaces.cli.main:app"`. | T001 | NFR-4 | `pip install -e .[dev]` succeeds; `ruff --version`, `mypy --version`, `pytest --version` run. |
| T003 | SETUP | Create package skeleton with empty `__init__.py` (each declaring `__all__ = []`): `src/todo/{domain,domain/smart,services,repositories,infrastructure,interfaces/cli,interfaces/api,app}` and `tests/{unit,integration,contract,security,architecture,performance}`. | T002 | Plan §3 | `python -c "import todo"` works; tree matches plan §3. |
| T004 | SETUP `[P]` | Add `.gitignore` (`.env`, `todo_data.json`, `*.corrupt-*`, `.venv`, caches, coverage), `.env.example` (`TODO_DATA_FILE`, `TODO_API_KEY` empty, host/port), README stub. | T002 | NFR-3 (no secrets) | Files exist; `.env.example` contains no real secret. |
| T005 | SETUP `[P]` | Add `.pre-commit-config.yaml`: ruff, ruff-format, mypy, detect-secrets, check compile. Generate `.secrets.baseline`. | T002 | Art. V.4, NFR-3 | `pre-commit run --all-files` passes on the skeleton. |
| T006 | HARNESS | Harness core v0 in `.harness/`: `gates.py` (gates 1–4: compileall, ruff format --check, ruff check, mypy strict), `report.py` (structured result + append to `.speckit/harness-log.md`), `run.py` (`--gate`, `--no-heal`; fail-fast; non-zero exit on failure). No healing yet. | T003 | Art. VII, NFR-4 | `python .harness/run.py` exits 0 on skeleton; a deliberately broken scratch file makes it exit non-zero and writes a log entry (then revert scratch). |
| T007 | SETUP `[P]` | Thin `Makefile` (`check`, `test`, `verify` → `python .harness/run.py`) and `.github/workflows/ci.yml` running `verify` on **windows-latest and ubuntu-latest**. | T006 | NFR-6, Art. V.4 | `make verify` (or documented PowerShell equivalent) runs the harness; CI file lints. |
| T008 | TEST | Architecture tests `tests/architecture/test_layers.py` (AST-based): (a) `domain` imports no other project layer nor typer/fastapi/pydantic; (b) `services` imports only `domain` + `repositories` + `services.ports`; (c) `interfaces/*` do not import `infrastructure` (only `app.container` may); (d) no `datetime.now`/`date.today`/`utcnow` calls in `domain/` or `services/`. | T003 | FR-12.2, NFR-2 | Tests pass on empty skeleton (vacuous) and are collected by the harness. |

---

## Phase 1 — Domain Foundations

| ID | Type | Task | Depends | Traces | Done when |
|---|---|---|---|---|---|
| T009 | TEST+IMPL | `domain/errors.py` with tests: `TodoError` base; `ValidationError`, `TaskNotFoundError`, `InvalidTransitionError`, `StorageError`, `StorageFormatError`; each carries a stable `code` (`validation_error`, `not_found`, `invalid_transition`, `storage_error`) and message. Test asserts hierarchy + codes. | T008 | FR-11 error codes, Art. III.5 | Hierarchy test green. |
| T010 | TEST | `tests/unit/test_task_model.py`: `Status` values `pending/in_progress/completed`; `Priority` ranks low=1, medium=2, high=3 and string round-trip; `Task` is frozen (assignment raises). | T009 | §3.1, §2 | Tests exist and fail (Red). |
| T011 | IMPL | `domain/task.py`: `Status(StrEnum)`, `Priority(IntEnum)` with `from_str`, frozen slotted `Task` dataclass (fields per spec §3.1, `tags` as tuple). | T010 | §3.1 | T010 green. |
| T012 | IMPL `[P]` | `services/ports.py` (`Clock` Protocol: `now() -> datetime`, UTC) and `repositories/base.py` (`Store` frozen dataclass `next_id`, `tasks`; `TaskRepository` Protocol: `load_all()`, `save_all(store)`). | T011 | Plan D2, D4 | Modules type-check under `mypy --strict`; T008 still green. |
| T013 | SETUP | `tests/conftest.py`: `FakeClock` (settable, advanceable, UTC-aware), `InMemoryTaskRepository` (records `save_count`), `tmp_data_file` fixture. | T012 | NFR-2 | Fixtures importable; a smoke test uses each. |

---

## Phase 2 — Domain Rules (validation, transitions, overdue, update)

| ID | Type | Task | Depends | Traces | Done when |
|---|---|---|---|---|---|
| T014 | TEST | `tests/unit/test_task_validation.py::title`: empty, whitespace-only → `ValidationError`; 200 chars ok, 201 rejected; `"  Buy milk  "` → `"Buy milk"`; Unicode (`"café ✅"`, `"日本語"`) preserved. | T013 | AC-1.2, AC-1.3, AC-1.4, NFR-5 | Red. |
| T015 | IMPL | `domain/rules.py::normalize_title`. | T014 | as T014 | T014 green. |
| T016 | TEST | Tag tests: `["Work","work"," Home "]`→`["work","home"]`; >10 tags, 31-char tag, `"a b"`, `"#x"`, empty-string tag rejected; exactly 10 and 30 accepted; order = first occurrence. | T015 | AC-1.5, AC-1.6 | Red. |
| T017 | IMPL | `normalize_tags` (regex `^[a-z0-9][a-z0-9_-]*$`). | T016 | as T016 | Green. |
| T018 | TEST | Priority outside enum (`"urgent"`) rejected; `due_date`: `"2026-02-30"`, `"12/11/2026"` rejected, `"2020-01-01"` and `"9999-12-31"` accepted; description 2000 ok / 2001 rejected. | T017 | AC-1.7, AC-1.8, §3.1 | Red. |
| T019 | IMPL | `parse_priority`, `parse_due_date`, `normalize_description` in `rules.py`. | T018 | as T018 | Green. |
| T020 | TEST | `build_task` tests: defaults (`pending`, `medium`, `[]`, `""`, null due, null `completed_at`, `created_at == updated_at`); first id 1, next 2; function signature **does not accept** `id/status/created_at/updated_at/completed_at` as user fields (passing them raises `TypeError`/`ValidationError`). | T019 | AC-1.1, AC-1.9, AC-1.10 | Red. |
| T021 | IMPL | `rules.py::build_task(input, id, now)` composing T015/T017/T019. | T020 | as T020 | Green. |
| T022 | TEST | `tests/unit/test_transitions.py`: `parametrize` over **all 9** from→to cells (§3.3) — ✓ cells succeed, ✗ cells (incl. same-state, `completed→in_progress`) raise `InvalidTransitionError` with task unchanged; `completed_at` set on →completed, cleared on completed→pending; `updated_at` updated on success only; unknown status string → `ValidationError` (not `InvalidTransitionError`). | T021 | AC-6.1–6.5, FR-6 | Red. |
| T023 | IMPL | `rules.py::transition(task, new_status, now)`; transition table as a constant mapping. | T022 | as T022 | Green. |
| T024 | TEST | `test_overdue.py` with today=2026-11-12: due 11-11 pending → overdue; due 11-12 → not; due 11-13 → not; completed due 11-11 → not; no due → not; in_progress due 11-11 → overdue. | T021 | AC-5.8, §2 | Red. |
| T025 | IMPL | `rules.py::is_overdue(task, today)`. | T024 | as T024 | Green. |
| T026 | TEST | `apply_update` tests: only `priority` changes others intact + `updated_at` = now; `tags` replaces list; `tags=[]` clears; `due_date=None` clears; invalid value raises and original task object unchanged; empty change-set → `ValidationError`; attempting to set `status`/`id`/`created_at` → rejected. | T025 | AC-3.1–3.5, AC-3.7 | Red. |
| T027 | IMPL | `rules.py::apply_update(task, changes, now)` using sentinel for "unset" vs explicit `None`. | T026 | as T026 | Green. |

---

## Phase 3 — Query & Smart Logic (pure domain)

| ID | Type | Task | Depends | Traces | Done when |
|---|---|---|---|---|---|
| T028 | TEST | `tests/unit/test_filtering.py` using spec fixtures A(work,urgent) B(work) C(none): `tag=work`→A,B; `work`+`urgent` (all)→A; `urgent`+`home` `any`→A; case-insensitive `WORK`; unknown tag→`[]`; status filter; invalid status/match → `ValidationError`; combined status+priority+tag AND; `overdue=true/false`; empty input list → `[]`. | T027 | AC-5.1–5.9, AC-2.4 | Red. |
| T029 | IMPL | `domain/query.py::filter_tasks(...)`. | T028 | as T028 | Green. |
| T030 | TEST | `tests/unit/test_sorting.py`: default priority-desc `[2,4,3,1]`; `priority asc` `[1,3,2,4]`; `due_date asc` `[3,1,2]` / `desc` `[1,3,2]` (None last both ways); `created_at` and `id` keys; id-asc tie-break for every key/order; invalid `sort`/`order` → `ValidationError`; filter-then-sort composition; repeated calls identical. | T029 | AC-7.1–7.6 | Red. |
| T031 | IMPL | `query.py::sort_tasks(tasks, key, order)` (single stable key function; None-last handled explicitly). | T030 | as T030 | Green. |
| T032 | TEST | `tests/unit/test_next_task.py`: overdue-low beats not-overdue-high; two overdue → higher priority; equal priority → earlier due; equal → `in_progress` over `pending`; then lowest id; completed-only / empty → `None`. | T031 | AC-8.1–8.4 | Red. |
| T033 | IMPL | `domain/smart/next_task.py::select_next(tasks, today)` as one composite sort key. | T032 | as T032 | Green. |
| T034 | TEST `[P]` | Hypothesis property tests: sort result is a permutation of input; sorting twice = once (idempotent); `normalize_tags` idempotent and ≤10; `filter` result ⊆ input; `select_next` result ∈ non-completed input. | T033 | AC-7.6, NFR-4 | Properties pass (≥100 examples). |

---

## Phase 4 — JSON Persistence

| ID | Type | Task | Depends | Traces | Done when |
|---|---|---|---|---|---|
| T035 | TEST | `tests/integration/test_serialization.py`: `to_dict`→`from_dict` round-trip equality (incl. Unicode, null fields); output has **no** `overdue` key; `version == 1`; datetimes serialise as UTC `…Z`; missing `tasks`, bad enum, bad date, wrong types → `StorageFormatError`; `version: 2` → `StorageError` (newer). | T033 | AC-9.4, AC-9.7, NFR-5 | Red. |
| T036 | IMPL | `infrastructure/serialization.py` (`to_dict`, `from_dict`, `SUPPORTED_VERSION = 1`). | T035 | as T035 | Green. |
| T037 | TEST | `tests/integration/test_file_io_atomic.py`: write creates parent dir; file is UTF-8, 2-space indent, trailing newline; with `os.replace` monkeypatched to raise → original file **byte-identical**, no temp file left, `StorageError` raised; unwritable path → `StorageError`, nothing left behind; bounded retry (3×) on transient `PermissionError` from `os.replace` then success. | T036 | AC-9.2, AC-9.3, AC-9.4, AC-9.8 | Red. |
| T038 | IMPL | `infrastructure/file_io.py`: `atomic_write_text(path, text)` (temp file in same dir → write → flush → fsync → `os.replace`; cleanup in `finally`; bounded retry); `read_text_if_exists`. | T037 | as T037 | Green. |
| T039 | TEST | `tests/integration/test_json_repository.py`: missing file → empty store (`next_id=1`), file not created until first save; save-then-new-instance load returns same data; `next_id` persists across instances (delete highest, create → id not reused); 0-byte file, invalid JSON, schema-invalid → file renamed `<name>.corrupt-<UTCts>` with original bytes preserved, empty store returned, warning emitted; newer version → `StorageError`, file untouched; a failed mutation path never writes (via service in T044). | T038 | AC-9.1, 9.2, 9.5, 9.6, 9.7, AC-4.3 | Red. |
| T040 | IMPL | `infrastructure/json_repository.py::JsonFileTaskRepository` (+ quarantine helper, warning via `logging` and a returned/recorded warning list the CLI can print to stderr) and `infrastructure/clock.py::SystemClock`. | T039 | as T039 | Green. |

---

## Phase 5 — Service Layer & Composition

| ID | Type | Task | Depends | Traces | Done when |
|---|---|---|---|---|---|
| T041 | TEST | `tests/unit/test_task_service_crud.py` (in-memory repo + FakeClock), **create/read**: add → stored with id 1 then 2; invalid add → raises and `save_count` unchanged; `get` existing returns task with computed `overdue`; `get` unknown → `TaskNotFoundError`; `list` empty store → `[]`; `list` no filters → all. | T040 | AC-1.1, 1.2, 1.9, 2.1–2.4 | Red. |
| T042 | IMPL | `services/task_service.py`: `TaskService(repo, clock)` with `add_task`, `get_task`, `list_tasks(filters, sort)`; returns a `TaskView` (task + `overdue`) built via `domain`. | T041 | as T041 | Green. |
| T043 | TEST | Service **update/delete**: partial update persists and bumps `updated_at`; invalid update → no save, stored task unchanged; empty update rejected; unknown id → `TaskNotFoundError`; delete removes; delete unknown → not found; after deleting highest id next add gets id+1; delete of invalid id causes no save. | T042 | AC-3.1–3.7, AC-4.1–4.3, AC-9.9 | Red. |
| T044 | IMPL | `TaskService.update_task`, `delete_task`. | T043 | as T043 | Green. |
| T045 | TEST | Service **status & next**: `change_status` success persists; invalid transition → `InvalidTransitionError`, no save; unknown id → not found; `next_task()` returns view or `None` (empty / all completed). | T044 | AC-6.1–6.2, AC-6.6, AC-8.3, AC-9.9 | Red. |
| T046 | IMPL | `TaskService.change_status`, `next_task`. | T045 | as T045 | Green. |
| T047 | TEST+IMPL | `app/config.py` (`Settings` from env: `TODO_DATA_FILE` default `./todo_data.json`, `TODO_API_KEY` optional, host default `127.0.0.1`, port) and `app/container.py::build_service(settings, clock=None)`; tests for env parsing/defaults and an end-to-end "add via service A, read via service B on same temp file". | T046 | AC-9.1, AC-11.8 (default host), D7 | Tests green; interfaces can obtain a service from the container only. |

---

## Phase 6 — CLI (`todo`)

| ID | Type | Task | Depends | Traces | Done when |
|---|---|---|---|---|---|
| T048 | TEST | `tests/contract/test_cli.py` (Typer `CliRunner`, temp data file, FakeClock): `--help` for every command exits 0 non-empty; `add "X" --json` → one JSON object, exit 0; `list --json` → array (`[]` when empty); human `list` prints id, status, priority, title, tags, due date, overdue marker one per line; `show` existing; CLI offers no flags for id/status/timestamps on `add`. | T047 | AC-10.1–10.3, AC-10.6, AC-1.10, AC-2.1–2.4 | Red. |
| T049 | IMPL | `interfaces/cli/main.py` (`add`, `list`, `show`; options per spec FR-10; global `--data-file`, `--json`) and `render.py`. No business logic. | T048 | as T048 | Green. |
| T050 | TEST | CLI **mutations & errors**: `update` fields, `--clear-tags`, `--clear-due`; `delete` without `--yes` → exit 2 and nothing deleted, with `--yes` deletes; `start/complete/reopen` == explicit transitions; `next` prints task, and empty → exit 0 with message; exit codes: validation→2, not found→3, invalid transition→4, storage→5; stdout empty and message on stderr for every error; `show abc` → 2; corrupt-file warning goes to stderr. | T049 | AC-3.3, 4.4, 6.7, 8.3, 9.6 (CLI), 10.4, 10.5 | Red. |
| T051 | IMPL | Remaining commands + `interfaces/cli/errors.py` (single error→exit-code mapper) + `--yes` guard. | T050 | as T050 | Green; `todo --help` lists all commands. |

---

## Phase 7 — HTTP API

| ID | Type | Task | Depends | Traces | Done when |
|---|---|---|---|---|---|
| T052 | TEST | `tests/contract/test_api.py` (FastAPI `TestClient`) **happy paths & validation**: `POST /tasks` 201 + `Location`; `GET /tasks` 200 array incl. repeated `tag` params and filter/sort query params; `GET /tasks/{id}` 200; `PATCH` 200; `DELETE` 204; `POST /tasks/{id}/status` 200; `GET /health` 200; `GET /tasks/abc` → 422; malformed JSON body → 422 (not 500); body containing `id/status/created_at/...` on create → 422. | T051 | AC-11.1, 11.4, 11.5, 11.6, AC-1.10 | Red. |
| T053 | IMPL | `interfaces/api/app.py` (`create_app(container)`), `routes.py`, `schemas.py` (Pydantic `extra="forbid"`; shape only — domain remains source of truth). | T052 | as T052 | Green. |
| T054 | TEST | API **errors & routing**: not found → 404, invalid transition → 409, validation → 422, storage → 500 with generic message; every error body is `{"error":{"code","message"}}`; no stack trace / file path / exception class name in any body; unknown status value → 422 (not 409); `GET /tasks/next` returns task / 204 and is **not** parsed as an id; 405 on wrong method. | T053 | AC-11.2, 11.3, AC-6.5, 6.2, 8.3 | Red. |
| T055 | IMPL | `interfaces/api/errors.py` (exception handlers → status + body) and route order (`/tasks/next` before `/tasks/{id}`). | T054 | as T054 | Green. |
| T056 | TEST | API-key matrix: key unset → all endpoints open; key set → missing/wrong `X-API-Key` → 401 + `unauthorized` body **and no data change**, correct key → 200; `/health` always open; default bind host is `127.0.0.1` (settings + uvicorn launch helper). | T055 | AC-11.7, 11.8 | Red. |
| T057 | IMPL | `interfaces/api/security.py` (dependency, `secrets.compare_digest`) and a `serve()` helper using `Settings.host`. | T056 | as T056 | Green. |

---

## Phase 8 — Cross-Cutting Verification

| ID | Type | Task | Depends | Traces | Done when |
|---|---|---|---|---|---|
| T058 | TEST | `tests/contract/test_parity.py`: one shared scenario table (create, filter by tag, sort, valid transition, invalid transition, delete, not found) executed through **both** CLI and API on identical seed data; assert equivalent task data and equivalent error classes (exit 2/3/4 ↔ 422/404/409). | T057 | AC-12.1 | Green; adding a scenario row adds a test in both interfaces. |
| T059 | TEST `[P]` | Complete `tests/architecture/`: forbid framework imports in `domain`; forbid business logic helpers (`filter_tasks`, `sort_tasks`, `transition`) being *defined* in `interfaces/`; confirm both interfaces import `TaskService` only via container. | T057 | AC-12.2, NFR-2 | Green on real code. |
| T060 | TEST `[P]` | `tests/security/`: SQL/shell/HTML/path-traversal strings (e.g. `"'; DROP TABLE--"`, `"$(rm -rf /)"`, `"<script>"`, `"../../x"`) in title/tag/query stored and returned inertly via CLI and API; oversize bodies (≥1 MB) rejected without 500; error-leak checks; `eval/exec/pickle/shell=True/yaml.load` absent (grep test); data file never contains secrets. | T057 | NFR-3, spec §6.10, Art. VI | Green. |
| T061 | TEST `[P]` | `tests/performance/test_scale.py`: seed 10,000 tasks; list+filter+sort ≤ 1 s; single add ≤ 500 ms (marker `performance`, threshold overridable by env for slow CI). | T057 | NFR-1 | Green on dev machine. |
| T062 | TEST `[P]` | Unicode round-trip through CLI **and** API **and** file (`"café ✅"`, `"日本語"`, emoji tag rejected per tag regex, Unicode title accepted). | T057 | NFR-5 | Green. |
| T063 | TEST `[P]` | Edge-case sweep from spec §6 not yet covered: ids `0`, negative, huge, deleted, never-existed (CLI + API); empty store for every command; empty (0-byte) data file through CLI. | T057 | Spec §6.1, 6.5, 6.7 | Green. |

---

## Phase 9 — Self-Healing Harness (full)

| ID | Type | Task | Depends | Traces | Done when |
|---|---|---|---|---|---|
| T064 | HARNESS | Add gates 5–8 to `gates.py`: bandit (`-ll`), pip-audit, detect-secrets; unit; integration/contract/security; coverage (`--cov-branch`, total ≥90, `domain`+`services` ≥95 via a floor check script). | T063 | Art. VII, NFR-3, NFR-4, Art. IV.2 | `python .harness/run.py` runs all 8 gates green on the codebase. |
| T065 | TEST | `tests/harness/test_healer.py` (runs harness against throw-away temp projects): formatting violation → auto-fixed and re-run green; unfixable type error → escalated as a failure packet, not "fixed"; loop stops after **3** attempts; each attempt appended to `harness-log.md`. | T064 | NFR-7, Art. VII.1–5 | Red. |
| T066 | HARNESS | `.harness/healer.py`: parse tool output → `{gate,file,line,rule,msg}`; auto-fix only `ruff format` and `ruff check --fix` (safe); emit failure packet (JSON + markdown) for others; bounded retry; re-run failed + all earlier gates. | T065 | as T065 | T065 green. |
| T067 | TEST | `tests/harness/test_guards.py`: loosening ruff rules / mypy strictness / coverage threshold, adding `skip`/`xfail`, reducing collected test count, or increasing `noqa`/`type: ignore`/`nosec` count each makes the harness **fail**; changes outside `src/ tests/ .harness/` by an auto-fix fail. | T066 | Art. VII anti-cheat, NFR-7 | Red. |
| T068 | HARNESS | `.harness/guards.py` + `baseline.json` (config hashes, test count, suppression counts, coverage floors) + `run.py --rebaseline` (explicit only; healer cannot call it). Add `report.py --trace`: parses spec ACs and test names, fails if any `AC-x.y` has no test referencing it. | T067 | Art. VIII.1, spec §7 | T067 green; `--trace` reports 100% of ACs covered. |

---

## Phase 10 — Finish

| ID | Type | Task | Depends | Traces | Done when |
|---|---|---|---|---|---|
| T069 | DOC | `README.md`: install, CLI usage with examples for every command and exit code, API run command + endpoint table, env vars, data-file format, corrupt-file behaviour, harness usage, known limitation (single process). Verify `/docs` and every `--help` text are accurate. | T068 | Art. VIII.5 | Every README command executed once successfully (manual check list in PR). |
| T070 | TEST | Run `mutmut` on `domain/` and `services/`; triage surviving mutants (add tests or document equivalents in `.speckit/mutation-notes.md`). | T068 | Art. IV.7 (SHOULD) | Report saved; no unexplained survivors in `rules.py`/`query.py`. |
| T071 | SETUP | Final verification: `python .harness/run.py` green on Windows; CI green on Windows + Linux; walk the Definition of Done checklist (Art. IX); tag `v1.0.0`. | T069, T070 | Art. IX, NFR-6, NFR-7 | All DoD boxes ticked; no gate weakened (guards confirm). |

---

## Acceptance-Criteria Coverage Matrix

Every spec AC is proven by at least one task (test task shown first; IMPL tasks make them pass).

| AC | Task(s) | AC | Task(s) |
|---|---|---|---|
| 1.1 | T020, T041 | 7.1–7.3 | T030 |
| 1.2 | T014, T041 | 7.4 | T028+T030 (composition in T041/T042) |
| 1.3, 1.4 | T014 | 7.5 | T030 |
| 1.5, 1.6 | T016 | 7.6 | T030, T034 |
| 1.7, 1.8 | T018 | 8.1, 8.2, 8.4 | T032 |
| 1.9 | T020, T041 | 8.3 | T032, T045, T050, T054 |
| 1.10 | T020, T048, T052 | 9.1 | T039, T047 |
| 2.1–2.4 | T041, T048 | 9.2 | T037, T039 |
| 3.1, 3.2, 3.4, 3.5, 3.7 | T026, T043 | 9.3 | T037 |
| 3.3 | T026, T050 | 9.4 | T035, T037 |
| 3.6 | T043 | 9.5 | T039 |
| 4.1, 4.2, 4.3 | T043, T039 | 9.6 | T039, T050 |
| 4.4 | T050 | 9.7 | T035, T039 |
| 5.1–5.7, 5.9 | T028 | 9.8 | T037 |
| 5.8 | T024, T028 | 9.9 | T041, T043, T045 |
| 6.1–6.5 | T022 | 10.1–10.3, 10.6 | T048 |
| 6.6 | T045, T054 | 10.4, 10.5 | T050 |
| 6.7 | T050 | 11.1, 11.4–11.6 | T052 |
| 11.2, 11.3 | T054 | 11.7, 11.8 | T056 |
| 12.1 | T058 | 12.2 | T008, T059 |

| NFR | Task(s) |
|---|---|
| NFR-1 Performance | T061 |
| NFR-2 Determinism | T008, T013, T059 |
| NFR-3 Security | T005, T060, T064 |
| NFR-4 Quality gates | T002, T006, T064, T071 |
| NFR-5 Unicode | T014, T035, T062 |
| NFR-6 Portability | T007, T071 |
| NFR-7 Self-healing | T039, T065–T068 |

---

## Parallelisation & Milestones

- **Parallel groups:** T004/T005/T007 · T012 with T010 prep · T034 · T059–T063 · none otherwise (strict TDD pairs are sequential).
- **Milestone M1 (T001–T013):** governed, tooled skeleton; harness gates 1–4 green.
- **Milestone M2 (T014–T034):** all business rules proven in the pure domain (FR-1, 3, 5, 6, 7, 8 logic).
- **Milestone M3 (T035–T047):** persistence + service; FR-9 complete; CRUD usable programmatically.
- **Milestone M4 (T048–T057):** both interfaces complete (FR-10, FR-11).
- **Milestone M5 (T058–T068):** parity, security, performance, full self-healing harness.
- **Milestone M6 (T069–T071):** documented, mutation-checked, released.

**Rule for the implementer (and the harness):** if a task cannot be completed without loosening a test, threshold or lint rule, **stop and amend the spec/constitution** — never edit the gate to get green (Art. VII).
