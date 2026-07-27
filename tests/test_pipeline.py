# Unit tests for the deterministic half of the pipeline: tools/extract.py
# and tools/search.py. Two synthetic fixtures cover what test.nasl (the
# real plugin, kept as-is) doesn't exercise:
#   - paranoid_banner.nasl: paranoia gate, banner/version detection (vcf::/
#     ver_compare), CVE/xref, and the uppercase-constant severity form
#     (severity:SECURITY_HOLE, vs. a direct security_hole() call).
#   - active_check.nasl: a direct active check (http_send_recv) and the
#     direct-call severity form, plus CWEs.
# The third detection_style branch, "unknown", and the direct-call severity
# form are both already covered by test.nasl's real logic, so nothing new
# is needed for those.

from pathlib import Path

import pytest

import tools.search as search
from tools.extract import extract
from tools.search import plugin_search

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TEST_NASL = Path(__file__).resolve().parent.parent / "test.nasl"


# --- extract() -------------------------------------------------------------


def test_extract_test_nasl():
    data = extract(str(TEST_NASL))
    meta = data["metadata"]
    fp = data["fp_signals"]

    assert meta["script_id"] == "39465"
    assert meta["cwe_ids"][:3] == ["20", "74", "77"]
    assert meta["cve_ids"] == []  # identifies by CWE, not CVE
    # `report_paranoia > 1` widens which OS payloads run - it's not the
    # `report_paranoia < N` gate that skips the check, so must not read as
    # paranoid-only.
    assert fp["paranoid_only"] is False
    # Real active logic is behind torture_cgi_init()/torture_cgis() from an
    # include, invisible to both keyword patterns - must be "unknown", not
    # a guess.
    assert fp["detection_style"] == "unknown"
    assert data["severity"] == "high"  # security_hole(port:port, extra: report)


def test_extract_paranoid_banner_fixture():
    data = extract(str(FIXTURES / "paranoid_banner.nasl"))
    fp = data["fp_signals"]

    assert fp["paranoid_only"] is True
    assert fp["paranoia_threshold"] == 2
    assert fp["detection_style"] == "banner/version"  # vcf::/check_version_and_report
    assert data["severity"] == "high"  # severity:SECURITY_HOLE, no call form
    assert data["metadata"]["cve_ids"] == ["CVE-2024-90001"]
    assert data["metadata"]["xrefs"] == [{"name": "IAVA", "value": "2024-A-9001"}]


def test_extract_active_check_fixture():
    data = extract(str(FIXTURES / "active_check.nasl"))
    fp = data["fp_signals"]

    assert fp["detection_style"] == "active"  # http_send_recv3(...)
    assert data["severity"] == "high"  # security_hole(port:port)
    assert data["metadata"]["cwe_ids"] == ["78", "77"]


# --- plugin_search() --------------------------------------------------------


@pytest.fixture
def plugins_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(search, "PLUGINS_DIR", str(tmp_path))
    return tmp_path


def test_search_hit(plugins_dir):
    (plugins_dir / "p.nasl").write_text("script_id(90001);\n")
    assert plugin_search(90001).endswith("p.nasl")


def test_search_miss(plugins_dir):
    (plugins_dir / "p.nasl").write_text("script_id(1);\n")
    assert plugin_search(99999) is None


def test_search_no_substring_false_positive(plugins_dir):
    # Shares every leading digit with the real ID and mentions it in plain
    # text - the match must be exact ("script_id(90001)", closing paren
    # included), not a loose substring check.
    (plugins_dir / "decoy.nasl").write_text("script_id(900011);\n")
    (plugins_dir / "mentions.nasl").write_text("# see advisory 90001-2024\n")
    assert plugin_search(90001) is None


def test_search_scoped_to_nasl_extension(plugins_dir):
    # A .nbin plugin would look like this to the search: real content, wrong
    # extension. Must miss rather than match - see docs/ARCHITECTURE.md's
    # ".nbin handling".
    (plugins_dir / "compiled.nbin").write_text("script_id(90005);\n")
    assert plugin_search(90005) is None


def test_search_missing_plugins_dir_raises(monkeypatch):
    monkeypatch.setattr(search, "PLUGINS_DIR", None)
    with pytest.raises(RuntimeError, match="PLUGINS_DIR"):
        plugin_search(90001)
