# Scan Tech Assistant

Look up a Nessus plugin and get a plain-language explanation of why it fired —
built for the moment you're on a call with a customer and need an answer fast.

**How to use it:** type a plugin ID (the number off the report page) and send it.
The assistant will:

1. Locate the plugin's source on the mirror
2. Pull out its CVEs, severity, and false-positive signals
3. Read the trigger logic and explain — in plain language, anchored to quoted
   source lines — what it checks, what response makes it fire, and why it might
   have failed

**What this is not:** a triage engine. It won't render a verdict on whether a
finding is a true or false positive, and it won't run anything against a host.
You stay the human in the loop — this just gets you to an answer faster than
reading the `.nasl` file by hand.

`.nbin` (compiled) plugins aren't supported yet — you'll get a clear
"not supported" message instead of a guess.
