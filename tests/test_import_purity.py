"""
DATA-01 / BACK-01 guard — the backend-blind seams must never import ``ladybug``.

A ``ladybug`` import inside ``src/doxastica/protocol.py`` (the public ``BeliefStore``
seam) *or* ``src/doxastica/ports.py`` (the internal ``BackendPort`` seam) would leak the
backend dialect/topology across a contract boundary. Both modules carry the identical
"never import ``ladybug``" contract, so the guard is parameterized over both: it parses
each module and asserts no ``import`` / ``from ... import`` statement names ``ladybug``
(as its first dotted component). The scan walks the whole tree, so an import hidden inside
a ``TYPE_CHECKING`` block or a function body is caught too; only docstring/comment prose
mentioning ``ladybug`` is (correctly) ignored, because prose is not an import node.
"""

import ast
import pathlib

import pytest


@pytest.mark.parametrize("module", ["protocol", "ports"])
def test_seam_does_not_import_ladybug(module: str) -> None:
    """The backend-blind seams must import no ``ladybug`` module (DATA-01 / BACK-01)."""
    source = pathlib.Path(f"src/doxastica/{module}.py").read_text()
    tree = ast.parse(source)

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    offenders = [name for name in imported if name.split(".")[0] == "ladybug"]
    assert not offenders, f"{module}.py must not import ladybug; found: {offenders}"
