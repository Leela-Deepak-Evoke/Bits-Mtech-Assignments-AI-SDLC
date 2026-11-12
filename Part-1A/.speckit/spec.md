# Specification — Option A: Smart Todo & Task CLI/API

**Version:** 1.0.0 · **Date:** 2026-11-12 · **Status:** Draft for review
**Governed by:** `.speckit/constitution.md` v1.0.0

---

## 1. Purpose & Scope

A single-user task manager exposed through two interfaces — a **CLI** (`todo`) and an **HTTP API** (JSON over REST) — that share one service layer and one JSON-file data store.

**In scope:** task CRUD, tag filtering, status filtering, priority sorting, status transitions, JSON file persistence, overdue detection, a "next task" suggestion.
**Out of scope (v1):** multi-user accounts, sub-tasks, recurring tasks, reminders/notifications, multi-process file locking, a web UI, import/export formats other than the native JSON file.

Each requirement has an ID (`FR-`, `NFR-`) and each is verified by one or more **binary** acceptance criteria (`AC-`) that pass or fail with no judgement.

---

## 2. Glossary

| Term | Meaning |
|---|---|
| Task | The unit of work managed by the system. |
| Status | One of `pending`, `in_progress`, `completed`. |
| Priority | One of `low`, `medium`, `high`. Rank: high=3, medium=2, low=1. |
| Tag | A short lowercase label attached to a task. |
| Overdue | `due_date` is set, strictly before today (UTC), and status ≠ `completed`. |
| Today | The date from the injected clock, in UTC. |

---

## 3. Data Model

### 3.1 Task

| Field | Type | Rules |
|---|---|---|
| `id` | integer | Assigned by system, ≥ 1, unique, **never reused** after deletion. Immutable. |
| `title` | string | **Required.** Trimmed of leading/trailing whitespace; length 1–200 after trimming. |
| `description` | string | Optional, default `""`, 0–2000 chars. |
| `status` | enum | `pending` \| `in_progress` \| `completed`. Default `pending`. |
| `priority` | enum | `low` \| `medium` \| `high`. Default `medium`. |
| `tags` | list[string] | Default `[]`. Max 10 tags. Each tag: lowercased, trimmed, 1–30 chars, matching `^[a-z0-9][a-z0-9_-]*$`. Duplicates removed; order preserved by first occurrence. |
| `due_date` | date \| null | Optional, ISO `YYYY-MM-DD`. May be in the past. |
| `created_at` | datetime | UTC ISO-8601 with `Z`, set once at creation. |
| `updated_at` | datetime | UTC ISO-8601 with `Z`, set on every successful mutation. |
| `completed_at` | datetime \| null | Set when status becomes `completed`; cleared (null) when it leaves `completed`. |

### 3.2 Computed field
`overdue` (boolean) — derived per §2; included in all task outputs; **never persisted**.

### 3.3 Status transition table

| From \ To | pending | in_progress | completed |
|---|---|---|---|
| **pending** | ✗ | ✓ | ✓ |
| **in_progress** | ✓ | ✗ | ✓ |
| **completed** | ✓ (reopen) | ✗ | ✗ |

`✗` = rejected with an *invalid transition* error (including same-state transitions).

---

## 4. Functional Requirements

### FR-1 Create task
Create a task from `title` (required) and optional `description`, `priority`, `tags`, `due_date`. Status always starts `pending`.

- **AC-1.1** Given only `title="Buy milk"`, the created task has `status=pending`, `priority=medium`, `tags=[]`, `description=""`, `due_date=null`, `completed_at=null`, and `created_at == updated_at`.
- **AC-1.2** Given an empty or whitespace-only title, creation fails with a validation error and **no task is stored**.
- **AC-1.3** A title of exactly 200 chars is accepted; 201 chars is rejected.
- **AC-1.4** Title `"  Buy milk  "` is stored as `"Buy milk"`.
- **AC-1.5** Given tags `["Work", "work", " Home "]`, stored tags are `["work","home"]`.
- **AC-1.6** More than 10 distinct tags, a tag over 30 chars, or a tag containing a character outside `[a-z0-9_-]` (e.g. `"a b"`, `"#x"`) is rejected with a validation error.
- **AC-1.7** `priority="urgent"` (any value outside the enum) is rejected.
- **AC-1.8** `due_date="2026-02-30"` or `"12/11/2026"` is rejected; `"2020-01-01"` (past) is accepted.
- **AC-1.9** The first task created in an empty store gets `id=1`; the next gets `id=2`.
- **AC-1.10** A client-supplied `id`, `status`, `created_at`, `updated_at`, or `completed_at` on create is rejected (API: 422) or not exposed (CLI).

