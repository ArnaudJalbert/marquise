"""Architecture guard for use case input and output types.

Every use case declares its own ``InputData`` and ``OutputData`` as nested
classes, and no use case imports another use case's types. A use case may
still import another use case class to call it as an injected collaborator.

``ALLOWLIST`` holds the violations that existed when the guard was added.
Each fix removes its own entry; the test fails on new and stale entries.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

APPLICATION_DIR = (
    Path(__file__).resolve().parents[3] / "src" / "marquise" / "application"
)
USE_CASE_PACKAGES = ("use_cases", "queries")

ALLOWLIST = {
    "use_cases/create_screenings.py: CreateScreeningsCommand contract uses "
    "module-level ImportedScreeningData",
    "use_cases/create_missing_movies.py: imports EnrichMovieInputData from "
    "shared use case module marquise.application.movie_workflows",
    "use_cases/create_missing_movies.py: imports MatchMovieInputData from "
    "shared use case module marquise.application.movie_workflows",
    "use_cases/enrich_movie.py: imports EnrichMovieInputData from shared use case "
    "module marquise.application.movie_workflows",
    "use_cases/enrich_movie.py: imports EnrichMovieOutputData from shared use "
    "case module marquise.application.movie_workflows",
    "use_cases/enrich_movie.py: EnrichMovieUseCase has no nested InputData",
    "use_cases/enrich_movie.py: EnrichMovieUseCase has no nested OutputData",
    "use_cases/import_screenings.py: imports ImportedScreeningData from "
    "use case module marquise.application.use_cases.create_screenings",
    "use_cases/match_movie.py: MatchMovieUseCase has no nested InputData",
    "use_cases/match_movie.py: MatchMovieUseCase has no nested OutputData",
    "use_cases/match_movie.py: imports MatchMovieInputData from shared use case "
    "module marquise.application.movie_workflows",
    "use_cases/match_movie.py: imports MatchMovieOutputData from shared use case "
    "module marquise.application.movie_workflows",
    "use_cases/merge_movies.py: MergeMoviesUseCase has no nested InputData",
    "use_cases/merge_movies.py: MergeMoviesUseCase has no nested OutputData",
    "use_cases/merge_movies.py: imports MatchMovieInputData from shared use case "
    "module marquise.application.movie_workflows",
    "use_cases/merge_movies.py: imports MergeMoviesInputData from shared use "
    "case module marquise.application.movie_workflows",
    "use_cases/merge_movies.py: imports MergeMoviesOutputData from shared use "
    "case module marquise.application.movie_workflows",
    "use_cases/refresh_movies.py: RefreshMoviesUseCase has no nested InputData",
    "use_cases/refresh_movies.py: RefreshMoviesUseCase has no nested OutputData",
    "use_cases/refresh_movies.py: imports EnrichMovieInputData from shared use case "
    "module marquise.application.movie_workflows",
    "use_cases/refresh_movies.py: imports EnrichMovieOutputData from shared use "
    "case module marquise.application.movie_workflows",
    "use_cases/refresh_movies.py: imports RefreshMoviesInputData from shared use "
    "case module marquise.application.movie_workflows",
    "use_cases/refresh_movies.py: imports RefreshMoviesOutputData from shared use "
    "case module marquise.application.movie_workflows",
    "use_cases/refresh_movies.py: imports _enrich from use case module "
    "marquise.application.use_cases.enrich_movie",
    "use_cases/write_screening.py: WriteScreeningUseCase contract uses "
    "CreateScreeningUseCase.InputData",
    "use_cases/write_screening.py: WriteScreeningUseCase contract uses "
    "DeleteScreeningUseCase.InputData",
    "use_cases/write_screening.py: WriteScreeningUseCase contract uses "
    "UpdateScreeningUseCase.InputData",
    "use_cases/write_screening.py: WriteScreeningUseCase contract uses "
    "module-level ScreeningWriteContext",
    "use_cases/write_screening.py: WriteScreeningUseCase has no nested OutputData",
}


def _use_case_modules(root: Path) -> dict[str, tuple[str, ast.Module]]:
    """Map each use case module name to its relative path and AST."""
    modules: dict[str, tuple[str, ast.Module]] = {}
    for package in USE_CASE_PACKAGES:
        for path in sorted((root / package).rglob("*.py")):
            if path.name == "__init__.py":
                continue
            rel = path.relative_to(root)
            name = "marquise.application." + ".".join(rel.with_suffix("").parts)
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            modules[name] = (rel.as_posix(), tree)
    return modules


def _use_case_classes(tree: ast.Module) -> list[ast.ClassDef]:
    """Return top-level classes that define an ``execute`` method."""
    return [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(
            isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
            and item.name == "execute"
            for item in node.body
        )
    ]


def _contract_annotations(cls: ast.ClassDef) -> list[ast.expr]:
    """Collect nested contract fields and execute signature annotations."""
    annotations: list[ast.expr] = []
    for item in cls.body:
        if isinstance(item, ast.ClassDef):
            annotations += [
                node.annotation for node in item.body if isinstance(node, ast.AnnAssign)
            ]
            annotations += _contract_annotations(item)
        elif (
            isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
            and item.name == "execute"
        ):
            annotations += [
                arg.annotation
                for arg in [
                    *item.args.posonlyargs,
                    *item.args.args,
                    *item.args.kwonlyargs,
                ]
                if arg.arg != "self" and arg.annotation is not None
            ]
            if item.returns is not None:
                annotations.append(item.returns)
    return annotations


def _resolve_import_module(rel: str, node: ast.ImportFrom) -> str | None:
    """Resolve an absolute or relative import from a scanned module."""
    if node.level == 0:
        return node.module
    module_parts = ["marquise", "application", *Path(rel).with_suffix("").parts]
    package_parts = module_parts[:-1]
    package_parts = package_parts[: len(package_parts) - node.level + 1]
    if node.module:
        package_parts.extend(node.module.split("."))
    return ".".join(package_parts)


def _annotation_nodes(annotation: ast.expr) -> list[ast.AST]:
    """Include names inside quoted forward references in annotation scans."""
    nodes = list(ast.walk(annotation))
    for node in nodes.copy():
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            nodes.extend(_annotation_nodes(ast.parse(node.value, mode="eval").body))
    return nodes


def _uses_nested_type(
    annotation: ast.expr | None, cls: ast.ClassDef, name: str
) -> bool:
    """Return whether an annotation names this use case's nested type."""
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        annotation = ast.parse(annotation.value, mode="eval").body
    return (
        isinstance(annotation, ast.Name)
        and annotation.id == name
        or (
            isinstance(annotation, ast.Attribute)
            and annotation.attr == name
            and isinstance(annotation.value, ast.Name)
            and annotation.value.id == cls.name
        )
    )


