"""Architecture rules, checked by parsing imports (Constitution Art. II)."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "todo"
FRAMEWORKS = {"typer", "fastapi", "pydantic", "uvicorn", "starlette"}
PROJECT_LAYERS = {"services", "repositories", "infrastructure", "interfaces", "app"}


def imports_of(package: str) -> set[str]:
    found: set[str] = set()
    for file in (SRC / package).rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)
    return found


def top_levels(modules: set[str], prefix: str = "todo.") -> set[str]:
    return {m[len(prefix):].split(".")[0] for m in modules if m.startswith(prefix)}


def test_domain_is_pure() -> None:
    modules = imports_of("domain")
    assert top_levels(modules) - {"domain"} == set()
    assert {m.split(".")[0] for m in modules} & FRAMEWORKS == set()


def test_services_depend_only_on_domain_and_ports() -> None:
    assert top_levels(imports_of("services")) <= {"domain", "repositories", "services"}


def test_interfaces_never_import_infrastructure() -> None:
    assert "infrastructure" not in top_levels(imports_of("interfaces"))


def test_no_direct_clock_calls_in_domain_or_services() -> None:
    banned = ("datetime.now", "date.today", "utcnow", "time.time")
    for package in ("domain", "services"):
        for file in (SRC / package).rglob("*.py"):
            source = file.read_text(encoding="utf-8")
            assert not any(token in source for token in banned), file


def test_business_rules_are_not_defined_in_interfaces() -> None:
    forbidden = {"filter_tasks", "sort_tasks", "transition", "build_task", "apply_update"}
    for file in (SRC / "interfaces").rglob("*.py"):
        defined = {
            node.name
            for node in ast.walk(ast.parse(file.read_text(encoding="utf-8")))
            if isinstance(node, ast.FunctionDef)
        }
        assert not defined & forbidden, file
