# Harness log

Each run appends one section: overall verdict, per-check results, and the captured stdout/stderr of every step.

## Run 2026-11-12 16:46:00 UTC — PASS

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
46 files already formatted
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
  "generated_at": "2026-11-12T16:46:02Z"
}
```

stderr:
```text
(empty)
```

#### PASS — pip-audit (dependencies)
- command: `python -m pip_audit --progress-spinner off D:\Bits-Mtech\Assignment-1\Part-1A`
- exit code: 0 · 16.1s

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
162 passed in 1.86s
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
