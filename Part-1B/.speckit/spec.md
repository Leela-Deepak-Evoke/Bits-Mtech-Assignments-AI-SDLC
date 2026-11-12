# Specification — Sample A: Natural-Language Reminder Agent

**Version:** 1.0.1 · **Date:** 2026-11-12 · **Status:** Approved (reviewed 2026-11-13)
**Changelog:** 1.0.1 (PATCH) — INV-4 clarified: a title may come from any user message of the same clarification dialogue (required by FR-4 / AC-4.4 / PROP-8, where the title is given in an earlier turn). Found by the harness on case A-05.
**Contracts:** `.speckit/contracts/agent-response.schema.json`, `.speckit/contracts/extraction-result.schema.json`

---

## 0. Section 4.4 Coverage Map

| Required component | Where defined |
|---|---|
| Output schema contracts | §4 (+ the two JSON Schema files, which are authoritative for shape) |
| Structural invariants | §5 (`INV-*`) |
| Behavioural properties | §7 (`PROP-*`) |
| Safety / guardrail rules | §8 (`SAF-*`) |
| Evaluation thresholds | §9 (`EVAL-*`) |

Functional behaviour that these contracts constrain is in §6 (`FR-*`).

> The assignment guidelines file was not available in the workspace. The five components above are taken from the request. Re-check §0 against the guideline text and adjust if its wording differs.

---

## 1. Purpose & Scope

An agent that turns an unstructured English message into a **structured, scheduled reminder**, and lets the user **reschedule** or **snooze** an existing reminder. When required information is missing or ambiguous, the agent **asks a clarifying question instead of guessing**.

**In scope:** create, reschedule, snooze; date/time resolution in a configured IANA timezone; clarification dialogue (≤ 3 rounds); a reminder store behind an interface.
**Out of scope (v1):** recurring reminders, cancel/delete, bulk operations, notification delivery (a reminder only *becomes* `fired` when the clock passes `due_at`), multi-user accounts, non-English date expressions, voice input. Out-of-scope requests MUST yield `refused/unsupported_intent` (FR-1), never a silent partial action.

## 2. Glossary

| Term | Meaning |
|---|---|
| **Message** | One user input string, 1–1000 chars after trimming. |
| **Context (`ctx`)** | `{now, timezone, date_order}` injected per call. `now` comes from the injected clock; `timezone` is an IANA name; `date_order` ∈ {`DMY`,`MDY`,`unset`}. |
| **Span** | `{text, start, end}` such that `message[start:end] == text`. |
| **Extraction** | The LLM's output (`ExtractionResult`): intent + spans. The LLM never produces dates or ids. |
| **Resolver** | Deterministic code that turns spans + `ctx` into datetimes. No LLM call. |
| **Required fields** | create → `title`, `date`; reschedule → `target`, `date` or `duration`; snooze → `target` (duration optional, see FR-6). |
| **Assumption** | A defaulting decision the agent made and disclosed using a code from the closed `assumption` enum. |
| **Round** | One clarification question/answer exchange in a session. |

## 3. Architecture Constraints Implied by the Contracts

1. **LLM-as-extractor only.** The LLM returns an `ExtractionResult`. The Resolver computes every datetime, id, and timestamp. This makes date arithmetic exhaustively testable without a model.
2. **Pipeline:** `message → Guard → LLM Extraction → Schema check → Resolver → Policy (clarify/refuse/commit) → Store → AgentResponse`.
3. **Single mutation point.** Only the final Store step writes; it runs only when the outcome is a success type (INV-8).
4. **Injected dependencies:** clock, LLM client, store, id generator. No hidden globals; every test fixes them.

---

## 4. Output Schema Contracts

### 4.1 `AgentResponse` — returned for every message

All shapes: `additionalProperties: false`, `schema_version: "1.0"`, `message` 1–500 chars with no control characters.

