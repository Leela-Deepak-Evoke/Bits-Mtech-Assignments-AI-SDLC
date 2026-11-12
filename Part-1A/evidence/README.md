# Evidence

## `initial-generation/`

Raw, unmodified output of the first `/speckit.implement` pass, copied **after generation and before any test run, lint run, or edit**.

| Item | Detail |
|---|---|
| Contents | `src/`, `tests/`, `pyproject.toml` (41 files + `pyproject.toml`) |
| Integrity | `initial-generation.sha256` — SHA-256 of every file in the snapshot (verify with `cd initial-generation && sha256sum -c ../initial-generation.sha256`) |
| Status of snapshot | Never executed in place; do not edit. Compare against the working tree to see what changed. |

### What changed between the snapshot and the working tree

Only gate-driven, behaviour-neutral fixes (the first test run of the snapshot passed 162/162 and mypy strict passed; ruff reported 23 findings):

| Files | Change | Reason |
|---|---|---|
| `src/.../domain/{query,rules}.py`, `interfaces/cli/render.py`, `tests/**` | `ruff format` / safe `ruff --fix` (line wrapping, unused `noqa`, `__all__` ordering) | ruff gate |
| `src/.../interfaces/cli/main.py` | Removed a redundant duplicate `Settings(...)` assignment; added `PLR0917` to inline `noqa` on Typer commands | cleanup + lint (many CLI options are inherent) |
| `src/.../interfaces/api/app.py` | Added `PLR0917` to inline `noqa` on the list endpoint | lint (many query params are inherent) |
| `pyproject.toml` | Test files ignore `PLR0913/PLR0917` (wide fixture factory) | lint, justified in a comment |
| `tests/contract/test_cli.py` | Renamed fixture `_data_file` → `data_path` | ruff `PT019` |
| `tests/integration/test_json_persistence.py` | Rewrote `test_ac_9_9` to assert specific exception types instead of a convoluted `pytest.raises(Exception)` | test clarity; stronger assertion |

No assertion was removed or loosened, no threshold lowered, no test skipped.

## `final-generation/`

Copy of the **passing** state of `src/`, `tests/` and `pyproject.toml`, taken on 2026-11-12 immediately after a full harness run returned PASS (lint, security and tests; 162/162 tests, 91.7% branch coverage).

| Item | Detail |
|---|---|
| Contents | 41 files + `pyproject.toml`, `__pycache__` excluded |
| Integrity | `final-generation.sha256` (verify with `cd final-generation && sha256sum -c ../final-generation.sha256`) |
| Harness evidence | `harness-log.md` (the run whose result this snapshot corresponds to) |

### Initial vs final

| | `initial-generation/` | `final-generation/` |
|---|---|---|
| State | Raw output, never run in place | After gate-driven fixes, harness PASS |
| Files that differ | — | 12 of 42: `pyproject.toml`; `src/.../domain/{query,rules}.py`; `interfaces/{api/app.py, cli/main.py, cli/render.py}`; 6 test files |
| Nature of the differences | — | Formatting, safe lint fixes, a duplicate line removed, `noqa`/lint-config adjustments, one fixture renamed, one test rewritten (see the table above) |
| Behaviour | 162/162 tests passed | 162/162 tests pass |

Regenerate the comparison with `diff -rq initial-generation final-generation`.

Not included in either snapshot: `.harness/` (created after the first generation, so it has no "initial" counterpart; its results are in `harness-log.md`).
