---
name: strix
description: Run autonomous AI penetration testing against a codebase or running app using the strix-agent CLI, which performs real dynamic attacks (SQLi, XSS, auth bypass, IDOR, SSRF, business-logic flaws) in an isolated sandbox and reports validated, actionable findings. Use when the user asks for a security review, penetration test, vulnerability scan, or authorized red-team exercise against their own application.
---

# Strix

`strix-agent` (PyPI, by usestrix) is an open-source autonomous AI pentesting agent. Unlike static analysis, it dynamically exploits a running target in a sandbox and only reports findings it actually validated.

## Install & run

```bash
pip install strix-agent

# Pick an LLM backend and provide its API key, e.g.:
export STRIX_LLM=anthropic/claude-sonnet-5
export ANTHROPIC_API_KEY=...

strix -m "Pentest ./ and report exploitable vulnerabilities with fixes"
```

Strix is a standalone CLI agent, not an MCP server — it is not configured in `.mcp.json`. It can itself consume other MCP servers via `~/.strix/mcp-servers.json` if a run needs them.

## When to use

- The user explicitly asks for a penetration test, security assessment, or vulnerability scan of code or an app they own or are authorized to test.
- The user wants CI-integrated dynamic security scanning.

**Authorization required**: Strix performs real exploitation attempts, not passive scanning. Never point it at production systems or anything the user doesn't own or have written authorization to test.

Repo: https://github.com/usestrix/strix