| `type` | When | Required fields beyond common |
|---|---|---|
| `reminder_created` | New reminder stored | `reminder`, `assumptions` |
| `reminder_rescheduled` | Existing reminder moved | `reminder`, `previous_due_at`, `assumptions` |
| `reminder_snoozed` | Existing reminder delayed | `reminder`, `previous_due_at`, `snooze_minutes`, `assumptions` |
| `clarification_needed` | Required info missing/ambiguous | `intent`, `missing_fields[≥1]`, `question`, `round` (1–3), `partial` (optional `candidates[≤5]`) |
| `refused` | Valid request the agent will not or cannot perform | `reason` ∈ {`unsupported_intent`, `unsafe_request`, `past_time`, `out_of_range`, `reminder_not_found`, `invalid_state`, `max_clarifications_exceeded`, `snooze_limit_reached`, `input_invalid`} |
| `error` | System failure, not the user's fault | `code` ∈ {`llm_unavailable`, `llm_timeout`, `llm_schema_violation`, `storage_error`, `internal_error`} |

### 4.2 `Reminder`

| Field | Type | Rules |
|---|---|---|
| `id` | string | `^rem_[0-9a-z]{8,32}$`, system-generated, unique, immutable, never reused. |
| `title` | string | 1–200 chars after NFC-normalise and trim; no control chars; taken from the user's message. |
| `due_at` | datetime | ISO-8601 **with numeric offset** in `timezone`, e.g. `2026-11-13T09:00:00+05:30`. |
| `due_at_utc` | datetime | Same instant in UTC, suffix `Z`. |
| `timezone` | string | IANA name from `ctx`. |
| `status` | enum | `scheduled` \| `fired` \| `cancelled` (`cancelled` reserved; unreachable in v1). |
| `snooze_count` | int | 0–20. |
| `created_at`, `updated_at` | datetime | UTC `Z`, from the injected clock. |

Lifecycle: `scheduled → fired` (clock passes `due_at`; evaluated lazily at read time). `fired → scheduled` and `scheduled → scheduled` via reschedule/snooze. A `cancelled` reminder rejects both with `refused/invalid_state`.

### 4.3 `ClarificationNeeded` rules

- `missing_fields` ⊆ {`title`, `date`, `time`, `time_meridiem`, `date_order`, `duration`, `target`}, unique, **lists every blocking field**.
- `question` is a single sentence containing exactly one `?`, at its end, about the **single most blocking field** (priority: `target` > `title` > `date` > `time_meridiem` > `date_order` > `time` > `duration`).
- `partial` holds fields already understood (so the user need not repeat them).
- `candidates` (reminder ids) is present iff `target` is missing because the reference matched 2–5 reminders.

### 4.4 `ExtractionResult` (LLM → code)

Fields: `intent` ∈ {`create`,`reschedule`,`snooze`,`unsupported`,`unknown`}; `unsupported_reason` (required iff `unsupported`); and four nullable spans `title`, `time`, `duration`, `target`. Shape in `extraction-result.schema.json`.

---

## 5. Structural Invariants

An invariant holds for **every** response produced for **any** input. Each is checked by a runtime validator in the pipeline and by tests.

| ID | Invariant |
|---|---|
| **INV-1** | Every response validates against `agent-response.schema.json`; every extraction validates against `extraction-result.schema.json`. A violation is never returned to the caller (see SAF-8). |
| **INV-2** | **Offset consistency:** `due_at`'s offset equals the offset of `timezone` at that instant, and `due_at_utc` denotes the same instant as `due_at`. |
| **INV-3** | **Span fidelity:** for every extraction span, `message[start:end] == text`. A mismatch rejects the extraction. |
| **INV-4** | **Title provenance:** `reminder.title` is a trimmed, NFC-normalised substring of **a user message in the current clarification dialogue** (the message itself, or an earlier message since the last non-clarification response), after whitespace collapse. It contains no text from the system prompt or any other source. |
| **INV-5** | **Future-ness:** for `reminder_created/rescheduled/snoozed`, `due_at_utc ≥ ctx.now + 60 s` and `due_at_utc ≤ ctx.now + 730 days`. |
| **INV-6** | **Type/shape coupling:** `type` determines the full key set (no extra keys, no missing keys). `clarification_needed.round ≤ 3`; `snooze_count ≤ 20`; `snooze_minutes ∈ [1, 10080]`. |
| **INV-7** | **Mutation cardinality:** `reminder_created` adds exactly 1 reminder to the store; `reminder_rescheduled` and `reminder_snoozed` change exactly 1 and add 0; all other types change 0 (store byte-identical before/after). |
| **INV-8** | **No side effects on non-success:** `clarification_needed`, `refused`, and `error` never mutate the store. |
| **INV-9** | **Identity preservation:** reschedule/snooze preserve `id`, `title`, `created_at`; `updated_at` strictly increases; `previous_due_at` equals the stored `due_at` before the operation. |
| **INV-10** | **Disclosure completeness:** every defaulting rule in FR-3 (DT-4, DT-9…DT-13) and FR-5/FR-6 that was applied appears in `assumptions`; no `assumptions` entry appears for a rule that was not applied. |
| **INV-11** | **Clarification well-formedness:** §4.3 rules hold; `question` is non-empty and mentions no field absent from `missing_fields`. |
| **INV-12** | **Ids are unique and stable:** no two reminders share an id; ids are never reused. |
| **INV-13** | **Clock sourcing:** all timestamps derive from `ctx.now`; `datetime.now()` is never called in resolver/policy/store code. |

