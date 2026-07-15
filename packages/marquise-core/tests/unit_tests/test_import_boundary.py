"""Import boundary enforcement test.

Uses AST scanning to verify that Python files under ``apps/`` never import
from ``marquise`` private internals.  The import-linter contract in
``pyproject.toml`` provides the same enforcement for full packages.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
APPS_DIR = REPO_ROOT / "apps"

FORBIDDEN_PREFIXES = (
    "marquise.domain",
    "marquise.application",
    "marquise.interface_adapters",
    "marquise.infrastructure",
)


def _extract_imports_from_file(filepath: Path) -> list[str]:
    """Extract all imported module names from a Python file using AST."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _scan_directory_for_forbidden_imports(directory: Path) -> list[str]:
    """Scan .py files under directory for forbidden marquise imports.

    Args:
        directory: The directory to scan (e.g. apps/).

    Returns:
        A list of human-readable violation descriptions.
    """
    details: list[str] = []
    for py_file in directory.rglob("*.py"):
        rel = py_file.relative_to(directory)
        imports = _extract_imports_from_file(py_file)
        for mod in imports:
            if any(
                mod == prefix or mod.startswith(prefix + ".")
                for prefix in FORBIDDEN_PREFIXES
            ):
                details.append(f"  {rel}: imports '{mod}'")
                break
    return details


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


def test_apps_has_no_forbidden_imports() -> None:
    """Verify no file under apps/ imports from marquise private internals."""
    details = _scan_directory_for_forbidden_imports(APPS_DIR)
    assert not details, "Forbidden imports found in apps/:\n" + "\n".join(details)


def test_import_linter_contract_is_configured() -> None:
    """Verify the import-linter contract exists in pyproject.toml."""
    config = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "apps-use-public-surface-only" in config
    assert "forbidden_modules" in config


def test_scanner_catches_forbidden_import(tmp_path: Path) -> None:
    """Verify the AST scanner catches a deliberate deep import."""
    violating_dir = tmp_path / "apps"
    violating_dir.mkdir()
    (violating_dir / "bad_app.py").write_text(
        textwrap.dedent("""\
            from marquise.infrastructure.di.container import Container
        """)
    )

    details = _scan_directory_for_forbidden_imports(violating_dir)
    assert len(details) > 0, "Expected scanner to catch the forbidden import"
    assert any("bad_app.py" in d for d in details)
    assert any("marquise.infrastructure" in d for d in details)


def test_scanner_allows_public_surface_imports(tmp_path: Path) -> None:
    """Verify imports from the public marquise surface are NOT flagged."""
    clean_dir = tmp_path / "apps"
    clean_dir.mkdir()
    (clean_dir / "good_app.py").write_text(
        textwrap.dedent("""\
            from marquise import MarquiseFactory, create_factory
            from marquise import CinemaController
        """)
    )

    details = _scan_directory_for_forbidden_imports(clean_dir)
    assert not details, f"Public surface imports should be allowed, but got: {details}"