def find_violations(root: Path) -> set[str]:
    """Scan use case modules under an application root for contract drift.

    Args:
        root: Directory containing the ``use_cases`` and ``queries`` packages.

    Returns:
        One human-readable description per violation.
    """
    modules = _use_case_modules(root)
    use_case_names = {
        name: {cls.name for cls in _use_case_classes(tree)}
        for name, (_, tree) in modules.items()
    }
    all_use_case_names = set().union(*use_case_names.values())
    violations: set[str] = set()
    for rel, tree in modules.values():
        module_classes = {
            node.name for node in tree.body if isinstance(node, ast.ClassDef)
        }
        foreign_use_cases: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(
                        alias.name.startswith(f"marquise.application.{package}.")
                        for package in USE_CASE_PACKAGES
                    ):
                        violations.add(f"{rel}: imports use case module {alias.name}")
                continue
            if not isinstance(node, ast.ImportFrom):
                continue
            module = _resolve_import_module(rel, node)
            if module is None:
                continue
            is_use_case_module = module in modules or module in {
                f"marquise.application.{package}" for package in USE_CASE_PACKAGES
            }
            for alias in node.names:
                if is_use_case_module and alias.name in use_case_names.get(
                    module, all_use_case_names
                ):
                    foreign_use_cases.add(alias.asname or alias.name)
                elif is_use_case_module:
                    violations.add(
                        f"{rel}: imports {alias.name} from use case module {module}"
                    )
                elif module.endswith(".movie_workflows") and alias.name.endswith(
                    ("InputData", "OutputData")
                ):
                    violations.add(
                        f"{rel}: imports {alias.name} from shared use case module "
                        f"{module}"
                    )
        for cls in _use_case_classes(tree):
            nested = {item.name for item in cls.body if isinstance(item, ast.ClassDef)}
            execute = next(
                item
                for item in cls.body
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
                and item.name == "execute"
            )
            for kind in ("InputData", "OutputData"):
                if kind not in nested:
                    violations.add(f"{rel}: {cls.name} has no nested {kind}")
            if "InputData" in nested and not any(
                arg.arg != "self"
                and _uses_nested_type(arg.annotation, cls, "InputData")
                for arg in [
                    *execute.args.posonlyargs,
                    *execute.args.args,
                    *execute.args.kwonlyargs,
                ]
            ):
                violations.add(
                    f"{rel}: {cls.name} execute does not use its nested InputData"
                )
            if "OutputData" in nested and not _uses_nested_type(
                execute.returns, cls, "OutputData"
            ):
                violations.add(
                    f"{rel}: {cls.name} execute does not use its nested OutputData"
                )
            for annotation in _contract_annotations(cls):
                for node in _annotation_nodes(annotation):
                    if (
                        isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name)
                        and node.value.id in foreign_use_cases
                    ):
                        violations.add(
                            f"{rel}: {cls.name} contract uses "
                            f"{node.value.id}.{node.attr}"
                        )
                    elif (
                        isinstance(node, ast.Name)
                        and node.id in module_classes
                        and node.id != cls.name
                    ):
                        violations.add(
                            f"{rel}: {cls.name} contract uses module-level {node.id}"
                        )
    return violations


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


