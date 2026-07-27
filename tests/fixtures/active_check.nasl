#%NASL_MIN_LEVEL 70300
#
# Synthetic fixture - not a real Tenable plugin. Exercises a direct active
# check (payload sent, response matched) and the direct security_hole(port)
# call form of severity, as opposed to test.nasl's real active logic which
# is hidden behind an include and correctly resolves to "unknown".
#

if (description)
{
  script_id(90003);
  script_version("1.0");
  script_name(english:"Fixture: Active Payload Injection Check");
  script_family(english:"CGI abuses");

  script_cwe_id(78, 77);

  script_set_attribute(attribute:"synopsis", value:
"Fixture synopsis for a confirmed active check.");
  script_set_attribute(attribute:"description", value:
"Fixture description of an injected payload and a matched response.");
  script_set_attribute(attribute:"solution", value:"Sanitize input.");

  script_category(ACT_ATTACK);
  exit(0);
}

include("http.inc");

port = get_http_port(default:80);
payload = "/fixture.cgi?cmd=;id";
res = http_send_recv3(method:"GET", item:payload, port:port);

if (res && "uid=" >< res[2])
{
  security_hole(port:port);
}
