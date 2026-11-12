# Technical Plan — Smart Todo & Task CLI/API

**Version:** 1.0.0 · **Date:** 2026-11-12 · **Status:** Draft for review
**Inputs:** `.speckit/constitution.md` v1.0.0, `.speckit/spec.md` v1.0.0

---

## 1. Stack Decision

### 1.1 Recommendation: **Python 3.11+ (pytest + ruff + mypy)**

| Criterion | Python | Node.js/TypeScript | Winner |
|---|---|---|---|
| One language for CLI + API + tests | ✓ | ✓ | tie |
| Declarative validation matching spec §3.1 (enums, length, regex, extra-field rejection) | Pydantic v2 — native | zod — good | Python (slight) |
| API with auto OpenAPI (FR-11) | FastAPI, zero extra code | Fastify/Nest + plugins | Python |
| CLI with generated `--help`, exit codes (FR-10) | Typer (type-hint driven) | commander/yargs | Python |
| Lint + format in one fast tool | **ruff** (one dependency) | ESLint + Prettier + plugins | Python |
| Strict typing gate (Art. III.3) | mypy `--strict` | `tsc --strict` | tie |
| Security scanners (Art. VI) | bandit, pip-audit, detect-secrets | npm audit, eslint-plugin-security | tie |
| Property/mutation testing | hypothesis, mutmut | fast-check, Stryker | tie |
| Toolchain footprint | `pyproject.toml` only | `package.json` + tsconfig + eslint + jest config | Python |

**Decision:** Python is the cleanest fit: fewer tools, spec rules map 1:1 to Pydantic models, and OpenAPI/`--help` are generated rather than hand-written, so they cannot drift from behaviour.

### 1.2 Pinned toolchain

| Concern | Tool | Notes |
|---|---|---|
| Runtime | Python ≥ 3.11 | `tomllib`, better typing |
| Packaging | `pyproject.toml` (PEP 621), `uv` or `pip` + lock file | Pinned versions (Art. VI.6) |
| Domain models | `dataclasses` (frozen) in `domain/`; Pydantic only at interface boundary | Keeps domain framework-free (Art. II.1) |
| CLI | Typer | `CliRunner` for tests |
| API | FastAPI + Uvicorn | `TestClient` for tests |
| Persistence | stdlib `json`, `os.replace`, `tempfile` | **No ORM** (see §1.3) |
| Tests | pytest, pytest-cov, hypothesis, mutmut | |
| Lint/format/types | ruff, mypy | |
| Security | bandit, pip-audit, detect-secrets | |
| Hooks | pre-commit | |
| Task runner | `Makefile` + cross-platform `python .harness/run.py` | Windows is the primary dev OS, so Make is a thin wrapper only |

### 1.3 Constitution deviation (requires amendment before `/speckit.tasks`)
Constitution Art. I lists *SQLite via SQLAlchemy*. The spec (FR-9) mandates **JSON-file persistence**, so SQLAlchemy is dropped. Required amendment (MINOR, v1.1.0):
- Art. I Persistence → "JSON file via stdlib, behind a repository interface".
- Art. VII → harness lives in `.harness/` (invoked `python .harness/run.py`, since a dot-directory is not an importable package); log stays at `.speckit/harness-log.md`.
- Art. VII runtime-resilience bullet "migrations / DB locks" → "schema `version` check, corrupt-file recovery".

---

## 2. Architecture

### 2.1 Layers (one-way dependencies, Constitution Art. II)

```
 ┌───────────────────────────────┐   ┌────────────────────────────────┐
 │ interfaces/cli (Typer)        │   │ interfaces/api (FastAPI)       │
 │ parse → call service → format │   │ parse → call service → format  │
 └───────────────┬───────────────┘   └───────────────┬────────────────┘
                 └───────────────┬───────────────────┘
                                 ▼
                 ┌──────────────────────────────┐
                 │ services/  TaskService       │  use-cases, orchestration
                 │ (+ NextTaskSelector)         │
                 └───────┬───────────────┬──────┘
                         ▼               ▼
        ┌──────────────────────┐   ┌──────────────────────────────┐
        │ domain/              │   │ repositories/ (interface)    │
        │ Task, enums, rules,  │◄──│ TaskRepository (Protocol)    │
        │ errors, filter, sort │   └──────────────┬───────────────┘
        └──────────────────────┘                  ▼
                                   ┌──────────────────────────────┐
                                   │ infrastructure/              │
                                   │ JsonFileTaskRepository       │
                                   │ SystemClock                  │
                                   └──────────────────────────────┘
```
Arrows = "may import". `domain` imports nothing from the project's other layers. `infrastructure` implements interfaces defined in `repositories/` and `services/ports.py`.

