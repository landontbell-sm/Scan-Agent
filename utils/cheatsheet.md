# NASL cheat sheet

Fed to the LLM pass so it doesn't rely on training data for niche NASL idioms.
See docs/ARCHITECTURE.md "The explanation engine" for why each of these matters.

## 1. Liftable metadata — where ready-made text lives

- `script_name`, `script_id`, `script_cve_id`, `script_xref` — name and references
- `script_set_attribute(attribute:"synopsis"|"description"|"solution"|"risk_factor")`
  — pre-written vuln writeup, fix, and severity

## 2. False-positive signals — the reason this tool exists

- `report_paranoia` / `AUDIT_PARANOID` — runs only in paranoid mode; FP-prone
  (paranoia levels: 0 = avoid FPs, 1 = default, 2 = paranoid)
- other `AUDIT_*` bailouts — reasons a result is soft
- banner (version-compare off a header/KB) = FP-prone; active (payload + response
  match) = reliable. Some plugins spread this logic across includes/library calls
  (e.g. `torture_cgi_command_exec.nasl`'s `unix_flaws`/`win_flaws` arrays via
  `torture_cgi.inc`) — if you can't point to a specific compare or payload+match in
  the source, say so rather than guessing which style it is.

## 3. Match operators / functions — misread if left to training data

- `><` = contains, `>!<` = does not contain
- `=~` = regex match, `!~` = no match
- `egrep` / `ereg` / `eregmatch` = regex search on a string

## 4. Severity + delivery — quick mappings

- `security_hole` → high, `security_warning` → medium, `security_note` → low/info;
  `risk_factor` states it directly. Newer plugins built on `vcf::` helpers pass
  severity as an uppercase constant argument instead (`severity:SECURITY_HOLE`),
  not a direct call — same mapping applies.
- `get_http_port`, `http_get`, `http_keepalive_send_recv`, `http_send_recv3` — web
  check, and how it sends
- `set_kb_item` / `get_kb_item` — state passed between plugins (dependency gating)
