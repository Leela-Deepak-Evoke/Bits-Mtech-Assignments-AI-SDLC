# Harness log

Each run appends one section: overall verdict, per-check results, and the captured stdout/stderr of every step.

## Run 2026-11-12 16:50:33 UTC — PASS

Python 3.13.13 on Windows 11

| Check | Result |
|---|---|
| LINT | PASS |
| SECURITY | PASS |
| TESTS | PASS |

### LINT

#### PASS — syntax (compileall)
- command: `python -m compileall -q src tests .harness`
- exit code: 0 · 0.1s

stdout:
```text
(empty)
```

stderr:
```text
(empty)
```

#### PASS — ruff check
- command: `python -m ruff check src tests .harness`
- exit code: 0 · 0.1s

stdout:
```text
All checks passed!
```

stderr:
```text
(empty)
```

#### PASS — ruff format --check
- command: `python -m ruff format --check src tests .harness`
- exit code: 0 · 0.1s

stdout:
```text
47 files already formatted
```

stderr:
```text
(empty)
```

#### PASS — mypy --strict
- command: `python -m mypy`
- exit code: 0 · 0.3s

stdout:
```text
Success: no issues found in 32 source files
```

stderr:
```text
(empty)
```

### SECURITY

#### PASS — bandit (medium+)
- command: `python -m bandit -r src -ll -q`
- exit code: 0 · 0.3s

stdout:
```text
(empty)
```

stderr:
```text
(empty)
```

#### PASS — forbidden constructs (AST)
- command: `scan src for eval/exec/pickle/shell=True/os.system/yaml.load`
- exit code: 0 · 0.0s

stdout:
```text
no problems found
```

stderr:
```text
(empty)
```

#### PASS — detect-secrets
- command: `python -m detect_secrets scan --all-files src tests pyproject.toml .harness`
- exit code: 0 · 0.9s

stdout:
```text
{
  "version": "1.5.0",
  "plugins_used": [
    {
      "name": "ArtifactoryDetector"
    },
    {
      "name": "AWSKeyDetector"
    },
    {
      "name": "AzureStorageKeyDetector"
    },
    {
      "name": "Base64HighEntropyString",
      "limit": 4.5
    },
    {
      "name": "BasicAuthDetector"
    },
    {
      "name": "CloudantDetector"
    },
    {
      "name": "DiscordBotTokenDetector"
    },
    {
      "name": "GitHubTokenDetector"
    },
    {
      "name": "GitLabTokenDetector"
    },
    {
      "name": "HexHighEntropyString",
      "limit": 3.0
    },
    {
      "name": "IbmCloudIamDetector"
    },
    {
      "name": "IbmCosHmacDetector"
    },
    {
      "name": "IPPublicDetector"
    },
    {
      "name": "JwtTokenDetector"
    },
    {
      "name": "KeywordDetector",
      "keyword_exclude": ""
    },
    {
      "name": "MailchimpDetector"
    },
    {
      "name": "NpmDetector"
    },
    {
      "name": "OpenAIDetector"
    },
    {
      "name": "PrivateKeyDetector"
    },
    {
      "name": "PypiTokenDetector"
    },
    {
      "name": "SendGridDetector"
    },
    {
      "name": "SlackDetector"
    },
    {
      "name": "SoftlayerDetector"
    },
    {
      "name": "SquareOAuthDetector"
    },
    {
      "name": "StripeDetector"
    },
    {
      "name": "TelegramBotTokenDetector"
    },
    {
      "name": "TwilioKeyDetector"
    }
  ],
  "filters_used": [
    {
      "path": "detect_secrets.filters.allowlist.is_line_allowlisted"
    },
    {
      "path": "detect_secrets.filters.common.is_ignored_due_to_verification_policies",
      "min_level": 2
    },
    {
      "path": "detect_secrets.filters.heuristic.is_indirect_reference"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_likely_id_string"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_lock_file"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_not_alphanumeric_string"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_potential_uuid"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_prefixed_with_dollar_sign"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_sequential_string"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_swagger_file"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_templated_secret"
    }
  ],
  "results": {},
  "generated_at": "2026-11-12T16:50:35Z"
}
```

stderr:
```text
(empty)
```

#### PASS — pip-audit (dependencies)
- command: `python -m pip_audit --progress-spinner off D:\Bits-Mtech\Assignment-1\Part-1A`
- exit code: 0 · 11.0s

