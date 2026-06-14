"""Basic tests for doxastica."""

import doxastica


def test_import():
    assert hasattr(doxastica, "__all__")
