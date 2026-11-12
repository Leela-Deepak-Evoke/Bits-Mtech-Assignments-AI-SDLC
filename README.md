# Assignment 1 – Spec-Driven Development with AI

This repo holds two small Python projects, both built **spec-first**: we write down the rules (a "constitution" and a "spec"), let an AI generate the code, and then use automated checks (a "harness") to make sure the code actually follows those rules.

| Part | Project | One-line summary |
|---|---|---|
| [Part-1A](Part-1A) | Smart Todo & Task CLI/API | A to-do manager you can use from the terminal or over HTTP |
| [Part-1B](Part-1B) | Natural-Language Reminder Agent | Turns a sentence like *"remind me to call mom tomorrow at 5pm"* into a scheduled reminder |

---

## Part-1A – Smart Todo & Task CLI/API

A single-user task manager with two ways to use it:

- **CLI** – a `todo` command in your terminal (built with Typer)
- **API** – a JSON REST API (built with FastAPI)

Both share the same logic and the same JSON data file.

**What it can do**
- Create, read, update and delete tasks
- Filter by tag or status, sort by priority
- Move tasks between `pending` → `in_progress` → `completed` (invalid moves are rejected)
- Flag **overdue** tasks automatically
- Suggest the **next task** you should work on

**Task fields:** title, description, status, priority (low/medium/high), tags, due date, and created/updated/completed timestamps.

### Code layout (`Part-1A/src/todo`)

| Folder | Role |
|---|---|
| `domain/` | Core task rules and the "next task" logic |
| `services/` | Business operations (create, update, list…) |
| `repositories/` | Storage interface |
| `infrastructure/` | JSON file storage, clock, serialization |
| `interfaces/cli`, `interfaces/api` | The terminal and HTTP front-ends |
| `app/` | Config and wiring everything together |

### Flow diagram

```mermaid
flowchart TD
    U([User]) --> CLI["CLI: todo command<br/>(Typer)"]
    U --> API["HTTP API<br/>(FastAPI)"]
    CLI --> SVC
    API -->|"validate request (Pydantic)"| SVC["Task Service<br/>create / update / list / delete"]
    SVC --> DOM["Domain rules<br/>validation, status transitions,<br/>overdue check, next-task suggestion"]
    DOM -->|"valid"| REPO["Repository interface"]
    DOM -->|"invalid"| ERR["Error<br/>(CLI message / API 4xx)"]
    REPO --> JSON[("JSON file store")]
    CLK["Clock (UTC)"] -.-> SVC
    JSON --> REPO --> SVC
    SVC --> OUT["Task output<br/>(with computed overdue flag)"]
    OUT --> CLI
    OUT --> API
    ERR --> CLI
    ERR --> API
```

**Task status flow**

```mermaid
stateDiagram-v2
    [*] --> pending: create
    pending --> in_progress: start
    pending --> completed: complete
    in_progress --> pending: back to pending
    in_progress --> completed: complete
    completed --> pending: reopen
```

### Run it

```bash
cd Part-1A
pip install -e ".[dev]"
todo --help                 # CLI
python -m todo.interfaces.api   # start the API
pytest                      # run tests
```

### Run the harness (Part-1A)

The harness runs lint, then security checks, then tests, and ends with an overall PASS/FAIL (exit code 0 = PASS). Every run is appended to `Part-1A/.harness/harness-log.md`.

```bash
cd Part-1A
pip install -e ".[dev]"
python .harness/run_harness.py              # all checks
python .harness/run_harness.py --skip-audit # offline: skip pip-audit
python .harness/run_harness.py --only tests # lint | security | tests
```

---

## Part-1B – Natural-Language Reminder Agent

An agent that reads an English message and creates a structured reminder. It can also **reschedule** or **snooze** an existing one. If something is missing or unclear (e.g. no time given), it **asks a question instead of guessing**.

**Key ideas**
- The LLM (Claude) only *extracts* what the user meant – it never calculates dates.
- Plain, deterministic code resolves dates/times using the configured timezone.
- Output must match JSON schemas, and safety rules reject unsupported requests.
- Quality is measured on an evaluation dataset against set thresholds.

