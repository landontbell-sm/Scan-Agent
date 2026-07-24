# AI Scan Assistant

A research assistant for scan technicians. A tech types in a Nessus **plugin ID**
and the agent does the manual lookup legwork read the plugin, figure out what it
checks, what it does/runs, why it fired, why it might have failed, and whether it's
the kind of check that tends to false-positive and hands back a plain-language
explanation the tech can give the customer.

This is built for the moment a tech is **on the phone with a customer** asking
"what is this finding and what do I do about it, if anything?" Today that means opening the
Tenable plugin page, finding the plugin, cross-referencing vulners/CVE data, and
reading the test code by hand. This tool collapses that into one lookup.

## What it is / isn't

- **It is** a lookup + explanation tool. Input a plugin ID, get an explanation.
- **It is not** a triage engine. There are **no verdicts, no routing, and no
  auto-resolution**. Findings like these usually aren't "resolved" they're
  explained to the customer. The tech is always the human in the loop, by design.
- **It is read-only.** It reads and explains plugin logic. Replicating a finding
  stays a manual step a tech performs, but the agent should provide everythig they need
  to replicate/test the findings.

## Input / output

**Input:** `plugin_id` (the only required input the tech reads it off the report
page mid-call).

**Output:** A brief for the scan tech so they can understand it and explain/validate it:

- **`tech_brief`** fast, technical: what the plugin checks, false-positive
  analysis, source quality, and information about the scan and why it may have failed.

## How it works (high level)

The agent is thin; the value is in the tool layer.

1. Look up the plugin by ID and read its source from a **local mirror** of the
   Nessus plugins directory (`/opt/nessus/lib/nessus/plugins/`). There are over 300k
2. A **deterministic pass** extracts the facts from the `.nasl` plugin file name, CVEs,
   severity, false-positive signals, and more and lifts Tenable's own pre-written
   description and solution text.
3. An **LLM pass** reads the trigger logic what the plugin injects, what
   response makes it fire, what are the command(s) ran, and why it might have failed
   anchored to quoted source lines, and rewrites the description into a customer-ready script.

## Scope decisions for v1

- **`plugin_id` is the only input.** No scan ID, no Nessus API integration. The one
  thing a scan would add is the per-host result (the exact banner/string Nessus
  matched), but the tech can already see that on the report page so it isn't worth
  a scan integration, especially since the Nessus product/edition in use isn't
  confirmed yet.
- **Self-contained on the plugins mirror + NVD.** No live scanner connection in v1.
- **RipGrep instead of Grep** to improve plugin search speed. (Grep: 30+ seconds, RipGrep: 0-5 seconds)
  - `sudo apt install ripgrep`

## Future Development for v2

- **Allow more inputs:** Allow the scan tech to upload more information about the client and
  their environment. Basically be able to input all of the information they see on Gravity.
    - Such as the clients website, or relevant information about the host(s)/environments(s)
- **Produce Validation Commands:** Gather the information and injection from plugins and scan tech
  and use it to create validation commands (curl, grep, nmap, ect) that the scan tech can run themselves
  to validate the plugin findings and reproduce the Nessus scan in order to determine what
  caused the scan to be flagged. This should never be ran by the agent, the agent should output 
  a validation command(s) along with a command explination/reasoning for each so the scan tech knows
  what the command is, why they should run it, what it does and possible impacts, and what they are looking for.
    - We might run into issues where the LLM wont generate a validation command due to security reasons.


## Deployment

- Hosted in an **isolated sandbox**, inbound access restricted to the
  internal network / VPN, effectively acting as access contro. Plugins 
  are currently stored in `plugins.tar.gz` and should be extracted and installed in the Sandbox
- Chainlit UX: Very basic and straight forward UX which is similar to ChatGPT, Claude, Gemini, ect
  to reduce adoption friction and make it easy to use and understand.  
    - Seperate from the existing internal scan interface to allow for faster integration.
- Model is interchangeable (Claude or Gemini) — the tool layer is decoupled from it.
  - We shoudlnt be reliant on just one model/model provider to prevent vendor lock-in.
    - We also need to be able to evaluate the performace/effectiveness of different
      models, model providers, and prompts to detect drift or degregation.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full design, tool contracts, the
explanation engine internals, the NASL cheat sheet, and the rationale behind each
decision.

## Environment

- **Scanner:** standalone **Nessus Professional** (on the Tenable Core appliance),
  not Security Center — so plugin data comes from the local mirror, not a REST API.
- **Plugin directory:** `/opt/nessus/lib/nessus/plugins/` ~ there are 309,377 files 
  in this directory so the grep search takes a while.
- **Lookup method:** grep for `script_id(<plugin_id>)` in that directory (the same
  method techs use manually).
- **Mirror:** The plugins directory needs to be installed in the Sandbox.
  There are two ways that we can do this:
    - 1. Automate the install of a free offline version of Nessus and install plugins with Nessus command
    - 2. *Probably Easier*: Uncompress the `plugins.tar.gz` archive into the correct plugins directory
        - Manually Downloaded: 7/23/2026
