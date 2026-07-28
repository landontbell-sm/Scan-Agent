import re
STRING = r'"(?:[^"\\]|\\.)*"'


def unquote(s: str) -> str:
    """Strip the surrounding quotes and un-escape a matched STRING."""
    return re.sub(r"\\(.)", r"\1", s[1:-1], flags=re.DOTALL)


# script_name(english:"CGI Generic Command Execution")
NAME_RE = re.compile(r"script_name\(\s*(?:\w+\s*:\s*)?(" + STRING + r")\s*\)")

# script_family(english:"CGI abuses");  same language-keyword shape as name.
FAMILY_RE = re.compile(r"script_family\(\s*(?:\w+\s*:\s*)?(" + STRING + r")\s*\)")

# script_id(39465);
ID_RE = re.compile(r"script_id\((\d+)\)")

# script_version("1.40");
VERSION_RE = re.compile(r"script_version\(\s*(" + STRING + r")\s*\)")

# script_cve_id("CVE-2020-1234", "CVE-2020-5678")
CVE_CALL_RE = re.compile(r"script_cve_id\(([^)]*)\)")
CVE_ITEM_RE = re.compile(STRING)

# script_cwe_id(20, 74, 77, 78, 713, ...);  bare integers, not quoted strings.
CWE_CALL_RE = re.compile(r"script_cwe_id\(([^)]*)\)")
CWE_ITEM_RE = re.compile(r"\d+")

# script_xref(name:"IAVA", value:"2020-A-0999");  absent from test.nasl.
XREF_RE = re.compile(r"script_xref\(\s*name\s*:\s*(" + STRING + r")\s*,\s*value\s*:\s*(" + STRING + r")\s*\)")

# script_set_cvss_base_vector("CVSS2#AV:N/AC:L/Au:N/C:P/I:P/A:P");
CVSS_VECTOR_RE = re.compile(r"script_set_cvss_base_vector\(\s*(" + STRING + r")\s*\)")

# script_category(ACT_ATTACK);  bare constant, not a string - tells you
# whether the plugin is classified as an attack, info-gather, mixed, etc.
CATEGORY_RE = re.compile(r"script_category\(\s*(ACT_[A-Z_]+)\s*\)")

# script_set_attribute(attribute:"synopsis", value:"...")
ATTRIBUTE_RE = re.compile(
    r'script_set_attribute\(\s*attribute\s*:\s*"(?P<name>[^"]+)"'
    r"\s*,\s*value\s*:\s*(?P<value>" + STRING + r")\s*\)"
)

# audit(AUDIT_PARANOID);  audit(AUDIT_VER_NOT_GRANULAR, ...)
AUDIT_RE = re.compile(r"audit\(\s*(AUDIT_[A-Z0-9_]+)")

# The specific "only runs in paranoid mode" gate
PARANOIA_RE = re.compile(r"report_paranoia\s*<\s*(\d+)")

# Two different ways plugins report severity
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

# exit(0); marks the end of the description block.
EXIT_ZERO_RE = re.compile(r"exit\s*\(\s*0\s*\)\s*;")

# Detection-style hints
VERSION_CHECK_RE = re.compile(r"vcf::|check_version|ver_compare")
ACTIVE_CHECK_RE = re.compile(r"http_send_recv|http_keepalive_send_recv|send\s*\(\s*data\s*:")