### 2.2 Key design decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Domain logic is pure functions** over immutable `Task` (validation, transitions, overdue, filter, sort, next-task ranking). | Most testable; satisfies FR-5/6/7/8 with no I/O; 95% coverage gate is easy. |
| D2 | **Service owns the unit of work:** `load → apply pure function → save`. Repository exposes coarse `load_all()` / `save_all()`, not per-row ops. | JSON file is a whole-document store; coarse API makes atomic writes natural (AC-9.3, AC-9.9). |
| D3 | **Failed mutations never reach `save`:** validation/transition checks run before persistence. | AC-3.4, AC-9.9. |
| D4 | **Ports for nondeterminism:** `Clock` protocol (`now() -> datetime`), injected into the service. | NFR-2; deterministic overdue/`updated_at` tests. |
| D5 | **Single error hierarchy** in `domain/errors.py`; one mapper per interface (`cli/errors.py` → exit codes, `api/errors.py` → HTTP status + body). | Constitution III.5; AC-10.4, AC-11.2. |
| D6 | **Pydantic only at the edge:** request/response schemas in `interfaces/api/schemas.py`; CLI parses via the same validating factory `domain.task.validate_new_task(...)`. | Spec rules live **once** in domain (single source of truth, FR-12.2); API schemas only reject unknown fields and shape types. |
| D7 | **Composition root** `app/container.py` builds repository + clock + service from config. CLI and API both call it. | No globals; parity (FR-12). |
| D8 | **`/tasks/next` declared before `/tasks/{id}`** and `{id}` typed `int`. | AC-11.3, AC-11.4. |
| D9 | **Optional API key** as a FastAPI dependency reading `TODO_API_KEY`; compared with `secrets.compare_digest`. | AC-11.7; avoids timing leak. |
| D10 | **Overdue is computed in the domain** (`is_overdue(task, today)`), never stored. | Spec §3.2, AC-9.4. |

### 2.3 Domain API (sketch)

```python
# domain/task.py
class Status(StrEnum): PENDING; IN_PROGRESS; COMPLETED
class Priority(IntEnum): LOW=1; MEDIUM=2; HIGH=3        # rank == sort key

@dataclass(frozen=True, slots=True)
class Task: id, title, description, status, priority, tags: tuple[str, ...],
            due_date: date | None, created_at, updated_at, completed_at

# domain/rules.py  (pure)
normalize_title / normalize_tags / validate_due_date
transition(task, new_status, now) -> Task       # raises InvalidTransitionError
is_overdue(task, today) -> bool
apply_update(task, changes, now) -> Task

# domain/query.py (pure)
filter_tasks(tasks, *, status, priority, tags, match, overdue, today) -> list[Task]
sort_tasks(tasks, *, key, order) -> list[Task]  # id-asc tiebreak, None due last
# domain/smart/next_task.py
select_next(tasks, today) -> Task | None
```

---

## 3. File Structure

