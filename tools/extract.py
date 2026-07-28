import logging
import time

from utils import nasl_patterns as pat

logger = logging.getLogger(__name__)


def extract(path: str) -> dict:
    """Read a .nasl file and return its deterministic facts."""
    started = time.monotonic()
    logger.info("extract started path=%s", path)

    with open(path, "r") as f:
        raw = f.read()

    parts = pat.EXIT_ZERO_RE.split(raw, maxsplit=1)
    header, body = parts if len(parts) == 2 else (raw, raw)

    metadata = parse_metadata(header)
    result = {
        "metadata": metadata,
        "fp_signals": find_fp_signals(body),
        "severity": determine_severity(body, metadata["attributes"]),
        "header": header,
        "body": body,
        "raw": raw,
    }
    logger.info(
        "extract done path=%s script_id=%s severity=%s detection_style=%s duration=%.2fs",
        path,
        metadata["script_id"],
        result["severity"],
        result["fp_signals"]["detection_style"],
        time.monotonic() - started,
    )
    return result

def parse_metadata(header: str) -> dict:
    name = pat.NAME_RE.search(header)
    family = pat.FAMILY_RE.search(header)
    script_id = pat.ID_RE.search(header)
    version = pat.VERSION_RE.search(header)
    cvss_vector = pat.CVSS_VECTOR_RE.search(header)
    category = pat.CATEGORY_RE.search(header)

    cve_ids = []
    for call in pat.CVE_CALL_RE.findall(header):
        cve_ids.extend(pat.unquote(m) for m in pat.CVE_ITEM_RE.findall(call))

    cwe_ids = []
    for call in pat.CWE_CALL_RE.findall(header):
        cwe_ids.extend(pat.CWE_ITEM_RE.findall(call))

    xrefs = [
        {"name": pat.unquote(n), "value": pat.unquote(v)}
        for n, v in pat.XREF_RE.findall(header)
    ]

    attributes = {}
    for m in pat.ATTRIBUTE_RE.finditer(header):
        attributes.setdefault(m.group("name"), []).append(pat.unquote(m.group("value")))

    return {
        "script_name": pat.unquote(name.group(1)) if name else None,
        "script_id": script_id.group(1) if script_id else None,
        "script_version": pat.unquote(version.group(1)) if version else None,
        "family": pat.unquote(family.group(1)) if family else None,
        "category": category.group(1) if category else None,
        "cve_ids": cve_ids,
        "cwe_ids": cwe_ids,
        "xrefs": xrefs,
        "cvss_vector": pat.unquote(cvss_vector.group(1)) if cvss_vector else None,
        "attributes": attributes,
    }

def find_fp_signals(body: str) -> dict:
    paranoia = pat.PARANOIA_RE.search(body)
    is_version_check = bool(pat.VERSION_CHECK_RE.search(body))
    is_active_check = bool(pat.ACTIVE_CHECK_RE.search(body))
    if is_active_check:
        detection_style = "active"
    elif is_version_check:
        detection_style = "banner/version"
    else:
        detection_style = "unknown"

    return {
        "paranoid_only": paranoia is not None,
        "paranoia_threshold": int(paranoia.group(1)) if paranoia else None,
        "audit_bailouts": sorted(set(pat.AUDIT_RE.findall(body))),
        "detection_style": detection_style,
    }

def determine_severity(body: str, attributes: dict) -> str | None:
    tokens = {t for m in pat.SEVERITY_TOKEN_RE.findall(body) for t in m if t}
    if tokens:
        order = ["low", "medium", "high"]
        return max((pat.SEVERITY_FROM_TOKEN[t] for t in tokens), key=order.index)
    risk_factor = attributes.get("risk_factor")
    return risk_factor[0].lower() if risk_factor else None