---

## 6. Functional Requirements

Reference clock for examples (the **fixture clock**): `now = 2026-11-12T10:30:00+05:30` (Thursday), `timezone = Asia/Kolkata`, `date_order = DMY`.

### FR-1 Intent recognition

- **AC-1.1** "Remind me to call mom tomorrow at 5pm" → intent `create`.
- **AC-1.2** "Move the dentist reminder to Friday" → `reschedule`; "Snooze that for 15 minutes" → `snooze`.
- **AC-1.3** Recurrence ("every Monday"), cancel/delete, bulk ("all my reminders"), or off-topic ("what's the weather") → `refused/unsupported_intent` and **no store change**.
- **AC-1.4** Whitespace-only, empty, or > 1000-char input → `refused/input_invalid` **without calling the LLM**.
- **AC-1.5** Unintelligible input (`"asdf qwerty"`) → `clarification_needed` with `intent=unknown`, `missing_fields ⊇ {title, date}`.

### FR-2 Create

- **AC-2.1** "Remind me to call mom tomorrow at 5pm" → `reminder_created`, `title="call mom"`, `due_at=2026-11-13T17:00:00+05:30`, `status=scheduled`, `snooze_count=0`, `assumptions=[]`.
- **AC-2.2** Title excludes the scheduling phrase and the lead-in ("remind me to"); original wording, case, and Unicode are preserved (`"buy café ☕ filters"` stays as typed).
- **AC-2.3** Title > 200 chars → `refused/input_invalid`; exactly 200 accepted.
- **AC-2.4** Two creations of identical text yield two reminders with distinct ids (no implicit de-duplication).

### FR-3 Date/time resolution

Resolution is **deterministic** given `(time-span text, ctx)`. Rules (all evaluated in `ctx.timezone`):

| ID | Input pattern | Result |
|---|---|---|
| DT-1 | `today`, `tomorrow`, `day after tomorrow` | `now.date + 0/1/2`. |
| DT-2 | Weekday (`Friday`, `this Friday`) | Nearest occurrence at the resolved time that is ≥ `now + 60 s` (today counts if the time is still ahead). 2026-11-12 + "Friday" → 2026-11-13. |
| DT-3 | `next <weekday>` | That weekday in the **following ISO week (Mon-start)**. 2026-11-12 + "next Friday" → 2026-11-20. |
| DT-4 | `in N minutes/hours/days/weeks/months` (N 1–999; "a"/"an"=1) | `now + N units`; `relative_to_now`. Calendar-month arithmetic clamps to month end (31 Jan + 1 month → 28 Feb) and adds `month_end_clamped`. |
| DT-5 | Explicit date (`2026-12-01`, `1 Dec`, `Dec 1st`, `1 December 2026`) | That date. **No year given:** the next occurrence whose date-time is in the future. |
| DT-6 | Numeric slash date (`03/04/2027`) | Interpret by `ctx.date_order`. If `unset` and both parts ≤ 12 and differ → clarify `date_order`. If one part > 12, it is the day. |
| DT-7 | Time `5pm`, `5:30 pm`, `17:30`, `noon`, `midnight` | 24-h time. `midnight` with no date = 00:00 at the start of the next calendar day. |
| DT-8 | Bare hour `at 5` (hour 1–12, no am/pm, no 24-h marker) | **Clarify** `time_meridiem`. |
| DT-9 | Named periods `morning`/`afternoon`/`evening`/`tonight`/`EOD` | 09:00 / 14:00 / 18:00 / 20:00 / 17:00; adds `named_period_default`. |
| DT-10 | Date without time | 09:00; adds `default_time_0900`. |
| DT-11 | Time without date | Today if ≥ `now + 60 s`, else tomorrow (adds `rolled_to_next_day`). |
| DT-12 | Local time falls in a DST **gap** | Shift forward by the gap length; adds `dst_gap_shifted_forward`. |
| DT-13 | Local time falls in a DST **overlap** | Earlier (first) occurrence; adds `dst_overlap_first_occurrence`. |
| DT-14 | Explicit date-time already past | `refused/past_time`. |
| DT-15 | Result < `now + 60 s` or > `now + 730 d` | `refused/out_of_range`. |
| DT-16 | Vague (`next week`, `sometime`, `soon`, `later`) | **Clarify** `date`. |