### FR-2 Read tasks
- **AC-2.1** Fetching an existing id returns the full task including computed `overdue`.
- **AC-2.2** Fetching a non-existent id fails with *not found*.
- **AC-2.3** Listing on an empty store returns an empty list (success, not an error).
- **AC-2.4** Listing with no filters returns all tasks.

### FR-3 Update task
Partial update of `title`, `description`, `priority`, `tags`, `due_date`. Status is changed only via FR-6. `id`, `created_at` are immutable.

- **AC-3.1** Updating only `priority` leaves all other fields unchanged and sets `updated_at` to the current time.
- **AC-3.2** Updating `tags` **replaces** the whole tag list; `tags=[]` clears them.
- **AC-3.3** `due_date=null` (API) / `--clear-due` (CLI) removes the due date.
- **AC-3.4** An update with an invalid value (e.g. empty title) fails and the stored task is **unchanged** (including `updated_at`).
- **AC-3.5** An update containing no fields is rejected with a validation error.
- **AC-3.6** Updating a non-existent id fails with *not found*.
- **AC-3.7** An update that attempts to set `status`, `id`, or `created_at` is rejected.

### FR-4 Delete task
- **AC-4.1** Deleting an existing id removes it; a subsequent fetch returns *not found*.
- **AC-4.2** Deleting a non-existent id fails with *not found*.
- **AC-4.3** After deleting task 3 (the highest id), the next created task gets `id=4`, not 3.
- **AC-4.4** CLI delete requires `--yes`; without it the command exits with a usage error and deletes nothing.

### FR-5 Filtering (incl. tags)
List filters combine with logical **AND**.

| Filter | Semantics |
|---|---|
| `status` | exact match on one status |
| `priority` | exact match on one priority |
| `tag` (repeatable) | task must contain **all** given tags (`match=all`, default) |
| `match=any` | with multiple `tag`s, task must contain **at least one** |
| `overdue=true` | only overdue tasks; `overdue=false` only non-overdue |

- **AC-5.1** With tasks A(tags work,urgent) B(tags work) C(no tags), `tag=work` returns A and B.
- **AC-5.2** `tag=work&tag=urgent` (all) returns only A.
- **AC-5.3** `tag=urgent&tag=home&match=any` returns A only (has `urgent`).
- **AC-5.4** Tag filtering is case-insensitive on input: `tag=WORK` behaves as `tag=work`.
- **AC-5.5** A tag that no task has returns an empty list (success).
- **AC-5.6** `status=in_progress` returns only in-progress tasks; an invalid status value fails with a validation error.
- **AC-5.7** `status=pending&priority=high&tag=work` returns only tasks satisfying all three.
- **AC-5.8** With today=2026-11-12, a pending task due 2026-11-11 is overdue; due 2026-11-12 is **not** overdue; a completed task due 2026-11-11 is **not** overdue; a task with no due date is **not** overdue. `overdue=true` returns exactly the overdue ones.
- **AC-5.9** An invalid `match` value fails with a validation error.

### FR-6 Status transitions
- **AC-6.1** Every ✓ cell in §3.3 succeeds and updates `status` and `updated_at`.
- **AC-6.2** Every ✗ cell in §3.3 fails with *invalid transition* and leaves the task unchanged.
- **AC-6.3** Moving to `completed` sets `completed_at` to the current time.
- **AC-6.4** Moving `completed → pending` sets `completed_at` to null.
- **AC-6.5** Requesting a status outside the enum fails with a validation error (not *invalid transition*).
- **AC-6.6** Transitioning a non-existent id fails with *not found*.
- **AC-6.7** CLI shortcuts `start` (→ in_progress), `complete` (→ completed), `reopen` (→ pending) behave identically to an explicit transition.

