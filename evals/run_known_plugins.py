"""Golden-set eval for the pipeline - see docs/ARCHITECTURE.md's "Open
questions / next steps" (evals/known_plugins/).

Deterministic extraction is already covered by tests/test_pipeline.py; this
script exists for the part unit tests can't grade: does tools/explain.py's
LLM pass stay honest, model to model and prompt change to prompt change?
The one automatable invariant is the system prompt's "quote source lines
verbatim" instruction - so this script extracts anything in the model's
output that looks like a quoted source excerpt and flags it if it doesn't
appear verbatim in the plugin body. Everything else about brief quality
(is the summary actually plain-language, is the FP call right) needs a
human reading the printed output - this is a fixture-refresh/drift check,
not a pass/fail gate.

Usage:
    uv run python -m evals.run_known_plugins          # deterministic facts only
    uv run python -m evals.run_known_plugins --llm     # + one real model call per case

Cases reuse the fixtures tests/test_pipeline.py already exercises rather
than a separate plugins/ directory - one less thing to keep in sync. The
".nbin -> not supported" case isn't here: it's a property of
tools/search.py's *.nasl scoping, already covered by
test_search_scoped_to_nasl_extension in tests/test_pipeline.py.
"""

import argparse
import asyncio
import re
from pathlib import Path

from tools.explain import explain_plugin
from tools.extract import extract

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"

CASES = [
    {
        "name": "torture_cgi_command_exec (real plugin 39465)",
        "path": REPO_ROOT / "test.nasl",
        "expect": {"detection_style": "unknown", "severity": "high", "paranoid_only": False},
    },
    {
        "name": "paranoid + banner/version check (fixture)",
        "path": FIXTURES / "paranoid_banner.nasl",
        "expect": {"detection_style": "banner/version", "severity": "high", "paranoid_only": True},
    },
    {
        "name": "active injection check (fixture)",
        "path": FIXTURES / "active_check.nasl",
        "expect": {"detection_style": "active", "severity": "high", "paranoid_only": False},
    },
]

# Separate regexes per delimiter type, each finding its own open/close pairs
# independently. A single [`"]...[`"] pattern looks tempting but is wrong:
# when a genuine short quote (e.g. `"uid="`) fails the length filter below,
# its closing delimiter gets reinterpreted as the *opening* delimiter of the
# next match, silently swallowing everything in between as a bogus "quote".
_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_DQUOTE_RE = re.compile(r'"([^"\n]+)"')


def unverified_quotes(text: str, source: str) -> list[str]:
    """Anything the model quoted (backtick- or "-delimited, 6+ chars) that
    doesn't appear verbatim in the plugin body it was given - a likely
    invented payload or match condition.
    """
    spans = _BACKTICK_RE.findall(text) + _DQUOTE_RE.findall(text)
    return [q for q in spans if len(q) >= 6 and q not in source]


def check_deterministic(case: dict, data: dict) -> list[str]:
    problems = []
    for field, expected in case["expect"].items():
        actual = data["fp_signals"].get(field, data.get(field))
        if actual != expected:
            problems.append(f"{field}: expected {expected!r}, got {actual!r}")
    return problems


async def check_llm(case: dict, data: dict) -> list[str]:
    brief = await explain_plugin(data)
    print(f"    summary: {brief.summary}")
    print(f"    detection_reliability: {brief.detection_reliability}")
    print(f"    fp_analysis: {brief.fp_analysis}")

    bad = unverified_quotes(brief.summary, data["body"]) + unverified_quotes(
        brief.fp_analysis, data["body"]
    )
    return [f"quoted but not found in source: {q!r}" for q in bad]


async def main(run_llm: bool) -> int:
    failures = 0
    for case in CASES:
        print(f"\n=== {case['name']} ===")
        data = extract(str(case["path"]))

        problems = check_deterministic(case, data)
        if run_llm:
            problems += await check_llm(case, data)

        if problems:
            failures += 1
            for p in problems:
                print(f"  FAIL: {p}")
        else:
            print("  ok")

    print(f"\n{len(CASES) - failures}/{len(CASES)} cases clean")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--llm", action="store_true", help="also run tools/explain.py's LLM pass (costs a real API call per case)"
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(run_llm=args.llm)))
