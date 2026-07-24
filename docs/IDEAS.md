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
- **Advanced Logging:** Every LLM response also returns rich metadata like input/output tokens and more which
  can be used for cost/usage monitoring. 
- **Cross Refrencing:** The `.nasl` documents contain helpful see also urls which link to docs, we could extract
    those and have the agent web_search those urls to pull the additional context.
- **`.nbin` Support**: Right now we dont.
- **National Vulnerabilities Database Integration:** Build out a custom tool(s) that hook to the NVD api for 
    a more comprehensive overview.
        - **This could also be setup with RAG and embed ALL of the raw plugin files into the rag database.**