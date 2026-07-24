# Regex patterns for the NASL constructs tools/extract.py pulls facts from.
# Grounded against test.nasl (plugin 39465, CGI Generic Command Execution) -
# see the comment on each pattern for what in that file it does/doesn't match.

import re

# NASL string literal, allowing escaped chars (\" etc.) inside it. Plain
# `"(.*?)"` breaks if the text contains an escaped quote; this matches "any
# char that isn't a quote or backslash, OR a backslash followed by anything."
STRING = r'"(?:[^"\\]|\\.)*"'


def unquote(s: str) -> str:
    """Strip the surrounding quotes and un-escape a matched STRING."""
    # DOTALL so a backslash-newline line continuation un-escapes too, not
    # just single-char escapes like \" - `.` otherwise skips newlines.
    return re.sub(r"\\(.)", r"\1", s[1:-1], flags=re.DOTALL)


# script_name(english:"CGI Generic Command Execution");  The language keyword
# isn't always "english" (and older plugins can omit it entirely), so this
# accepts any identifier before the colon, or none at all.
NAME_RE = re.compile(r"script_name\(\s*(?:\w+\s*:\s*)?(" + STRING + r")\s*\)")

# script_family(english:"CGI abuses");  same language-keyword shape as name.
FAMILY_RE = re.compile(r"script_family\(\s*(?:\w+\s*:\s*)?(" + STRING + r")\s*\)")

# script_id(39465);
ID_RE = re.compile(r"script_id\((\d+)\)")

# script_version("1.40");
VERSION_RE = re.compile(r"script_version\(\s*(" + STRING + r")\s*\)")

# script_cve_id("CVE-2020-1234", "CVE-2020-5678");  (call may repeat, and each
# call may list several CVEs). test.nasl has none of these - it identifies by
# CWE instead - so this correctly comes back empty for that file.
CVE_CALL_RE = re.compile(r"script_cve_id\(([^)]*)\)")
CVE_ITEM_RE = re.compile(STRING)

# script_cwe_id(20, 74, 77, 78, 713, ...);  bare integers, not quoted strings.
CWE_CALL_RE = re.compile(r"script_cwe_id\(([^)]*)\)")
CWE_ITEM_RE = re.compile(r"\d+")

# script_xref(name:"IAVA", value:"2020-A-0999");  absent from test.nasl.
XREF_RE = re.compile(
    r"script_xref\(\s*name\s*:\s*(" + STRING + r")\s*,\s*value\s*:\s*(" + STRING + r")\s*\)"
)

# script_set_cvss_base_vector("CVSS2#AV:N/AC:L/Au:N/C:P/I:P/A:P");
CVSS_VECTOR_RE = re.compile(r"script_set_cvss_base_vector\(\s*(" + STRING + r")\s*\)")

# script_category(ACT_ATTACK);  bare constant, not a string - tells you
# whether the plugin is classified as an attack, info-gather, mixed, etc.
CATEGORY_RE = re.compile(r"script_category\(\s*(ACT_[A-Z_]+)\s*\)")

# script_set_attribute(attribute:"synopsis", value:"...");  One pattern
# covers every attribute name (synopsis/description/solution/see_also/...).
# test.nasl calls this with "see_also" twice, so tools/extract.py collects
# these as {name: [value, ...]} rather than {name: value} - a plain dict
# would silently drop the first see_also URL.
ATTRIBUTE_RE = re.compile(
    r'script_set_attribute\(\s*attribute\s*:\s*"(?P<name>[^"]+)"'
    r"\s*,\s*value\s*:\s*(?P<value>" + STRING + r")\s*\)"
)

# audit(AUDIT_PARANOID);  audit(AUDIT_VER_NOT_GRANULAR, ...);  etc. test.nasl
# calls neither - it uses report_paranoia to widen which OS payloads run, not
# to skip the check, so it correctly has no bailouts.
AUDIT_RE = re.compile(r"audit\(\s*(AUDIT_[A-Z0-9_]+)")

# The specific "only runs in paranoid mode" gate: if (report_paranoia < 2) ...
# test.nasl instead has `if (report_paranoia > 1)`, a different comparison
# used for a different purpose, so this must not match it.
PARANOIA_RE = re.compile(r"report_paranoia\s*<\s*(\d+)")

# Two different ways plugins report severity: older plugins call
# security_hole(port) directly; newer ones (e.g. vcf::check_version_and_report)
# pass the severity in as an uppercase constant argument, no call/parens at
# all: `severity:SECURITY_HOLE`. Both need matching or a large share of
# current plugins come back with no severity.
SEVERITY_TOKEN_RE = re.compile(
    r"\b(security_hole|security_warning|security_note)\s*\("
    r"|\b(SECURITY_HOLE|SECURITY_WARNING|SECURITY_NOTE)\b"
)

SEVERITY_FROM_TOKEN = {
    "security_hole": "high",
    "SECURITY_HOLE": "high",
    "security_warning": "medium",
    "SECURITY_WARNING": "medium",
    "security_note": "low",
    "SECURITY_NOTE": "low",
}

# exit(0); marks the end of the description block. Matched as a pattern
# rather than a literal string so `exit( 0 ) ;` (extra spacing) still splits
# correctly instead of silently returning an empty body.
EXIT_ZERO_RE = re.compile(r"exit\s*\(\s*0\s*\)\s*;")

# Detection-style hints (see docs/ARCHITECTURE.md's banner-vs-active
# discriminator). Deliberately narrow: torture_cgi-style active checks that
# go through an include (torture_cgi_init/torture_cgis in test.nasl) won't
# match ACTIVE_CHECK_RE and correctly come back "unknown" rather than being
# guessed - get_kb_item() alone is too generic a signal to call "banner"
# (test.nasl calls it for OS detection, not a version compare).
VERSION_CHECK_RE = re.compile(r"vcf::|check_version|ver_compare")
ACTIVE_CHECK_RE = re.compile(r"http_send_recv|http_keepalive_send_recv|send\s*\(\s*data\s*:")