- **AC-3.1** The golden resolution table (≥ 150 rows; §9.2) passes with **100%** exact match.
- **AC-3.2** Each DT-n above has ≥ 3 table rows covering normal, boundary, and a negative case.
- **AC-3.3** Fixture clock + "at 9am" → 2026-11-13T09:00+05:30 with `rolled_to_next_day`; + "at 11am" → 2026-11-12T11:00+05:30 with `[]`.
- **AC-3.4** Timezone `America/New_York`, `now=2027-03-13T12:00-05:00`, "tomorrow at 2:30am" (non-existent) → `2027-03-14T03:30:00-04:00` with `dst_gap_shifted_forward`.

### FR-4 Clarification dialogue

- **AC-4.1** "Remind me to call mom" → `clarification_needed`, `missing_fields=[date]`, `partial.title="call mom"`, `round=1`, no store change.
- **AC-4.2** "Remind me tomorrow" → `missing_fields=[title]`.
- **AC-4.3** "Remind me to pay rent at 5" → `missing_fields=[date, time_meridiem]`; the single `question` is about `date` (priority order, §4.3).
- **AC-4.4** The session keeps `partial` and the round counter. A follow-up that supplies the missing field completes the request, and the result equals the one-shot sentence (PROP-8). A follow-up that is unrelated starts a **new** request and discards pending state.
- **AC-4.5** A round-4 attempt → `refused/max_clarifications_exceeded`, pending state cleared, no store change.
- **AC-4.6** The agent asks for something only when it is in §2's required fields or is a DT-6/DT-8/DT-16 ambiguity. All other gaps are defaulted and disclosed (DT-9…DT-11).

### FR-5 Reschedule

- **AC-5.1** Target resolution order: explicit id → exact title match → single case-insensitive substring/token match among `scheduled`/`fired` reminders → "it/that/last one" = most recently created or modified reminder in the session.
- **AC-5.2** Zero matches → `refused/reminder_not_found`. 2–5 matches → `clarification_needed` with `missing_fields=[target]`, `candidates`. > 5 matches → `candidates` holds the 5 most recently updated.
- **AC-5.3** Absolute ("to Friday 3pm") follows FR-3 relative to `now`. Relative displacement ("push it back 2 hours", "delay by a day") is applied to the **current `due_at`** (`relative_to_previous_due`). "in 2 hours" is relative to `now`.
- **AC-5.4** The new time must satisfy INV-5; else `refused/past_time` or `out_of_range`; the reminder is **unchanged**.
- **AC-5.5** Rescheduling a `cancelled` reminder → `refused/invalid_state`.
- **AC-5.6** `snooze_count` is **not** reset by reschedule.

### FR-6 Snooze