### FR-7 Priority sorting
List supports `sort` ∈ {`priority`, `due_date`, `created_at`, `id`} and `order` ∈ {`asc`, `desc`}.

- **Default** (no `sort`): `priority` descending.
- **Tie-breaking (always):** by `id` ascending, regardless of `order`.
- **Priority** ranks high > medium > low.
- **due_date:** tasks with no due date are placed **last** in both `asc` and `desc`.

- **AC-7.1** Default listing of tasks (id1 low, id2 high, id3 medium, id4 high) returns ids `[2,4,3,1]`.
- **AC-7.2** `sort=priority&order=asc` on the same data returns `[1,3,2,4]`.
- **AC-7.3** `sort=due_date&order=asc` with due dates (id1: 2026-12-01, id2: none, id3: 2026-11-15) returns `[3,1,2]`; with `order=desc` returns `[1,3,2]`.
- **AC-7.4** Sorting applies **after** filtering (filter then sort).
- **AC-7.5** Invalid `sort` or `order` value fails with a validation error.
- **AC-7.6** Sorting is stable/deterministic: repeated identical requests return identical order.

### FR-8 Smart suggestion ("next")
`todo next` / `GET /tasks/next` returns the single most actionable task, chosen from tasks with status ≠ `completed` by this ordered rule: (1) overdue first, (2) higher priority, (3) earlier due date (none last), (4) `in_progress` before `pending`, (5) lower id.

- **AC-8.1** Given overdue-low (id1) and not-overdue-high (id2), result is id1.
- **AC-8.2** Given two overdue tasks, high (id3) and medium (id2), result is id3.
- **AC-8.3** Given only completed tasks or an empty store, the result is *no actionable task* (CLI exit 0 with message; API 204 No Content / `null`) — **not** an error.
- **AC-8.4** Equal on rules 1–3, an `in_progress` task wins over a `pending` one.

### FR-9 JSON file persistence
All tasks persist in one JSON file, path from env `TODO_DATA_FILE` (default `./todo_data.json`; `--data-file` CLI override).

File schema:
```json
{ "version": 1, "next_id": 3, "tasks": [ { "id": 1, "title": "...", "description": "", "status": "pending",
  "priority": "medium", "tags": [], "due_date": null, "created_at": "2026-11-12T09:00:00Z",
  "updated_at": "2026-11-12T09:00:00Z", "completed_at": null } ] }
```

- **AC-9.1** Data created by one process is visible to a new process (CLI invocation, or API restart) pointing at the same file.
- **AC-9.2** If the file does not exist, the app starts with an empty store and **creates the file on first write** (and its parent directory if needed).
- **AC-9.3** Writes are **atomic**: data is written to a temp file in the same directory then renamed over the target; if the write fails mid-way, the original file is byte-for-byte unchanged.
- **AC-9.4** The file is valid UTF-8 JSON, 2-space indented, and `overdue` is **not** present in it.
- **AC-9.5** `next_id` persists across restarts so ids are never reused (see AC-4.3).
- **AC-9.6** If the file contains invalid JSON, the app moves it to `<name>.corrupt-<UTC timestamp>`, starts with an empty store, and reports a warning (CLI: stderr; API: log). The corrupt content is **never silently deleted**.
- **AC-9.7** If the file is valid JSON but fails schema validation (unknown `version`, missing `tasks`, bad field values), it is treated per AC-9.6 for malformed data except an unknown **newer** `version`, which fails with a *storage error* and is left untouched.
- **AC-9.8** A read-only/unwritable location produces a *storage error*; no partial file is left behind.
- **AC-9.9** A failed mutation (validation, not found, invalid transition) does **not** modify the file.

### FR-10 CLI interface
Command name `todo`. Output is human-readable by default; `--json` emits machine-readable JSON to stdout. Errors go to stderr.