```
Part-1A/
├── .speckit/
│   ├── constitution.md
│   ├── spec.md
│   ├── plan.md                    ← this file
│   └── harness-log.md             ← appended by harness (Art. VII.5)
├── .harness/                      ← self-healing harness (Art. VII)
│   ├── run.py                     ← entry point: python .harness/run.py [--gate X] [--no-heal]
│   ├── gates.py                   ← gate definitions (name, command, auto-fixable?)
│   ├── healer.py                  ← classify failures, apply safe auto-fixes, bounded retry
│   ├── guards.py                  ← anti-cheat: detect weakened config / skipped tests
│   ├── report.py                  ← structured result + harness-log writer
│   └── baseline.json              ← locked thresholds & config hashes (coverage floor, ruff rules)
├── src/
│   └── todo/
│       ├── __init__.py
│       ├── domain/
│       │   ├── task.py            ← Task, Status, Priority
│       │   ├── rules.py           ← normalisation, validation, transitions, overdue
│       │   ├── query.py           ← filter + sort
│       │   ├── errors.py          ← TodoError hierarchy
│       │   └── smart/next_task.py ← FR-8, isolated (Art. II.6)
│       ├── services/
│       │   ├── task_service.py    ← use-cases (add/get/list/update/delete/change_status/next)
│       │   └── ports.py           ← Clock protocol
│       ├── repositories/
│       │   └── base.py            ← TaskRepository Protocol (load_all/save_all)
│       ├── infrastructure/
│       │   ├── json_repository.py ← FR-9 implementation
│       │   ├── file_io.py         ← atomic write, corrupt-file quarantine
│       │   ├── serialization.py   ← Task ⇄ dict, schema version check
│       │   └── clock.py           ← SystemClock
│       ├── interfaces/
│       │   ├── cli/
│       │   │   ├── main.py        ← Typer app + commands
│       │   │   ├── render.py      ← human + --json output
│       │   │   └── errors.py      ← error → exit code
│       │   └── api/
│       │       ├── app.py         ← FastAPI factory create_app(container)
│       │       ├── routes.py
│       │       ├── schemas.py     ← Pydantic (extra="forbid")
│       │       ├── security.py    ← API-key dependency
│       │       └── errors.py      ← error → status + {"error":{...}}
│       └── app/
│           ├── config.py          ← env → Settings (TODO_DATA_FILE, TODO_API_KEY, host/port)
│           └── container.py       ← composition root
├── tests/
│   ├── conftest.py                ← FakeClock, InMemoryTaskRepository, tmp data file fixtures
│   ├── unit/                      ← test_task_validation, test_transitions, test_filtering,
│   │                                test_sorting, test_next_task, test_task_service_crud
│   ├── integration/               ← test_json_repository, test_file_io_atomic
│   ├── contract/                  ← test_cli, test_api, test_parity
│   ├── security/                  ← injection, oversize, authz/API-key, error-leak
│   ├── architecture/              ← import-layer rules, "no datetime.now in domain/services"
│   └── performance/               ← NFR-1 (10k tasks)
├── pyproject.toml                 ← deps, ruff, mypy, pytest, coverage config, scripts: `todo`
├── Makefile                       ← thin: check / test / verify → python .harness/run.py
├── .pre-commit-config.yaml
├── .env.example
├── .gitignore                     ← .env, todo_data.json, .venv, caches, *.corrupt-*
└── README.md
```

Entry points (in `pyproject.toml`): `todo = "todo.interfaces.cli.main:app"`; API run via `uvicorn todo.interfaces.api.app:create_app --factory --host 127.0.0.1`.

---

## 4. JSON Persistence — Data Flow

### 4.1 Read path (every service call)
```
service.list_tasks(...)
  └─► repo.load_all()
        ├─ file missing ───────────────► return Store(next_id=1, tasks=[])      (AC-9.2)
        ├─ read bytes (UTF-8) ─► json.loads
        │     ├─ JSONDecodeError / 0 bytes ─► quarantine file → *.corrupt-<UTCts>
        │     │                              warn; return empty Store            (AC-9.6)
        │     └─ ok ─► serialization.from_dict(doc)
        │           ├─ version > supported ─► raise StorageError (file untouched) (AC-9.7)
        │           ├─ schema/field invalid ─► quarantine + warn + empty Store    (AC-9.7)
        │           └─ ok ─► Store(next_id, tasks)
  ◄─ pure domain functions (filter → sort) ─► result
```

### 4.2 Write path (create / update / delete / transition)
```
service.add_task(input)
  1. store = repo.load_all()
  2. task  = domain.build_task(input, id=store.next_id, now=clock.now())   ← validation here
       └─ error ⇒ raise (NO write; AC-1.2, AC-9.9)
  3. new_store = Store(next_id=store.next_id+1, tasks=[*store.tasks, task])
  4. repo.save_all(new_store)
        a. doc  = serialization.to_dict(new_store)   (no `overdue`; AC-9.4)
        b. text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        c. fd,tmp = tempfile.mkstemp(dir=<same dir as target>)     (same FS ⇒ atomic rename)
        d. write text; flush; os.fsync(fd); close
        e. os.replace(tmp, target)                                  (atomic on Windows & POSIX)
        f. on ANY exception: delete tmp, re-raise as StorageError;
           target is byte-identical to before                       (AC-9.3, AC-9.8)
  5. return task
```
- `next_id` lives in the file and is incremented on create only, so deletions never cause reuse (AC-4.3, AC-9.5).
- Parent directory is created on first write (AC-9.2).
- Temp file lives next to the target and is removed on failure — no partial files (AC-9.8).