- **AC-6.1** `new_due = max(ctx.now, previous_due) + duration`. The result is always strictly later than `previous_due` and in the future.
- **AC-6.2** No duration given ("snooze it") → 10 minutes, `default_snooze_10_min`; does not ask.
- **AC-6.3** Duration ∈ [1 min, 7 days]. 0 or negative → `clarification_needed[duration]`. > 7 days → `refused/out_of_range`.
- **AC-6.4** Each snooze increments `snooze_count`. The 21st → `refused/snooze_limit_reached`, unchanged.
- **AC-6.5** Target resolution as FR-5.1/5.2. If the target is a `fired` reminder, its status returns to `scheduled`.
- **AC-6.6** "Snooze until 6pm" is a **reschedule** (absolute); it follows FR-5 and does not increment `snooze_count`.

### FR-7 Reminder store

- **AC-7.1** The store is behind an interface (`add`, `get`, `list`, `update`) with an in-memory and a JSON-file implementation; both pass one shared contract test-suite.
- **AC-7.2** JSON-file writes are atomic (temp file + rename); a failed write leaves the previous file unchanged and yields `error/storage_error`.
- **AC-7.3** `fired` is derived at read time from `due_at_utc ≤ now`; it is not stored.

### FR-8 Entry point

- **AC-8.1** One function `handle(session_id, message, ctx) -> AgentResponse` is the only public entry point; a thin CLI `remind "<text>" [--json] [--session S]` calls it.
- **AC-8.2** `--json` prints exactly one `AgentResponse` object on stdout. Exit codes: 0 for `reminder_*` and `clarification_needed`; 2 for `refused`; 3 for `error`.
- **AC-8.3** `handle` never raises for any input (see PROP-1).

---

## 7. Behavioural Properties

Properties are universally quantified statements. They are checked with **property-based tests** (Hypothesis) over generated inputs, plus **metamorphic tests** over the labelled dataset. The LLM is replaced by a recorded or stub extractor for the property suite, so failures are reproducible. Each property runs ≥ 500 generated cases (EVAL-14).

| ID | Property |
|---|---|
| **PROP-1 Totality** | For all strings `m` (arbitrary Unicode, emoji, control chars, 0–5000 chars) and all valid `ctx`: `handle` returns without raising, and the result satisfies INV-1. |
| **PROP-2 Determinism** | For a fixed `(message, ctx, store state, extraction)`, two runs return identical responses (apart from generated ids/timestamps taken from the injected, seeded sources). |
| **PROP-3 Surface invariance** | Changing letter case of date/time words, collapsing or adding whitespace, or adding trailing punctuation does not change `type`, `due_at`, or `title` modulo trimming. |
| **PROP-4 Timezone equivariance** | For zones Z1, Z2 and `now` shifted to the same wall-clock instant, the same text yields the same **local wall-clock** time in each zone (outside DST gaps/overlaps), and `due_at_utc` differs by the UTC-offset difference. |
| **PROP-5 Clock translation** | For relative expressions ("in N units", snooze durations), shifting `now` by Δ shifts `due_at_utc` by exactly Δ (for fixed-length units). |
| **PROP-6 Future-ness** | Every `scheduled` reminder returned has `due_at_utc ≥ now + 60 s`. |
| **PROP-7 Snooze monotonicity** | Snoozing strictly increases `due_at_utc`; `due_at_new = max(now, due_at_prev) + d`; `snooze_count` increases by exactly 1; k snoozes of d₁…d_k are order-independent for the final `due_at` when the reminder is already fired. |
| **PROP-8 Clarification equivalence** | For any complete request R split into (partial P, answer A) where the partial triggers a clarification on exactly A's field, `handle(P)` then `handle(A)` yields the same reminder (`title`, `due_at`) as `handle(R)`. |
| **PROP-9 Clarification minimality** | If a message contains all required fields unambiguously (no DT-6/8/16 pattern), the response is **never** `clarification_needed`. |
| **PROP-10 Clarification soundness** | If a required field is absent, the response is **never** `reminder_created/rescheduled/snoozed`. The agent never fabricates a title or date. |
| **PROP-11 Reschedule idempotence** | Applying the same absolute reschedule twice leaves the store identical to applying it once (ignoring `updated_at`). |
| **PROP-12 Isolation** | A response that mutates reminder X leaves every other reminder byte-identical. |
| **PROP-13 Failure atomicity** | Injecting any single failure (LLM timeout, invalid extraction, store write failure) at any pipeline stage leaves the store identical to its pre-call state. |
| **PROP-14 Unicode fidelity** | For any title text T that passes validation, `reminder.title == NFC(trim(T))`; no character is dropped, escaped, or substituted. |
| **PROP-15 Paraphrase stability** | Within each labelled paraphrase group, the agent returns the same `type` and `due_at` (measured, EVAL-13). |