### Flow diagram

```mermaid
flowchart TD
    U([User message]) --> CLI["CLI: remind"]
    CLI --> SAN["Sanitize input<br/>(length, safety checks)"]
    SAN --> AG["Reminder Agent"]
    AG --> LLM["LLM extractor (Claude)<br/>intent + text spans only"]
    LLM --> SCH{"Matches<br/>extraction schema?"}
    SCH -->|no| REF["Refused / error response"]
    SCH -->|yes| INT{"Intent?"}
    INT -->|"unsupported"| REF
    INT -->|"create / reschedule / snooze"| RES["Resolver (plain code, no LLM)<br/>dates, times, durations, timezone"]
    RES --> OK{"Enough info<br/>and unambiguous?"}
    OK -->|no| CLAR["Ask a clarifying question<br/>(max 3 rounds)"]
    CLAR --> U
    OK -->|yes| STORE[("Reminder store")]
    STORE --> INV["Invariant checks"]
    INV --> RESP["Structured response<br/>(validated against schema)"]
    REF --> RESP
    RESP --> U
```

**How quality is checked**

```mermaid
flowchart LR
    DS[("Eval dataset")] --> EX["Executor<br/>runs cases through the agent"]
    EX --> L1["Layer 1<br/>structure / schema"]
    EX --> L2["Layer 2<br/>invariants"]
    EX --> L3["Layer 3<br/>semantic correctness"]
    L1 --> M["Metrics"]
    L2 --> M
    L3 --> M
    M --> T{"Meets<br/>thresholds?"}
    T -->|yes| P([PASS])
    T -->|no| F([FAIL])
```

### Run it

```bash
cd Part-1B
pip install -e ".[dev]"
remind --help
pytest
python evals/run_eval.py    # deterministic evaluation (replay)
```

### Run the harness (Part-1B)

Part-1B has **two evaluation pipelines**. Both append to `Part-1B/evidence/harness-log.md`.

```bash
cd Part-1B
pip install -e ".[dev]"

# 1. Deterministic pipeline: replays recorded extractions, no network, no API key. Exit code 0 = PASS.
python evals/run_eval.py --label "my run"

# 2. Non-deterministic pipeline: the real Claude model extracts, each case is repeated.
export GROQ_API_KEY=...             # or put it in a git-ignored .env file; never commit it (PowerShell: $env:GROQ_API_KEY="...")
python evals/run_live_eval.py --runs 3 --pause 1          # Groq (default provider)
python evals/run_live_eval.py --provider anthropic        # needs ANTHROPIC_API_KEY instead
python evals/run_live_eval.py --stub-client   # offline smoke test of the pipeline, not real model evidence

# Record the final human decision
python .harness/log.py decision --decision ACCEPT --by "<your name>" --notes "<why>"
```

### Acceptance and known limitations

See [Part-1A/ACCEPTANCE.md](Part-1A/ACCEPTANCE.md) and [Part-1B/ACCEPTANCE.md](Part-1B/ACCEPTANCE.md).

---

## Overall workflow (both parts)

```mermaid
flowchart LR
    C["Constitution<br/>(rules)"] --> S["Spec<br/>(requirements + tests)"]
    S --> P["Plan"]
    P --> T["Tasks"]
    T --> G["AI generates code"]
    G --> H["Harness<br/>lint → security → tests"]
    H -->|fail| G
    H -->|pass| D(["Final code + evidence"])
```

## What's in each part

```
Part-X/
├── .speckit/   Constitution, spec, plan, tasks (the "rules" written before coding)
├── .harness/   Automated checks: lint, security, tests, and quality gates
├── src/        Final source code
├── tests/      Test suite
└── evidence/   Snapshot of the first AI-generated code (with SHA-256 hash) for comparison
```

Part-1B additionally has `evals/` with the evaluation dataset and runner.

## Requirements

- Python 3.11+
- Part-1B's live evaluation needs a `GROQ_API_KEY` (or `ANTHROPIC_API_KEY`) environment variable or git-ignored `.env`. No keys or `.env` files are stored in this repo.
