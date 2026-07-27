#%NASL_MIN_LEVEL 70300
#
# Synthetic fixture - not a real Tenable plugin. Covers the paths test.nasl
# doesn't: the paranoia gate, banner/version detection (ver_compare), CVE/
# xref parsing, and the uppercase-constant form of severity
# (severity:SECURITY_HOLE, as opposed to a direct security_hole() call).
#

if (description)
{
  script_id(90001);
  script_version("1.0");
  script_name(english:"Fixture: Paranoid Banner Check");
  script_family(english:"Web Servers");

  script_cve_id("CVE-2024-90001");
  script_xref(name:"IAVA", value:"2024-A-9001");

  script_set_attribute(attribute:"synopsis", value:
"Fixture synopsis for a paranoid-mode-only banner check.");
  script_set_attribute(attribute:"description", value:"Fixture description.");
  script_set_attribute(attribute:"solution", value:"Fixture solution.");

  script_category(ACT_GATHER_INFO);
  exit(0);
}

include("vcf.inc");

if (report_paranoia < 2) audit(AUDIT_PARANOID);

app_info = vcf::get_app_info(app:"Fixture App");
vcf::check_version_and_report(
  app_info: app_info,
  fix: "2.0.0",
  severity: SECURITY_HOLE
);
