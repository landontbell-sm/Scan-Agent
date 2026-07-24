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

## Current state (early skeleton)

`docs/ARCHITECTURE.md` now tracks the actual file layout (`tools/`, `utils/`) and has
an "Implementation status" table — check that table for what's built vs. stub before
assuming a piece exists. Short version: `tools/search.py` is implemented; `main.py` is
an unrelated `uv init` leftover; everything else in the pipeline (`tools/extract.py`,
`tools/explain.py`, `utils/llm.py`'s `complete()` seam, `utils/cheatsheet.md`,
pipeline orchestration, `app.py`'s actual handler) is still a stub or unwritten.

## Commands

This project uses `uv` (Python >=3.13, see `.python-version`).

```bash
uv sync                        # install dependencies from pyproject.toml / uv.lock
uv run chainlit run app.py -w  # run the Chainlit dev server (auto-reload)
uv run python tools/search.py  # exercise the search/extract stub directly (has a __main__ block)
```

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
- Without `PLUGINS_DIR` set and populated, `tools/search.py` lookups will fail/return
  `None`.

## Architecture (target design, per docs/ARCHITECTURE.md)

The intended flow is a **fixed, linear pipeline**, not a tool-calling agent — there's
no agent loop or MCP server. Exactly one LLM call happens, at the end, after
deterministic extraction has already gathered the facts that must be right:

```
tech types plugin_id → app.py → pipeline orchestration (planned)
  → tools/search.py: ripgrep `script_id(<id>)` over the mirror → file path
  → tools/extract.py: regex-split file into header/body, lift script_name/CVE/
                       synopsis/description/solution/risk_factor, detect FP signals
  → tools/explain.py + utils/llm.py: prompt (extracted dict + cheatsheet.md)
                                       → model → tech_brief
  → app.py sends tech_brief back
```

Key design invariants to preserve when extending this:

- **Deterministic-vs-LLM split is intentional.** Anything mechanically extractable
  from the `.nasl` file (IDs, CVEs, severity, Tenable's own synopsis/solution text,
  `AUDIT_*`/`report_paranoia` false-positive signals) must come from regex extraction
  in `tools/extract.py`, never from the model. The LLM is only trusted for the one part
  that needs real comprehension: what the plugin injects and what response makes it
  fire.
- **Banner-vs-active is the core false-positive discriminator**: a check that
  version-compares a banner/KB value is FP-prone; a check that sends a payload and
  matches the response is reliable. This distinction should surface in every brief.
- **Model access is behind one seam** (`utils/llm.py`'s intended `complete()`
  function) so the provider (Claude vs. Gemini) is swappable and nothing upstream
  depends on which one is active.
- **Require quoted source lines** in the LLM's trigger explanation — this is what
  makes the explanation verifiable by a code-literate tech instead of just trusted.
- **`.nasl` only in v1.** `.nbin` (compiled NASL) has no public decompiler; a lookup
  resolving to `.nbin` (or no match) should return a clear "not supported" response
  rather than a guess (see `docs/ARCHITECTURE.md` "`.nbin` handling" for the deferred
  v2 approach).
- **No verdicts, no auto-resolution, no agent-executed commands.** Even the v2
  "validation command" feature is explanation output for the tech to run manually,
  never something the agent executes itself.