### 4.3 Concurrency stance (v1, per spec assumption)
Single process at a time. Atomic replace guarantees the file is never half-written, but two concurrent writers could lose an update (last write wins). Documented limitation; revisit with a lock file if scope grows. The coarse load→mutate→save pattern is the only place that would need a lock, so it can be added without changing interfaces.

### 4.4 Sample serialization contract
`serialization.py` is the sole place that knows the on-disk shape (`version: 1`). Dates → ISO strings; datetimes → UTC `...Z`; tags → list; enums → their string values. `from_dict` validates strictly and raises `StorageFormatError` (→ quarantine path) on any deviation.

---

## 5. Request Flow Examples

**`todo add "Pay rent" --tag home --due 2026-11-15`**
`cli.main.add` → `container.build()` → `TaskService.add_task` → domain validation → `repo.save_all` (atomic) → `render.task(...)` → stdout, exit 0.

**`POST /tasks/7/status {"status":"completed"}`**
`api.routes` (auth dep → schema validate) → `TaskService.change_status(7, COMPLETED)` → `load_all` → `domain.transition` → (`InvalidTransitionError` ⇒ 409 mapper) → `save_all` → 200 + task JSON.

Both interfaces share steps from `TaskService` onward (FR-12.2).

---

## 6. Self-Healing Harness (`.harness/`)

### 6.1 Gate pipeline (Constitution Art. VII)
| # | Gate | Command | Auto-fix? |
|---|---|---|---|
| 1 | Syntax | `python -m compileall -q src tests .harness` | no |
| 2 | Format | `ruff format --check` | **yes** → `ruff format` |
| 3 | Lint | `ruff check` | **partly** → `ruff check --fix` (safe fixes only) |
| 4 | Types | `mypy --strict src` | no (agent/dev repair) |
| 5 | Security | `bandit -r src -ll`; `pip-audit`; `detect-secrets-hook` | no |
| 6 | Unit tests | `pytest tests/unit tests/architecture` | no |
| 7 | Integration/contract/security tests | `pytest tests/integration tests/contract tests/security` | no |
| 8 | Coverage | `pytest --cov --cov-branch --cov-fail-under=90` + per-package floors | no |

### 6.2 Healing loop (per gate, max 3 attempts)
```
run gate ─► pass ─► next gate
   │fail
   ▼
classify (parse tool output → [{file,line,rule,msg}])
   ├─ auto-fixable ─► apply fixer ─► guards.check() ─► re-run this gate AND all prior gates
   └─ needs reasoning ─► emit failure packet (JSON + markdown) for the implementing agent/dev
                         ─► wait for patch ─► guards.check() ─► re-run
attempts > 3 ─► STOP, exit non-zero, write escalation report
every step ─► append to .speckit/harness-log.md
```

### 6.3 Anti-cheating guards (`guards.py`)
Run after every repair; any hit fails the run:
1. Config hash check: `pyproject.toml` `[tool.ruff]`, `[tool.mypy]`, coverage threshold vs `baseline.json` — loosening is rejected.
2. Test inventory: number of collected tests must not decrease vs baseline without a spec change; reject new `skip`, `xfail`, `pytest.mark.skip`.
3. Suppression budget: count of `# noqa`, `# type: ignore`, `# nosec` must not increase.
4. Scope check: files changed by an auto-fix must be inside `src/`, `tests/`, `.harness/`.

`baseline.json` is updated only by an explicit, reviewed command (`run.py --rebaseline`), never by the healer.

### 6.4 Runtime self-healing (product)
Corrupt/invalid JSON → quarantine + empty store + warning (AC-9.6/9.7). Interrupted writes cannot corrupt data (atomic replace). Stale temp files from a crash are ignored (and cleaned on next successful write).