| Command | Maps to |
|---|---|
| `todo add TITLE [--desc T] [--priority P] [--tag T]... [--due DATE]` | FR-1 |
| `todo list [--status S] [--priority P] [--tag T]... [--match all\|any] [--overdue/--no-overdue] [--sort K] [--order O]` | FR-2, 5, 7 |
| `todo show ID` | FR-2 |
| `todo update ID [--title] [--desc] [--priority] [--tag T]... [--clear-tags] [--due DATE] [--clear-due]` | FR-3 |
| `todo delete ID --yes` | FR-4 |
| `todo start ID` / `complete ID` / `reopen ID` | FR-6 |
| `todo next` | FR-8 |

**Exit codes:** `0` success · `2` validation/usage error · `3` not found · `4` invalid transition · `5` storage error.

- **AC-10.1** Each documented command exists and `todo <command> --help` exits 0 with non-empty text.
- **AC-10.2** `todo add "X" --json` prints a single JSON object parseable by `json.loads` containing the created task, exit 0.
- **AC-10.3** `todo list --json` prints a JSON array (empty `[]` when none), exit 0.
- **AC-10.4** Each error class in FR-1…FR-9 produces the exit code in the table above and a message on stderr; stdout is empty on error.
- **AC-10.5** `todo show abc` (non-integer id) exits 2.
- **AC-10.6** Human-readable `list` output shows id, status, priority, title, tags, due date, and an overdue marker, one task per line.

### FR-11 HTTP API interface
JSON over REST; `Content-Type: application/json`. OpenAPI available at `/docs` and `/openapi.json`.

| Method & Path | Success | Maps to |
|---|---|---|
| `POST /tasks` | 201 + task, `Location` header | FR-1 |
| `GET /tasks` (query: `status, priority, tag, match, overdue, sort, order`) | 200 + array | FR-2, 5, 7 |
| `GET /tasks/{id}` | 200 + task | FR-2 |
| `PATCH /tasks/{id}` | 200 + task | FR-3 |
| `DELETE /tasks/{id}` | 204 | FR-4 |
| `POST /tasks/{id}/status` body `{"status": "..."}` | 200 + task | FR-6 |
| `GET /tasks/next` | 200 + task, or 204 | FR-8 |
| `GET /health` | 200 `{"status":"ok"}` | — |

**Error mapping:** validation → **422**; not found → **404**; invalid transition → **409**; storage error → **500** (generic message, no internals); wrong method → 405; unauthorised → **401**.
**Error body (all errors):** `{"error": {"code": "<machine_code>", "message": "<text>"}}` with codes `validation_error`, `not_found`, `invalid_transition`, `storage_error`, `unauthorized`.

- **AC-11.1** Each row in the table returns the stated success status for a valid request.
- **AC-11.2** Each error class returns the status and error-body shape above; no stack trace, file path, or exception class name appears in any error body.
- **AC-11.3** `GET /tasks/next` is routed to the "next" handler, not interpreted as `id="next"` (no 422 caused by non-integer id).
- **AC-11.4** `GET /tasks/abc` returns 422.
- **AC-11.5** `GET /tasks?tag=a&tag=b&match=any` supports repeated `tag` parameters.
- **AC-11.6** `POST /tasks` with malformed JSON returns 422 (not 500).
- **AC-11.7** If env `TODO_API_KEY` is set, every endpoint except `/health` requires header `X-API-Key` equal to it, else 401 and no data change. If unset, no key is required (local single-user mode).
- **AC-11.8** The server binds to `127.0.0.1` by default.

### FR-12 CLI/API parity
- **AC-12.1** For each scenario in the shared scenario table (create, filter by tag, sort, transition, invalid transition, delete), the CLI and API invoked on identical initial data produce equivalent task data and equivalent error classes.
- **AC-12.2** Both interfaces call the same service functions; neither implements filtering, sorting, validation, or transition rules itself (verified by architecture test).

---

## 5. Non-Functional Requirements