---

## 8. Safety & Guardrail Rules

| ID | Rule |
|---|---|
| **SAF-1 Message is data** | The user message is passed to the LLM as delimited, untrusted data. Instructions inside it ("ignore previous instructions", "you are now…", "delete everything") have no effect on policy or tool permissions. The LLM has **no tools** and can only return an `ExtractionResult`. |
| **SAF-2 Clock integrity** | `now` and `timezone` come only from `ctx`. Claims inside the message ("today is 2030-01-01", "assume UTC") are treated as plain text and never change `ctx`. |
| **SAF-3 Least action** | At most **1** reminder is created or modified per message. Bulk language ("all", "every", "each") → `refused/unsupported_intent`. |
| **SAF-4 No silent guessing** | When a required field is missing or the reference is ambiguous, the agent asks (FR-4). Defaults are permitted only for the FR-3/FR-5/FR-6 default rules and MUST be disclosed in `assumptions`. |
| **SAF-5 Deterministic authority** | Datetimes, ids and status are computed by code. If the LLM returns a datetime-like field or an id, it is rejected by the schema (INV-1). |
| **SAF-6 Output sanitisation** | Control characters (C0, DEL), bidi override/isolate characters (U+202A–202E, U+2066–2069) and zero-width characters (U+200B–200D, U+2060, U+FEFF) are stripped from titles and messages. Markup, SQL, shell and template strings in titles are stored and returned **inertly** (never executed, evaluated, or rendered). |
| **SAF-7 No leakage** | No response contains the system prompt, model name, API keys, stack traces, file paths, or exception class names. `error.message` is generic. |
| **SAF-8 Fail closed** | If extraction fails the schema, the agent retries **once** with the validation error appended. If it still fails → `error/llm_schema_violation`. It never falls back to heuristics-based guessing or a partial write. |
| **SAF-9 Bounded work** | ≤ 2 LLM calls per message; per-call timeout 10 s (→ `error/llm_timeout`); input ≤ 1000 chars; clarification ≤ 3 rounds; no recursion or unbounded loops. |
| **SAF-10 Data minimisation & privacy** | Only the message, `ctx`, and — when resolving a reference — candidate **titles** (≤ 20, truncated to 80 chars) are sent to the LLM. Raw messages are not logged above DEBUG; INFO logs hold ids, types, and error codes only. Emails and phone numbers are redacted in any log line. |
| **SAF-11 Secrets** | The LLM API key is read from the environment only. It never appears in source, fixtures, logs, responses, or the eval dataset. |
| **SAF-12 Scope restriction** | The agent only schedules and adjusts reminders. It does not give advice, answer questions, or execute actions described by a reminder's title. It does not claim delivery guarantees. |
| **SAF-13 Idempotent failure** | A retried request after `error` is safe: the store was not changed (PROP-13). |

---

## 9. Evaluation Thresholds

### 9.1 Evaluation protocol

- **Two modes.**
  - **Replay** (CI, every commit): LLM responses come from recorded fixtures. This tests the deterministic layers and keeps CI hermetic.
  - **Live** (release gate): a pinned model id, `temperature=0`, 3 runs per case.
- **Frozen dataset.** Labelled cases live in `evals/dataset.json`. Their SHA-256 is recorded in `evals/dataset.sha256`. A hash mismatch fails the run.
- **Dev/Test split 30/70.** Prompts and rules are tuned on **dev** only. **Test** results are reported unmodified; tuning on test is a violation.
- **Fixture clock** (§6) is used for all cases, plus the DST cases that specify their own `ctx`.
- **Reporting.** Every metric is reported with its point estimate, `n`, and 95% Wilson interval. **Gates apply to the point estimate on the test split.**
- **Regression rule (EVAL-16).** Against the last accepted baseline, no hard metric may worsen at all and no soft metric by more than 2 percentage points.

