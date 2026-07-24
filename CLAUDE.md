# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Chainlit web app for scan technicians at SecurityMetrics. A tech types in a Nessus
**plugin ID** (`.nasl` script) and the tool looks up the plugin source on a local
mirror, deterministically extracts its metadata and false-positive signals, and uses
an LLM to explain the trigger logic — producing a plain-language `tech_brief` the
tech can read on a live customer call.

It is explicitly a **lookup + explanation tool, not a triage engine**: no verdicts,
no auto-resolution, no agent-run commands. Read-only by design. See `README.md` for
the product framing and `docs/ARCHITECTURE.md` for the full pipeline design, tool
contracts, the NASL cheat sheet content, and the rationale table — read
`docs/ARCHITECTURE.md` before making structural changes, since most design decisions
there were deliberate trade-offs, not defaults.

## Current state (v1 pipeline complete end to end)

`docs/ARCHITECTURE.md` tracks the actual file layout (`tools/`, `utils/`) and has an
"Implementation status" table. Short version: `search → extract → explain` is fully
wired — `app.py` calls all three in sequence (orchestration inline, no `pipeline.py`)
and sends back the model's real tech brief, not a placeholder. `main.py` is an
unrelated `uv init` leftover; `utils/build_index.py` is an optional, unused
alternative lookup strategy. What's actually left is process, not code: no
`evals/known_plugins/` eval set yet (see ARCHITECTURE.md "Open questions").

`test.nasl` at the repo root is a real plugin (39465, `torture_cgi_command_exec.nasl`
from the mirror) kept as a dev fixture — `tools/extract.py`'s `__main__` block runs
against it by default, and it's the file every extraction pattern was grounded against.
It's the reason the regex work is trustworthy without needing the full mirror checked
out locally.

## Commands

This project uses `uv` (Python >=3.13, see `.python-version`).

```bash
uv sync                          # install dependencies from pyproject.toml / uv.lock
uv run chainlit run app.py -w    # run the Chainlit dev server (auto-reload)
uv run python -m tools.extract   # run extract() against test.nasl and pprint the result
uv run python -m tools.search 39465  # ripgrep the mirror for a plugin ID (needs PLUGINS_DIR)
```

Run these with `-m` (not a bare script path) — `tools/extract.py` imports
`utils.nasl_patterns`, a sibling package, which only resolves when Python treats the
repo root as the import root. `python tools/extract.py` puts `tools/` itself on
`sys.path` instead and the import fails.

There is no test suite, lint config, or CI configured yet.

ripgrep is a required system dependency for plugin lookup speed (plain `grep` over the
~309k-file mirror takes 30+ seconds; ripgrep takes 0–5s):

```bash
sudo apt install ripgrep
```

## Environment / data dependencies

- Config comes from a git-ignored `.env` (see `.gitignore` — dotfiles, `*.nasl`,
  `*.tar.gz`, and `*.license` are all excluded from version control). Key variables:
  `PLUGINS_DIR`, `ANTHROPIC_API_KEY`, plus Nessus-related keys not yet consumed by code.
- `PLUGINS_DIR` must point at a local directory of `.nasl` files. Production is the
  full Nessus mirror (`/opt/nessus/lib/nessus/plugins/`, ~309k files, ~1GB compressed
  as `plugins.tar.gz`) but that's deliberately **not** in this repo (too large to
  version, and provisioning it is a deployment concern, not a build-time one — see
  `docs/ARCHITECTURE.md` "Plugins mirror"). For local dev, `PLUGINS_DIR` just needs to
  point at a handful of sample `.nasl` files, not the full mirror.
- If `PLUGINS_DIR` is unset, `tools/search.py`'s `plugin_search()` raises `RuntimeError`
  rather than returning `None` — `None` is reserved for "ripgrep ran and genuinely found
  no matching plugin," which must stay distinguishable from a broken environment.

## Architecture (per docs/ARCHITECTURE.md)

This is a **fixed, linear pipeline**, not a tool-calling agent — there's no agent
loop or MCP server. Exactly one LLM call happens, at the end, after deterministic
extraction has already gathered the facts that must be right:

```
tech types plugin_id → app.py's on_message
  → tools/search.py: ripgrep `script_id(<id>)` over the mirror → file path
      (id → path only; anything past that is extract.py's job)
  → tools/extract.py: regex-split file into header/body (patterns from
                       utils/nasl_patterns.py), lift script_name/CVE/CWE/xrefs/
                       synopsis/description/solution/risk_factor, detect FP signals
  → tools/explain.py: build_prompt() (extracted dict + utils/cheatsheet.md)
                       → utils/llm.py's respond() → tech_brief text
  → app.py sends the tech_brief back
```

Key design invariants to preserve when extending this:

- **One job per file.** `tools/search.py` only turns a plugin ID into a file path.
  Everything about reading *that* file's content belongs in `tools/extract.py`
  (patterns in `utils/nasl_patterns.py`) — don't let header/body-splitting or
  metadata regex creep back into `search.py`; that duplication is what made the two
  files drift out of sync before.
- **Deterministic-vs-LLM split is intentional.** Anything mechanically extractable
  from the `.nasl` file (IDs, CVEs, severity, Tenable's own synopsis/solution text,
  `AUDIT_*`/`report_paranoia` false-positive signals) must come from regex extraction
  in `tools/extract.py`, never from the model. The LLM is only trusted for the one part
  that needs real comprehension: what the plugin injects and what response makes it
  fire.
- **Banner-vs-active is a best-effort deterministic signal, not a guaranteed one.**
  `tools/extract.py`'s `detection_style` keyword-matches `ver_compare`/`vcf::` (banner)
  vs. `http_send_recv*`/`send(data:...)` (active), but active checks that delegate
  through an include (e.g. `torture_cgi_command_exec.nasl` via `torture_cgi.inc`) match
  neither and correctly come back `"unknown"`. Don't "fix" that by widening the
  keywords — a broader match (e.g. matching on `get_kb_item` alone) produces false
  positives on real files (see `test.nasl`, which calls `get_kb_item` for OS detection,
  not a version compare). Leave the ambiguous cases for the LLM pass to actually read.
- **Severity has two call shapes.** Older plugins call `security_hole(port)` directly;
  `vcf::`-based plugins pass severity as an uppercase constant argument instead
  (`severity:SECURITY_HOLE`, no call/parens) — both must be matched, and the
  `risk_factor` attribute is the fallback when neither appears in the body.
- **Model access is behind one seam** (`utils/llm.py`'s `respond(prompt)` function,
  currently Claude via `client.messages.create`, model defaulting to
  `claude-sonnet-5` and overridable with `ANTHROPIC_LLM_MODEL`) so the provider is
  swappable and nothing upstream depends on which one is active.
- **Check `stop_reason` for `"refusal"` before reading the response.** This app's
  entire job is explaining injection/exploit payloads, which is exactly the content
  a model's safety classifiers can decline — `utils/llm.py` raises a `RuntimeError`
  on refusal rather than silently returning an empty string. Don't remove this check
  when touching `respond()`.
- **Require quoted source lines** in the LLM's trigger explanation — this is what
  makes the explanation verifiable by a code-literate tech instead of just trusted.
- **`.nasl` only in v1.** `.nbin` (compiled NASL) has no public decompiler; a lookup
  resolving to `.nbin` (or no match) should return a clear "not supported" response
  rather than a guess (see `docs/ARCHITECTURE.md` "`.nbin` handling" for the deferred
  v2 approach).
- **No verdicts, no auto-resolution, no agent-executed commands.** Even the v2
  "validation command" feature is explanation output for the tech to run manually,
  never something the agent executes itself.