| ID | Requirement | Binary check |
|---|---|---|
| **NFR-1** | Performance: with 10,000 tasks, list/filter/sort completes in ≤ 1 s and a single add in ≤ 500 ms on the dev machine. | Timed test passes. |
| **NFR-2** | Determinism: all "now/today" values come from an injected clock; no service/domain code calls `datetime.now()` directly. | Grep/architecture test finds none; tests use a fake clock. |
| **NFR-3** | Security: all input validated per §3.1 at the boundary; no secrets in repo; security gates per Constitution Art. VI pass. | `bandit`, `pip-audit`, `detect-secrets`, `tests/security/` all pass. |
| **NFR-4** | Quality gates: Constitution Art. III–V (ruff, mypy strict, coverage ≥ 90% / domain+services ≥ 95%). | `make verify` green. |
| **NFR-5** | Unicode: titles/descriptions with non-ASCII characters (e.g. `"café ✅"`, `"日本語"`) round-trip unchanged through CLI/API and file. | Round-trip test passes. |
| **NFR-6** | Portability: runs on Windows, Linux, macOS (path handling and atomic rename work on all). | Tests pass on Windows (primary) and CI Linux. |
| **NFR-7** | Self-healing: persistence recovery per AC-9.6; harness per Constitution Art. VII. | AC-9.6 test + `make verify` pass. |

---

## 6. Edge-Case Checklist (each MUST have a test)

1. Empty store: list, show, next, delete, transition.
2. Title: empty, whitespace, 200/201 chars, Unicode, leading/trailing spaces.
3. Tags: duplicates, mixed case, 10/11 tags, 30/31 chars, invalid characters, empty tag string.
4. Due date: invalid calendar date, wrong format, past, today, far future (`9999-12-31`).
5. Ids: 0, negative, non-integer, very large, deleted, never-existed.
6. Transitions: all 9 from/to combinations; same-state; unknown status.
7. File: missing, empty file (0 bytes), invalid JSON, wrong schema, newer `version`, read-only path, interrupted write.
8. Overdue boundary: due yesterday / today / tomorrow, with each status.
9. Sorting ties and missing due dates in both orders.
10. Injection-style strings in title/tag/query params stored and returned inertly (no execution/escaping failures).

---

## 7. Traceability Matrix (requirement → test group)

| Requirement | Test location (planned) |
|---|---|
| FR-1…FR-4 | `tests/unit/test_task_service_crud.py`, `tests/unit/test_task_validation.py` |
| FR-5 | `tests/unit/test_filtering.py` |
| FR-6 | `tests/unit/test_transitions.py` (parametrised over §3.3) |
| FR-7 | `tests/unit/test_sorting.py` |
| FR-8 | `tests/unit/test_next_task.py` |
| FR-9 | `tests/integration/test_json_repository.py` |
| FR-10 | `tests/contract/test_cli.py` |
| FR-11 | `tests/contract/test_api.py`, `tests/security/` |
| FR-12 | `tests/contract/test_parity.py`, `tests/architecture/` |
| NFR-1…7 | `tests/performance/`, `tests/security/`, harness |

---

## 8. Assumptions & Open Questions

**Assumptions (made to remove ambiguity; change here if wrong):**
1. Single user, single process at a time; no cross-process file locking in v1.
2. Priority has three levels (`low/medium/high`); "smart" is delivered via overdue detection and `next`.
3. Integer ids (not UUIDs) for CLI ergonomics.
4. `completed → pending` is the only way to reopen; `completed → in_progress` is deliberately disallowed.
5. API authentication is an **optional shared API key** (AC-11.7) because the app is local single-user; this is the minimal interpretation of Constitution Art. VI.4.

**Constitution deviation to resolve:** Constitution Art. I lists *SQLite via SQLAlchemy* for persistence, but this spec requires **JSON file persistence**. The repository interface (Art. II.1) remains, with a `JsonFileTaskRepository` as the implementation. The constitution should be amended (MINOR bump) to change the persistence row accordingly.

**Open questions for review:**
1. Should `tag` filter default to ALL-match (as specified) or ANY-match?
2. Is a `critical` priority level needed?
3. Should deleting require confirmation in the API (currently no)?
