"""
D-02 / DATA-01 / BACK-01 guard — the backend-blind spine must never import ``ladybug``.

A module-level ``ladybug`` import inside the public ``BeliefStore`` seam (``protocol.py``),
the internal ``BackendPort`` seam (``ports.py``), the engine (``core.py``), or the in-memory
oracle (``backends/memory.py``) would leak the backend dialect/topology across a contract
boundary, or chain-load the optional driver into the always-importable spine. All four spine
modules carry the identical "never import ``ladybug`` at any level" contract (D-02), so the
static guard is parameterized over them. The ONLY module that imports ``ladybug`` is
``backends/ladybug.py`` — a module-level import inside the guarded driver boundary, which is NOT
part of the backend-blind spine and is therefore not scanned. Construction is pure DI
(``MemoryCore(InMemoryBackend())`` / ``MemoryCore(LadybugBackend.open(...))``); no spine module
holds a sanctioned function-local ladybug import any more.

This guard inspects **MODULE-LEVEL imports only** — top-level statements plus imports inside a
module-scoped ``if TYPE_CHECKING:`` block — and deliberately IGNORES imports nested inside
function/method bodies (so the scan stays robust against any future function-local import the
contract might permit). The synthetic negative control below proves the scan distinguishes a
module-level ``ladybug`` import (a real violation) from a function-local one.

Two independent proofs of D-02 isolation live here:

1. The static module-level AST scan (catches a top-level OR ``TYPE_CHECKING``-block ``ladybug``
   import — the real violations — while permitting any function-local one).
2. A subprocess that installs a ``sys.meta_path`` finder raising ``ModuleNotFoundError`` for any
   ``ladybug`` import, then imports the driver-free spine and constructs
   ``MemoryCore(InMemoryBackend())`` — proving the spine imports and runs with ladybug genuinely
   blocked. This complements CI base-install Job 1 (Plan 04) where ladybug is truly uninstalled.
"""

import ast
import pathlib
import subprocess
import sys
import textwrap

import pytest


def _is_type_checking_test(test: ast.expr) -> bool:
    """True if ``test`` is a bare ``TYPE_CHECKING`` name or a ``typing.TYPE_CHECKING`` attribute."""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def _module_level_imports(tree: ast.Module) -> list[str]:
    """
    Collect imports at module scope only: top-level + ``TYPE_CHECKING``-block imports.

    Deliberately ignores imports nested inside function/method bodies — a function-local ladybug
    import (were one ever permitted by D-02) must not be seen by the driver-blind scan. Descends
    into module-level ``if TYPE_CHECKING:`` blocks (and their ``else``) but never into
    ``FunctionDef`` / ``AsyncFunctionDef`` / ``ClassDef``.
    """
    nodes: list[ast.stmt] = list(tree.body)
    for stmt in tree.body:
        if isinstance(stmt, ast.If) and _is_type_checking_test(stmt.test):
            nodes += [*stmt.body, *stmt.orelse]

    imported: list[str] = []
    for node in nodes:
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


@pytest.mark.parametrize("module", ["protocol", "ports", "core", "backends/memory"])
def test_seam_does_not_import_ladybug(module: str) -> None:
    """A backend-blind module must carry no MODULE-LEVEL ``ladybug`` import (D-02 / DATA-01)."""
    source = pathlib.Path(f"src/doxastica/{module}.py").read_text()
    tree = ast.parse(source)

    imported = _module_level_imports(tree)
    offenders = [name for name in imported if name.split(".")[0] == "ladybug"]
    assert not offenders, f"{module}.py must not import ladybug at module level; found: {offenders}"


def test_scan_flags_a_module_level_ladybug_import() -> None:
    """
    Negative control: the module-level scan DOES catch a top-level/TYPE_CHECKING ladybug import.

    Proves the scan is not vacuously green — a genuine module-level violation (both a plain
    top-level import and a ``TYPE_CHECKING``-block import) is detected, while a function-local
    import (the sanctioned ``factories`` pattern) is NOT.
    """
    violating = textwrap.dedent(
        """
        from typing import TYPE_CHECKING
        import ladybug
        if TYPE_CHECKING:
            import ladybug as _lb_tc
        def factory():
            import ladybug as _local  # sanctioned function-local (must NOT be flagged)
        """
    )
    imported = _module_level_imports(ast.parse(violating))
    offenders = [name for name in imported if name.split(".")[0] == "ladybug"]
    # The top-level and TYPE_CHECKING imports are caught (2); the function-local one is not.
    assert offenders == ["ladybug", "ladybug"], (
        f"scan must flag top-level + TYPE_CHECKING ladybug imports only; got {offenders}"
    )


def test_driver_free_spine_imports_with_ladybug_blocked() -> None:
    """
    The driver-free spine imports and constructs a core with ladybug BLOCKED (D-02).

    Runs a subprocess that installs a ``sys.meta_path`` finder raising ``ModuleNotFoundError`` for
    any ``ladybug`` import, then imports ``doxastica`` / ``doxastica.core`` /
    ``doxastica.backends.memory`` (the always-importable driver-free spine), constructs
    ``MemoryCore(InMemoryBackend())``, and exits 0 — the independent runtime proof alongside CI
    base-install Job 1 (Plan 04).
    """
    code = textwrap.dedent(
        """
        import sys

        class _BlockLadybug:
            def find_spec(self, name, path=None, target=None):
                if name == "ladybug" or name.startswith("ladybug."):
                    raise ModuleNotFoundError(f"ladybug blocked for D-02 isolation test: {name}")
                return None

        sys.meta_path.insert(0, _BlockLadybug())

        # Defensive: prove the block actually works before testing the spine.
        try:
            import ladybug  # noqa: F401
        except ModuleNotFoundError:
            pass
        else:
            raise SystemExit("ladybug was importable; the block did not take effect")

        import doxastica  # noqa: F401
        import doxastica.core  # noqa: F401
        import doxastica.backends.memory  # noqa: F401
        from doxastica import MemoryCore
        from doxastica.backends.memory import InMemoryBackend

        core = MemoryCore(InMemoryBackend())
        assert core is not None
        """
    )
    result = subprocess.run(  # noqa: S603 (trusted: sys.executable + inline code, no shell)
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"driver-free spine must import + run with ladybug blocked; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