def test_use_case_violations_match_allowlist() -> None:
    """Scenario: scanning the real application yields exactly the allowlist.

    A new violation fails the test. A fixed violation still in the allowlist
    also fails, so each fix must remove its entry.
    """
    violations = find_violations(APPLICATION_DIR)
    assert sorted(violations - ALLOWLIST) == [], "New use case type violations"
    assert sorted(ALLOWLIST - violations) == [], "Stale allowlist entries"


def test_guard_flags_shared_and_cross_use_case_types(tmp_path: Path) -> None:
    """Scenario: a use case with outside and borrowed types is reported."""
    use_cases = tmp_path / "use_cases"
    use_cases.mkdir()
    (use_cases / "first.py").write_text(
        textwrap.dedent("""\
            from dataclasses import dataclass

            @dataclass
            class Row:
                value: str

            class FirstUseCase:
                class InputData:
                    rows: list[str]

                class OutputData:
                    pass

                async def execute(self, input_data: Row) -> OutputData: ...
            """),
        encoding="utf-8",
    )
    (use_cases / "_second.py").write_text(
        textwrap.dedent("""\
            from dataclasses import dataclass
            from marquise.application.use_cases.first import (
                FirstUseCase,
                Row as ImportedRow,
            )

            @dataclass
            class Row:
                value: str

            class SecondUseCase:
                class InputData:
                    inner: list["FirstUseCase.InputData"]

                class OutputData:
                    value: str

                async def execute(self, input_data: "Row") -> "Row": ...
            """),
        encoding="utf-8",
    )
    (use_cases / "third.py").write_text(
        textwrap.dedent("""\
            from marquise.application.movie_workflows import SharedInputData
            """),
        encoding="utf-8",
    )
    (use_cases / "fourth.py").write_text(
        textwrap.dedent("""\
            from marquise.application.use_cases import FirstUseCase, SharedData
            """),
        encoding="utf-8",
    )
    (use_cases / "fifth.py").write_text(
        textwrap.dedent("""\
            import marquise.application.use_cases.first as first
            """),
        encoding="utf-8",
    )

    assert find_violations(tmp_path) == {
        "use_cases/first.py: FirstUseCase contract uses module-level Row",
        "use_cases/first.py: FirstUseCase execute does not use its nested InputData",
        "use_cases/fifth.py: imports use case module "
        "marquise.application.use_cases.first",
        "use_cases/fourth.py: imports SharedData from use case module "
        "marquise.application.use_cases",
        "use_cases/_second.py: imports Row from use case module "
        "marquise.application.use_cases.first",
        "use_cases/_second.py: SecondUseCase contract uses FirstUseCase.InputData",
        "use_cases/_second.py: SecondUseCase contract uses module-level Row",
        "use_cases/_second.py: SecondUseCase execute does not use its nested InputData",
        "use_cases/_second.py: SecondUseCase execute does not use its nested OutputData",
        "use_cases/third.py: imports SharedInputData from shared use case module "
        "marquise.application.movie_workflows",
    }


def test_guard_allows_nested_types_and_collaborator_calls(tmp_path: Path) -> None:
    """Scenario: nested types and calling another use case are not reported."""
    use_cases = tmp_path / "use_cases"
    use_cases.mkdir()
    (use_cases / "first.py").write_text(
        textwrap.dedent("""\
            class FirstUseCase:
                class InputData:
                    value: str

                class OutputData:
                    class Row:
                        value: str

                    rows: list[Row]

                async def execute(self, input_data: InputData) -> OutputData: ...
            """),
        encoding="utf-8",
    )
    (use_cases / "second.py").write_text(
        textwrap.dedent("""\
            from marquise.application.use_cases.first import FirstUseCase

            class SecondUseCase:
                class InputData:
                    value: str

                class OutputData:
                    count: int

                def __init__(self, first: FirstUseCase) -> None:
                    self.first = first

                async def execute(
                    self, input_data: "SecondUseCase.InputData"
                ) -> "SecondUseCase.OutputData":
                    await self.first.execute(FirstUseCase.InputData(value="x"))
            """),
        encoding="utf-8",
    )

    assert find_violations(tmp_path) == set()
