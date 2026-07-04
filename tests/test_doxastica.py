"""Basic tests for doxastica."""

import doxastica


def test_import() -> None:
    assert hasattr(doxastica, "__all__")