---

## 7. Testing Strategy

| Layer | Approach | Key doubles |
|---|---|---|
| Domain (`rules`, `query`, `smart`) | Pure unit + `hypothesis` property tests (e.g. sort is stable & a permutation; tag normalisation idempotent) | `FakeClock` |
| Service | Unit with `InMemoryTaskRepository`; assert repo is **not** saved on failure (AC-9.9) | in-memory repo, FakeClock |
| JSON repo | Integration on `tmp_path`: roundtrip, missing/empty/corrupt/newer-version, read-only dir, simulated failure between write and replace (monkeypatch `os.replace`) | none |
| CLI | `CliRunner` against container wired to temp file + FakeClock; assert exit codes & stdout/stderr split | temp data file |
| API | `TestClient` against `create_app(container)`; assert status, error shape, no leakage, API-key matrix | temp data file |
| Parity | Parametrised scenario table executed through both interfaces; compare normalised results | — |
| Architecture | AST/import scan: `domain` imports no other layer or framework; interfaces don't import `infrastructure` except via container; no `datetime.now`/`date.today` in `domain/`/`services/` | — |
| Performance | 10k-task fixture, timed assertions (NFR-1) with generous CI margin flag | — |

Every `AC-*` in the spec maps to at least one test whose docstring or `id` cites it (e.g. `test_ac_5_2_tag_filter_all_match`), enabling a script-checkable traceability report (`.harness/report.py --trace`).

---

## 8. Constitution Compliance Check

| Article | Status | How satisfied |
|---|---|---|
| I Stack | ⚠ amend | Persistence row changes to JSON (§1.3) |
| II Modularity | ✓ | §2.1 layers, D1–D7, architecture tests |
| III Clean code | ✓ | frozen dataclasses, error hierarchy, DI clock, mypy strict, small modules |
| IV Testing | ✓ | §7; test-first ordering enforced in task list |
| V Lint guard | ✓ | ruff/mypy gates 2–4; pre-commit |
| VI Security | ✓ | Pydantic `extra="forbid"`, API key, no `eval/shell`, bandit/pip-audit/detect-secrets, localhost bind, error mapper hides internals |
| VII Harness | ✓ / ⚠ | §6; location `.harness/` requires wording amendment (§1.3) |
| VIII Workflow | ✓ | traceability via AC ids |

---

## 9. Implementation Phasing (input to `/speckit.tasks`)

| Phase | Deliverable | Spec coverage |
|---|---|---|
| 0 | Scaffolding: `pyproject.toml`, tooling config, pre-commit, harness skeleton (gates 1–4 working), architecture tests | NFR-4 |
| 1 | Domain: `Task`, enums, errors, validation, transitions, overdue (tests first) | FR-1, FR-6, §3 |
| 2 | Domain: filter, sort, next-task (tests first) | FR-5, FR-7, FR-8 |
| 3 | Persistence: serialization, atomic file IO, `JsonFileTaskRepository`, quarantine | FR-9 |
| 4 | `TaskService` + container + config | FR-1–FR-8 wiring |
| 5 | CLI + contract tests | FR-10 |
| 6 | API + auth + contract/security tests | FR-11 |
| 7 | Parity tests, performance tests, full harness (gates 5–8, guards, healing loop) | FR-12, NFR-1/3/7 |
| 8 | README, final `make verify`, traceability report | Art. IX |

Each phase ends with `python .harness/run.py` green.

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Whole-file rewrite is O(n) per mutation | Slow at very large n | NFR-1 sets 10k as the ceiling; coarse repo interface lets us swap the backend without touching services |
| Concurrent writers lose updates | Data loss (rare, single-user) | Documented; lock-file extension point in `file_io.py` |
| `os.replace` fails on Windows if target open/locked by AV/indexer | Transient `StorageError` | Bounded retry (3× short backoff) inside `file_io.py`, covered by a test with a patched `os.replace` |
| Validation duplicated between Pydantic and domain | Behaviour drift | D6: domain is the single source of truth; Pydantic only checks shape/unknown fields; parity tests |
| Healer "fixes" by weakening gates | False green | §6.3 guards + baseline lock |
| Dot-directory `.harness/` not importable | Awkward imports | Run as script; modules use relative file imports, no package semantics needed |