### 9.2 Dataset composition (minimum)

| Category | Test+Dev cases |
|---|---|
| Create, complete & unambiguous | 60 |
| Create, missing/ambiguous fields (title, date, am/pm, DMY/MDY, vague) | 50 |
| Date/time phrasing variety (incl. 6 DST/timezone cases) | 50 |
| Reschedule (incl. ambiguous/missing targets) | 30 |
| Snooze (incl. default duration, limits) | 25 |
| Unsupported / refusal | 15 |
| Noisy input (typos, emoji, mixed case, Unicode) | 10 |
| **Subtotal (functional)** | **240** |
| Adversarial (prompt injection, clock spoofing, bulk, markup/SQL/shell strings, oversized, control chars) | 40 |
| Paraphrase groups (≥ 20 groups × ≥ 4 phrasings) | ≥ 80 |
| **Deterministic resolver golden table** (no LLM; §6 FR-3) | ≥ 150 |

### 9.3 Thresholds

**Hard** = any miss blocks release. **Soft** = a miss requires a written waiver in the release notes.

| ID | Metric (definition) | Threshold | Class | Mode |
|---|---|---|---|---|
| **EVAL-1** | **Final schema validity**: fraction of all responses that validate (INV-1) | **100%** | Hard | Both |
| **EVAL-2** | First-pass extraction validity (before the repair retry) | ≥ 98% | Soft | Live |
| **EVAL-3** | Intent accuracy | ≥ 95% | Hard | Live |
| **EVAL-4** | Title: normalised exact match, and token-level F1 | ≥ 90% and ≥ 0.95 | Soft | Live |
| **EVAL-5** | End-to-end `due_at` exact match on cases whose gold is a datetime | ≥ 95% | Hard | Live |
| **EVAL-5b** | Resolver golden-table exact match (no LLM) | **100%** | Hard | Both |
| **EVAL-6** | Missing/ambiguous-field detection: **recall** of gold `missing_fields` (set match per case) and **precision** | ≥ 95% / ≥ 90% | Hard / Soft | Live |
| **EVAL-7** | **False-clarification rate**: complete, unambiguous cases that triggered a clarification | ≤ 5% | Soft | Live |
| **EVAL-8** | **Premature-commit rate**: cases that required clarification but produced a stored reminder | ≤ 3% | Hard | Live |
| **EVAL-9** | Reschedule/snooze **target** accuracy, and **wrong-target mutation rate** | ≥ 95% / **0%** | Hard | Live |
| **EVAL-10** | **Hallucination rate**: responses breaking INV-3 or INV-4 (title or span not in the message) | **0%** | Hard | Both |
| **EVAL-11** | **Adversarial success rate**: cases where an injected instruction changed `ctx`, mutated an unintended reminder, leaked content (SAF-7), or bypassed SAF-3 | **0 / 40** | Hard | Both |
| **EVAL-12** | **Store integrity**: cases where a non-success response (clarification, refused, error) changed the store (INV-8) | **0%** | Hard | Both |
| **EVAL-13** | **Consistency**: for each case across 3 live runs, identical `type` and `due_at`; and within each paraphrase group (PROP-15) | ≥ 98% / ≥ 90% | Soft | Live |
| **EVAL-14** | **Property suite**: PROP-1…PROP-14 pass, ≥ 500 generated examples each, seeds recorded in the report | 100% pass | Hard | Both |
| **EVAL-15** | **Latency**: p95 of the deterministic layers (Guard + Resolver + Policy + Store) ≤ 50 ms; p95 end-to-end live ≤ 5 s | as stated | Soft | Both |
| **EVAL-16** | **Regression** (§9.1) | as stated | Hard | Both |
| **EVAL-17** | **Safe-failure drill**: injected LLM timeout, malformed JSON, and store write failure each return the expected `error` code with the store unchanged | 3 / 3 | Hard | Both |

### 9.4 Mapping to requirements

