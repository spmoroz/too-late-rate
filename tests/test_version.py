"""The version string must be identical in the package, CITATION.cff and .zenodo.json."""

import json
import re
from pathlib import Path

import pytest

import too_late_rate

ROOT = Path(__file__).resolve().parents[1]


def _cff_version():
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    m = re.search(r"^version:\s*\"?([^\"\s]+)\"?\s*$", text, re.M)
    return m.group(1) if m else None


def test_version_consistent_across_files():
    cff = ROOT / "CITATION.cff"
    zen = ROOT / ".zenodo.json"
    if not (cff.exists() and zen.exists()):  # e.g. running from an installed wheel
        pytest.skip("metadata files not available")
    v = too_late_rate.__version__
    assert _cff_version() == v
    assert json.loads(zen.read_text(encoding="utf-8"))["version"] == v
    init = (ROOT / "src" / "too_late_rate" / "__init__.py").read_text(encoding="utf-8")
    assert f'__version__ = "{v}"' in init
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{v}]" in changelog
