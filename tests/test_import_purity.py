"""
DATA-01 guard — the public ``BeliefStore`` seam must never import ``ladybug``.

A ``ladybug`` import inside ``src/doxastica/protocol.py`` would leak the backend
dialect/topology across the contract boundary. This AST scan makes that leak a build
failure rather than a review note: it parses the module and asserts no ``import`` /
``from ... import`` statement names ``ladybug`` (as its first dotted component). The scan
walks the whole tree, so an import hidden inside a ``TYPE_CHECKING`` block or a function
body is caught too; only docstring/comment prose mentioning ``ladybug`` is (correctly)
ignored, because prose is not an import node.
"""

import ast
import pathlib


def test_protocol_does_not_import_ladybug() -> None:
    """``protocol.py`` must import no ``ladybug`` module (DATA-01)."""
    source = pathlib.Path("src/doxastica/protocol.py").read_text()
    tree = ast.parse(source)

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    offenders = [name for name in imported if name.split(".")[0] == "ladybug"]
    assert not offenders, f"protocol.py must not import ladybug; found: {offenders}"