stdout:
```text
(empty)
```

stderr:
```text
No known vulnerabilities found
```

### TESTS

#### PASS — pytest (unit, integration, contract, architecture) + coverage
- command: `python -m pytest tests -q -p no:cacheprovider --cov --cov-report=term-missing:skip-covered`
- exit code: 0 · 2.5s

stdout:
```text
........................................................................ [ 44%]
........................................................................ [ 88%]
..................                                                       [100%]
=============================== tests coverage ================================
______________ coverage: platform win32, python 3.13.13-final-0 _______________

Name                                         Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------------------------
src\todo\domain\rules.py                       110      6     56      7    92%   45, 57, 70, 98->103, 111, 113, 156
src\todo\infrastructure\file_io.py              37      3      6      2    88%   19-20, 24->exit, 29
src\todo\infrastructure\json_repository.py      39      4      4      1    88%   48-49, 52-53
src\todo\infrastructure\serialization.py        47      6     18      4    85%   27, 30-31, 36, 40, 76
src\todo\interfaces\api\__main__.py              3      3      2      0     0%   3-6
src\todo\interfaces\api\app.py                  53      4      2      0    93%   85-86, 91-92
src\todo\interfaces\api\errors.py               38      3      6      1    91%   49, 70-71
src\todo\interfaces\cli\errors.py                8      1      4      1    83%   28
src\todo\interfaces\cli\main.py                118     14     38      9    83%   59, 77, 150, 152, 154, 156, 160, 224, 228, 233-237
----------------------------------------------------------------------------------------
TOTAL                                          736     44    166     25    92%

23 files skipped due to complete coverage.
Required test coverage of 90.0% reached. Total coverage: 91.69%
162 passed in 1.89s
```

stderr:
```text
(empty)
```

#### PASS — AC traceability (informational)
- command: `match spec AC ids against test names`
- exit code: 0 · 0.0s

stdout:
```text
AC traceability: 72/76 acceptance criteria referenced by tests
not yet referenced: AC-2.4, AC-7.4, AC-12.1, AC-12.2
```

stderr:
```text
(empty)
```

---

## Appendix A — Rule outcomes

| Gate | Rule / tool configuration (from `pyproject.toml`) | Outcome |
|---|---|---|
| Syntax | `python -m compileall -q src tests .harness` | PASS |
| Lint | ruff rule sets `E F W I N UP B C4 C90 SIM PL RUF S D ANN PT T20`; max complexity 10; google docstrings; ignores `D203 D213 D107` | PASS — 0 findings |
| Format | `ruff format --check` | PASS — 0 files to reformat |
| Types | `mypy --strict` over `src` | PASS — 0 issues in 32 source files |
| Security: static | `bandit -r src -ll` (medium and above) | PASS — 0 findings |
| Security: constructs | AST ban on `eval`, `exec`, `pickle`, `marshal`, `shelve`, `shell=True`, `os.system`, `yaml.load` | PASS — 0 hits |
| Security: secrets | `detect-secrets scan --all-files` | PASS — 0 findings |
| Security: dependencies | `pip-audit` on the project's declared dependencies | PASS — no known vulnerabilities |
| Tests | pytest, all suites under `tests/` | PASS — 162/162 |
| Coverage | branch coverage, `fail_under = 90` | PASS — see Appendix B |
| Traceability | spec ACs referenced by test names (informational) | 72/76; unreferenced: AC-2.4, AC-7.4, AC-12.1, AC-12.2 |

## Appendix B — Test results by suite

| Suite | Tests | Passed | Failed |
|---|---|---|---|
| architecture | 5 | 5 | 0 |
| contract | 42 | 42 | 0 |
| integration | 16 | 16 | 0 |
| unit | 99 | 99 | 0 |
| **Total** | **162** | **162** | **0** |

Per-test results (`python -m pytest tests -v`, verbatim):