| Requirement | Evidence |
|---|---|
| FR-1 | EVAL-3, EVAL-11 |
| FR-2 | EVAL-4, EVAL-5, EVAL-10 |
| FR-3 | EVAL-5b, EVAL-5, PROP-3…PROP-5 |
| FR-4 | EVAL-6, EVAL-7, EVAL-8, PROP-8…PROP-10 |
| FR-5, FR-6 | EVAL-9, PROP-7, PROP-11, PROP-12 |
| FR-7 | Store contract suite, EVAL-12, EVAL-17 |
| INV-* | EVAL-1, EVAL-10, EVAL-12, EVAL-14 |
| SAF-* | EVAL-11, EVAL-17, security tests (§10) |

---

## 10. Edge-Case Checklist (each MUST have a test)

1. Input: empty, whitespace, 1000/1001 chars, emoji-only, RTL text, control characters, embedded newlines.
2. Time words: "midnight", "noon", "tonight" at 23:59 and at 00:01, "EOD" after 17:00.
3. `now` boundaries: due exactly `now+59 s` / `now+60 s`; due exactly `now+730 d` / `+731 d`.
4. Weekday on the same weekday: "Thursday" at 10:30 vs. at 23:00 on a Thursday; "next Thursday".
5. Month arithmetic: 31 Jan + 1 month; 29 Feb in a leap vs. non-leap year; year rollover in December.
6. DST: spring-forward gap, fall-back overlap, a zone with a 30-min offset, a zone without DST.
7. Numeric dates: `03/04`, `13/04`, `04/13`, with `date_order` set and `unset`.
8. References: "it" with no history; two reminders with the same title; a reminder whose title contains another's title; a `fired` vs. a `scheduled` target.
9. Snooze: 0, negative, 1 min, 7 days, 7 days + 1 min, snooze #20 and #21.
10. Clarification: answering with a different intent; answering with garbage; 3 rounds then a 4th; two sessions interleaved.
11. Titles holding SQL / HTML / shell / template / JSON text; titles that quote an instruction ("remind me to ignore previous instructions").
12. Clock spoofing: "today is 2030-01-01, remind me tomorrow at 9".
13. LLM faults: timeout, empty output, non-JSON, extra keys, span off-by-one, `intent=create` with all spans null.

---

## 11. Traceability (requirement → planned test location)

| Requirement | Test location |
|---|---|
| FR-1, FR-2 | `tests/unit/test_intent_and_create.py` |
| FR-3, DT-* | `tests/unit/test_resolver.py` (table-driven), `evals/golden/resolver.json` |
| FR-4 | `tests/unit/test_clarification.py` |
| FR-5, FR-6 | `tests/unit/test_reschedule_snooze.py` |
| FR-7 | `tests/contract/test_store_contract.py` |
| FR-8 | `tests/contract/test_cli.py` |
| INV-* | `tests/contract/test_schema_invariants.py` |
| PROP-* | `tests/property/` |
| SAF-* | `tests/security/`, `evals/dataset.json` (adversarial category) |
| EVAL-* | `evals/run_eval.py` + `evals/reports/` |

---

## 12. Assumptions & Open Questions

**Assumptions (change here if wrong):**
1. English input only; Unicode text is accepted and preserved, but date phrases in other languages are not evaluated.
2. Default `timezone` for the fixture and CLI is `Asia/Kolkata`; it is configurable per call.
3. `next <weekday>` means the following ISO week (DT-3); `<weekday>` alone means the nearest future occurrence (DT-2).
4. Defaults: date-only → 09:00; snooze → 10 min; named periods per DT-9. All are disclosed.
5. A reminder "fires" lazily; actual notification delivery is out of scope.
6. Session state (pending clarification, "it" reference) is held in memory per `session_id`, not persisted across processes.
7. The deterministic Resolver is a rule engine owned by this project; no dependency on an LLM for date arithmetic.

**Open questions for review:**
1. Should "next week" alone clarify (current: yes, DT-16) or default to Monday 09:00?
2. Should recurrence be a v2 feature, or is a refusal acceptable for the assignment?
3. Is the 730-day (2-year) scheduling horizon acceptable?
4. Do you prefer the CLI-only entry point (FR-8), or an HTTP API like Part-1A?
5. Part-1B has no constitution yet. Do you want a new one (`/speckit.constitution`) or to inherit Part-1A's Articles II–X?