```text
============================= test session starts =============================
platform win32 -- Python 3.13.13, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\lsublari\AppData\Local\Programs\Python\Python313\python.exe
rootdir: d:\Bits-Mtech\Assignment-1\Part-1A
configfile: pyproject.toml
plugins: anyio-4.15.1, platformdirs-4.14.5, cov-7.1.0
collecting ... collected 162 items

tests/architecture/test_layers.py::test_domain_is_pure PASSED            [  0%]
tests/architecture/test_layers.py::test_services_depend_only_on_domain_and_ports PASSED [  1%]
tests/architecture/test_layers.py::test_interfaces_never_import_infrastructure PASSED [  1%]
tests/architecture/test_layers.py::test_no_direct_clock_calls_in_domain_or_services PASSED [  2%]
tests/architecture/test_layers.py::test_business_rules_are_not_defined_in_interfaces PASSED [  3%]
tests/contract/test_api.py::test_ac_11_1_crud_status_codes PASSED        [  3%]
tests/contract/test_api.py::test_ac_11_5_repeated_tag_params_and_sorting PASSED [  4%]
tests/contract/test_api.py::test_ac_11_2_error_statuses_and_body_shape PASSED [  4%]
tests/contract/test_api.py::test_ac_11_3_next_route_is_not_parsed_as_id PASSED [  5%]
tests/contract/test_api.py::test_ac_11_4_non_integer_id_is_422 PASSED    [  6%]
tests/contract/test_api.py::test_ac_11_6_malformed_json_is_422_not_500 PASSED [  6%]
tests/contract/test_api.py::test_ac_1_10_system_fields_rejected_on_create[id] PASSED [  7%]
tests/contract/test_api.py::test_ac_1_10_system_fields_rejected_on_create[status] PASSED [  8%]
tests/contract/test_api.py::test_ac_1_10_system_fields_rejected_on_create[created_at] PASSED [  8%]
tests/contract/test_api.py::test_ac_1_10_system_fields_rejected_on_create[updated_at] PASSED [  9%]
tests/contract/test_api.py::test_ac_1_10_system_fields_rejected_on_create[completed_at] PASSED [  9%]
tests/contract/test_api.py::test_ac_3_3_null_due_date_clears PASSED      [ 10%]
tests/contract/test_api.py::test_ac_11_7_api_key_required_when_configured PASSED [ 11%]
tests/contract/test_api.py::test_ac_11_8_default_host_is_localhost PASSED [ 11%]
tests/contract/test_api.py::test_storage_errors_do_not_leak_internals PASSED [ 12%]
tests/contract/test_cli.py::test_ac_10_1_every_command_has_help[add] PASSED [ 12%]
tests/contract/test_cli.py::test_ac_10_1_every_command_has_help[list] PASSED [ 13%]
tests/contract/test_cli.py::test_ac_10_1_every_command_has_help[show] PASSED [ 14%]
tests/contract/test_cli.py::test_ac_10_1_every_command_has_help[update] PASSED [ 14%]
tests/contract/test_cli.py::test_ac_10_1_every_command_has_help[delete] PASSED [ 15%]
tests/contract/test_cli.py::test_ac_10_1_every_command_has_help[start] PASSED [ 16%]
tests/contract/test_cli.py::test_ac_10_1_every_command_has_help[complete] PASSED [ 16%]
tests/contract/test_cli.py::test_ac_10_1_every_command_has_help[reopen] PASSED [ 17%]
tests/contract/test_cli.py::test_ac_10_1_every_command_has_help[next] PASSED [ 17%]
tests/contract/test_cli.py::test_ac_10_2_add_json PASSED                 [ 18%]
tests/contract/test_cli.py::test_ac_10_3_list_json_empty_and_populated PASSED [ 19%]
tests/contract/test_cli.py::test_ac_10_6_human_list_has_one_line_per_task PASSED [ 19%]
tests/contract/test_cli.py::test_cli_tag_filter_and_priority_sort PASSED [ 20%]
tests/contract/test_cli.py::test_ac_6_7_shortcuts_and_exit_codes PASSED  [ 20%]
tests/contract/test_cli.py::test_ac_10_4_and_10_5_exit_codes_and_stderr[args0-2] PASSED [ 21%]
tests/contract/test_cli.py::test_ac_10_4_and_10_5_exit_codes_and_stderr[args1-2] PASSED [ 22%]
tests/contract/test_cli.py::test_ac_10_4_and_10_5_exit_codes_and_stderr[args2-2] PASSED [ 22%]
tests/contract/test_cli.py::test_ac_10_4_and_10_5_exit_codes_and_stderr[args3-2] PASSED [ 23%]
tests/contract/test_cli.py::test_ac_10_4_and_10_5_exit_codes_and_stderr[args4-2] PASSED [ 24%]
tests/contract/test_cli.py::test_ac_10_4_and_10_5_exit_codes_and_stderr[args5-3] PASSED [ 24%]
tests/contract/test_cli.py::test_ac_10_4_and_10_5_exit_codes_and_stderr[args6-3] PASSED [ 25%]
tests/contract/test_cli.py::test_ac_10_4_and_10_5_exit_codes_and_stderr[args7-2] PASSED [ 25%]
tests/contract/test_cli.py::test_ac_3_3_update_and_clear_due PASSED      [ 26%]
tests/contract/test_cli.py::test_ac_4_4_delete_requires_yes PASSED       [ 27%]
tests/contract/test_cli.py::test_ac_8_3_next_with_nothing_is_not_an_error PASSED [ 27%]
tests/contract/test_cli.py::test_ac_9_6_corrupt_file_warns_on_stderr PASSED [ 28%]
tests/contract/test_cli.py::test_nfr_5_unicode_round_trip PASSED         [ 29%]
tests/integration/test_json_persistence.py::test_ac_9_2_missing_file_means_empty_store_and_no_file_created PASSED [ 29%]
tests/integration/test_json_persistence.py::test_ac_9_1_data_visible_to_a_new_instance PASSED [ 30%]
tests/integration/test_json_persistence.py::test_ac_9_2_parent_directory_created_on_first_write PASSED [ 30%]
tests/integration/test_json_persistence.py::test_ac_9_4_file_format PASSED [ 31%]
tests/integration/test_json_persistence.py::test_ac_9_5_next_id_survives_restart PASSED [ 32%]
tests/integration/test_json_persistence.py::test_ac_9_6_corrupt_file_is_quarantined_not_deleted[] PASSED [ 32%]
tests/integration/test_json_persistence.py::test_ac_9_6_corrupt_file_is_quarantined_not_deleted[{not json] PASSED [ 33%]
tests/integration/test_json_persistence.py::test_ac_9_6_corrupt_file_is_quarantined_not_deleted[{"version": 1}] PASSED [ 33%]
tests/integration/test_json_persistence.py::test_ac_9_6_corrupt_file_is_quarantined_not_deleted[{"version": 1, "next_id": 1, "tasks": [{"id": 1}]}] PASSED [ 34%]
tests/integration/test_json_persistence.py::test_ac_9_6_corrupt_file_is_quarantined_not_deleted[\xff\xfe] PASSED [ 35%]
tests/integration/test_json_persistence.py::test_ac_9_7_newer_version_fails_and_file_untouched PASSED [ 35%]
tests/integration/test_json_persistence.py::test_ac_9_3_failed_write_leaves_original_intact PASSED [ 36%]
tests/integration/test_json_persistence.py::test_transient_permission_error_is_retried PASSED [ 37%]
tests/integration/test_json_persistence.py::test_ac_9_8_unwritable_location_is_a_storage_error PASSED [ 37%]
tests/integration/test_json_persistence.py::test_ac_9_9_failed_mutations_do_not_modify_the_file PASSED [ 38%]
tests/integration/test_json_persistence.py::test_serialization_round_trip_and_validation PASSED [ 38%]
tests/unit/test_query_and_next.py::test_ac_5_1_single_tag PASSED         [ 39%]
tests/unit/test_query_and_next.py::test_ac_5_2_multiple_tags_match_all PASSED [ 40%]
tests/unit/test_query_and_next.py::test_ac_5_3_multiple_tags_match_any PASSED [ 40%]
tests/unit/test_query_and_next.py::test_ac_5_4_tag_filter_is_case_insensitive PASSED [ 41%]
tests/unit/test_query_and_next.py::test_ac_5_5_unknown_tag_returns_empty PASSED [ 41%]
tests/unit/test_query_and_next.py::test_ac_5_6_status_filter_and_invalid_status PASSED [ 42%]
tests/unit/test_query_and_next.py::test_ac_5_7_filters_combine_with_and PASSED [ 43%]
tests/unit/test_query_and_next.py::test_ac_5_8_overdue_filter PASSED     [ 43%]
tests/unit/test_query_and_next.py::test_ac_5_9_invalid_match_rejected PASSED [ 44%]
tests/unit/test_query_and_next.py::test_ac_7_1_default_is_priority_descending PASSED [ 45%]
tests/unit/test_query_and_next.py::test_ac_7_2_priority_ascending PASSED [ 45%]
tests/unit/test_query_and_next.py::test_ac_7_3_due_date_sort_puts_missing_last_in_both_orders PASSED [ 46%]
tests/unit/test_query_and_next.py::test_ac_7_5_invalid_sort_or_order_rejected PASSED [ 46%]
tests/unit/test_query_and_next.py::test_ac_7_6_sort_is_deterministic_with_id_tiebreak PASSED [ 47%]
tests/unit/test_query_and_next.py::test_created_at_and_id_sorting PASSED [ 48%]
tests/unit/test_query_and_next.py::test_ac_8_1_overdue_beats_higher_priority PASSED [ 48%]
tests/unit/test_query_and_next.py::test_ac_8_2_two_overdue_higher_priority_wins PASSED [ 49%]
tests/unit/test_query_and_next.py::test_ac_8_3_nothing_actionable PASSED [ 50%]
tests/unit/test_query_and_next.py::test_ac_8_4_in_progress_beats_pending_when_otherwise_equal PASSED [ 50%]
tests/unit/test_task_service.py::test_ac_1_1_and_1_9_add_assigns_incrementing_ids PASSED [ 51%]
tests/unit/test_task_service.py::test_ac_1_2_invalid_add_stores_nothing PASSED [ 51%]
tests/unit/test_task_service.py::test_ac_2_1_get_includes_computed_overdue PASSED [ 52%]
tests/unit/test_task_service.py::test_ac_2_2_get_unknown_id_not_found PASSED [ 53%]
tests/unit/test_task_service.py::test_ac_2_3_list_on_empty_store PASSED  [ 53%]
tests/unit/test_task_service.py::test_ac_3_1_update_bumps_updated_at PASSED [ 54%]
tests/unit/test_task_service.py::test_ac_3_4_failed_update_does_not_save PASSED [ 54%]
tests/unit/test_task_service.py::test_ac_3_6_update_unknown_id PASSED    [ 55%]
tests/unit/test_task_service.py::test_ac_4_1_and_4_2_delete PASSED       [ 56%]
tests/unit/test_task_service.py::test_ac_4_3_ids_are_never_reused PASSED [ 56%]
tests/unit/test_task_service.py::test_ac_6_status_changes_persist_and_invalid_ones_do_not_save PASSED [ 57%]
tests/unit/test_task_service.py::test_ac_6_6_status_change_unknown_id PASSED [ 58%]
tests/unit/test_task_service.py::test_list_filters_then_sorts PASSED     [ 58%]
tests/unit/test_task_service.py::test_ac_8_3_next_task_none_when_empty PASSED [ 59%]
tests/unit/test_task_service.py::test_next_task_returns_view PASSED      [ 59%]
tests/unit/test_task_validation.py::test_ac_1_2_empty_or_blank_title_rejected[] PASSED [ 60%]
tests/unit/test_task_validation.py::test_ac_1_2_empty_or_blank_title_rejected[   ] PASSED [ 61%]
tests/unit/test_task_validation.py::test_ac_1_2_empty_or_blank_title_rejected[\t\n] PASSED [ 61%]
tests/unit/test_task_validation.py::test_ac_1_3_title_length_boundary PASSED [ 62%]
tests/unit/test_task_validation.py::test_ac_1_4_title_is_trimmed PASSED  [ 62%]
tests/unit/test_task_validation.py::test_nfr_5_unicode_title_preserved[caf\xe9 \u2705] PASSED [ 63%]
tests/unit/test_task_validation.py::test_nfr_5_unicode_title_preserved[\u65e5\u672c\u8a9e] PASSED [ 64%]
tests/unit/test_task_validation.py::test_ac_1_5_tags_lowercased_trimmed_deduplicated PASSED [ 64%]
tests/unit/test_task_validation.py::test_ac_1_6_tag_count_boundary PASSED [ 65%]
tests/unit/test_task_validation.py::test_ac_1_6_tag_length_boundary PASSED [ 66%]
tests/unit/test_task_validation.py::test_ac_1_6_invalid_tag_characters_rejected[a b] PASSED [ 66%]
tests/unit/test_task_validation.py::test_ac_1_6_invalid_tag_characters_rejected[#x] PASSED [ 67%]
tests/unit/test_task_validation.py::test_ac_1_6_invalid_tag_characters_rejected[] PASSED [ 67%]
tests/unit/test_task_validation.py::test_ac_1_6_invalid_tag_characters_rejected[-lead] PASSED [ 68%]
tests/unit/test_task_validation.py::test_ac_1_6_invalid_tag_characters_rejected[\xe9moji] PASSED [ 69%]
tests/unit/test_task_validation.py::test_tags_must_be_a_list_not_a_string PASSED [ 69%]
tests/unit/test_task_validation.py::test_ac_1_7_invalid_priority_rejected[urgent] PASSED [ 70%]
tests/unit/test_task_validation.py::test_ac_1_7_invalid_priority_rejected[] PASSED [ 70%]
tests/unit/test_task_validation.py::test_ac_1_7_invalid_priority_rejected[None] PASSED [ 71%]
tests/unit/test_task_validation.py::test_ac_1_7_invalid_priority_rejected[3] PASSED [ 72%]
tests/unit/test_task_validation.py::test_priority_parsing_is_case_insensitive PASSED [ 72%]
tests/unit/test_task_validation.py::test_ac_1_8_invalid_due_date_rejected[2026-02-30] PASSED [ 73%]
tests/unit/test_task_validation.py::test_ac_1_8_invalid_due_date_rejected[12/11/2026] PASSED [ 74%]
tests/unit/test_task_validation.py::test_ac_1_8_invalid_due_date_rejected[20261112] PASSED [ 74%]
tests/unit/test_task_validation.py::test_ac_1_8_invalid_due_date_rejected[2026-1-1] PASSED [ 75%]
tests/unit/test_task_validation.py::test_ac_1_8_invalid_due_date_rejected[tomorrow] PASSED [ 75%]
tests/unit/test_task_validation.py::test_ac_1_8_past_and_far_future_due_dates_accepted[2020-01-01] PASSED [ 76%]
tests/unit/test_task_validation.py::test_ac_1_8_past_and_far_future_due_dates_accepted[9999-12-31] PASSED [ 77%]
tests/unit/test_task_validation.py::test_description_length_boundary PASSED [ 77%]
tests/unit/test_task_validation.py::test_ac_1_1_build_task_defaults PASSED [ 78%]
tests/unit/test_task_validation.py::test_ac_1_9_build_task_uses_given_id PASSED [ 79%]
tests/unit/test_task_validation.py::test_ac_1_10_system_fields_rejected_on_create[id] PASSED [ 79%]
tests/unit/test_task_validation.py::test_ac_1_10_system_fields_rejected_on_create[status] PASSED [ 80%]
tests/unit/test_task_validation.py::test_ac_1_10_system_fields_rejected_on_create[created_at] PASSED [ 80%]
tests/unit/test_task_validation.py::test_ac_1_10_system_fields_rejected_on_create[updated_at] PASSED [ 81%]
tests/unit/test_task_validation.py::test_ac_1_10_system_fields_rejected_on_create[completed_at] PASSED [ 82%]
tests/unit/test_task_validation.py::test_title_is_required PASSED        [ 82%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_1_and_6_2_full_transition_matrix[pending-pending] PASSED [ 83%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_1_and_6_2_full_transition_matrix[pending-in_progress] PASSED [ 83%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_1_and_6_2_full_transition_matrix[pending-completed] PASSED [ 84%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_1_and_6_2_full_transition_matrix[in_progress-pending] PASSED [ 85%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_1_and_6_2_full_transition_matrix[in_progress-in_progress] PASSED [ 85%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_1_and_6_2_full_transition_matrix[in_progress-completed] PASSED [ 86%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_1_and_6_2_full_transition_matrix[completed-pending] PASSED [ 87%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_1_and_6_2_full_transition_matrix[completed-in_progress] PASSED [ 87%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_1_and_6_2_full_transition_matrix[completed-completed] PASSED [ 88%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_3_completing_sets_completed_at PASSED [ 88%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_4_reopening_clears_completed_at PASSED [ 89%]
tests/unit/test_transitions_update_overdue.py::test_ac_6_5_unknown_status_is_validation_not_transition_error PASSED [ 90%]
tests/unit/test_transitions_update_overdue.py::test_failed_transition_leaves_task_unchanged PASSED [ 90%]
tests/unit/test_transitions_update_overdue.py::test_ac_5_8_overdue_rules[due0-pending-True] PASSED [ 91%]
tests/unit/test_transitions_update_overdue.py::test_ac_5_8_overdue_rules[due1-in_progress-True] PASSED [ 91%]
tests/unit/test_transitions_update_overdue.py::test_ac_5_8_overdue_rules[due2-pending-False] PASSED [ 92%]
tests/unit/test_transitions_update_overdue.py::test_ac_5_8_overdue_rules[due3-pending-False] PASSED [ 93%]
tests/unit/test_transitions_update_overdue.py::test_ac_5_8_overdue_rules[due4-completed-False] PASSED [ 93%]
tests/unit/test_transitions_update_overdue.py::test_ac_5_8_overdue_rules[None-pending-False] PASSED [ 94%]
tests/unit/test_transitions_update_overdue.py::test_ac_3_1_partial_update_changes_only_given_fields PASSED [ 95%]
tests/unit/test_transitions_update_overdue.py::test_ac_3_2_tags_replaced_and_cleared PASSED [ 95%]
tests/unit/test_transitions_update_overdue.py::test_ac_3_3_due_date_can_be_cleared PASSED [ 96%]
tests/unit/test_transitions_update_overdue.py::test_ac_3_4_invalid_update_leaves_original_unchanged PASSED [ 96%]
tests/unit/test_transitions_update_overdue.py::test_ac_3_5_empty_update_rejected PASSED [ 97%]
tests/unit/test_transitions_update_overdue.py::test_ac_3_7_immutable_fields_rejected[status] PASSED [ 98%]
tests/unit/test_transitions_update_overdue.py::test_ac_3_7_immutable_fields_rejected[id] PASSED [ 98%]
tests/unit/test_transitions_update_overdue.py::test_ac_3_7_immutable_fields_rejected[created_at] PASSED [ 99%]
tests/unit/test_transitions_update_overdue.py::test_updated_at_moves_forward_by_clock PASSED [100%]

============================= 162 passed in 1.26s =============================
```

## Appendix C — Self-healing record (repair log)

| Item | Value |
|---|---|
| Failures observed in this run | 0 lint, 0 security, 0 test |
| Repair attempts | 0 |
| Code changed by the repair loop | None |
| Re-run after repair | Not applicable: the first run was already green |

The repair loop was **not triggered** because nothing failed. No failure was manufactured to exercise it. The harness was shown to detect failures earlier in this session by planting an unused import, an `eval()` call and a failing test: all three checks went FAIL (exit code 1), and after the scratch files were removed the harness returned to PASS. That fault drill was logged to a throwaway file and is not part of this record. Earlier lint findings from the first generation (23 ruff findings) were fixed before this run; the before/after is in `evidence/README.md`, and the raw pre-fix code is in `evidence/initial-generation/`.

Note: the request refers to "Section 3.7". No section with that number exists in `constitution.md`, `spec.md`, `plan.md` or `tasks.md`; the repair-logging requirement used here is Constitution Article VII (self-healing harness: log every run and repair). If Section 3.7 comes from an external assignment document, map this appendix to it.

## Appendix D — Formal decision record

| Field | Value |
|---|---|
| Subject | Smart Todo & Task CLI/API, initial implementation (Part-1A) |
| Evidence reviewed | This log (harness run above, Appendices A to C), `evidence/initial-generation/`, `evidence/README.md` |
| Harness verdict | PASS (lint PASS, security PASS, tests PASS) |
| Known gaps at decision time | Self-healing loop, anti-cheat guards and locked baseline not built; security, performance and parity tests (T058 to T063) not written; constitution amendment T001 not applied (it still names SQLite); AC-2.4, AC-7.4, AC-12.1, AC-12.2 have no referencing test |
| **Decision** | **ACCEPT** |
| Basis | Recorded at the instruction of the project owner in the working session on 2026-11-12, following a fully green harness run. Not an independent review. |
| Reviewer name | ____________________ |
| Reviewer signature / date | ____________________ |

The reviewer name and signature are intentionally blank: a named person must fill them in. Until then this record documents the decision as instructed, not a signed approval.
