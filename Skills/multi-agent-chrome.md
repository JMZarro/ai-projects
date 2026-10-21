---
name: multi-agent-chrome
description: Orchestrate parallel browser automation using multiple Chrome DevTools MCP instances.  Use when a task requires doing the same browser action across many targets simultaneously (e.g., submitting contact forms, filling applications, scraping pages that need JS rendering).  Spin up 1-5 parallel Chrome agents.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Powershell
---

# Multi-Agent Chrome Orchestrator

Spin up 1-5 parallel agents, each with its own Chrome browser, to do browser tasks concurrently.

## When to Use

- Submitting contact forms across a list of websites
- Filling out applications on multiple platforms
- Scraping JS-rendered pages that need real browser interaction
- Any repetitive bowser task where doing it sequentially is too slow

## Architecture

'''
Business workspace (orchestrator)
|- active/multi-chrome-agent/
|  |- chat.md                   # Shared coordination file
|  |- launch_chrome.sh          # Spawns Chrome instances on ports 9223-9227
|  |- kill_chrome.sh            # Tears down all Chrome instances
|  |- chrome-agent-1/           # Workspace for Agent 1
|  |  |- .mcp.json              # Chrome DevTools on port 9223
|  |  |- Gemini.md              # Agent behavior instructions
|  |- chrome-agent-2/           # Port 9224
|  |- chrome-agent-3/           # Port 9225
|  |- chrome-agent-4/           # Port 9226
|  |- chrome-agent-5/           # Port 9227
'''

## Step-by-Step Orchestration

### 1. Determine how many agents are needed

Look at the task.  If there are 10 contact forms to fill, 3-5 agents is good.  If there are 3, use 2-3.  Don't over-provision.

### 2. Launch Chrome instances

```powershell
& "C:\Users\jason\Business\active\multi-chrome-agent\launch_chrome.ps1" [COUNT]
```

This spawns 'COUNT' Chrome instances on ports 9223+.  Wait for the "READY" confirmation for each.

### 3. Reset the chat file

Clear the chat file and write task assignments:

'''markdown

#### Multi-Chrome Agent Chat

##### Orchestrator

[2026-03-05 14:30] Launching 3 agents for contact form submission.

###### Agent 1 Tasks

1. Go to [Example Website](https://example1.com/contact) -> fill name: "Jay Zee", email: [Example Email]("jayzee@getwebsited.com"), message: "Hi, I'm interested in..."
2. Go to [Example Website](https://example2.com/contact) -> same form fill

###### Agent 2 Tasks

1. Go to [Example Website](https://example3.com/contact) -> fill form
2. Go to [Example Website](https://example4.com/contact) -> fill form

###### Agent 3 Tasks

1. Go to [Example Website](https://example5.com/contact) -> fill form
2. Go to [Example Website](https://example6.com/contact) -> fill form

##### Agent 1

##### Agent 2

##### Agent 3

'''

### 4. Spawn Code agents

For each agent, open a new terminal and run:

'''powershell

cd C:/Users/jason/Business/active/multi-chrome-agent/chrome-agent-N && gemini

'''

Where N is 1-5.  Each agent will:

- Pick up its GEMINI.md (browser worker instructions)
- Connect to its Chrome instance via its local .mcp.json
- Read chat.md for its task assignments
- Execute tasks and report status back to chat.md

**Programmatic launch via PowerShell:** Gemini blocks nested sessions via environment variables. To launch agents programmatically from within an existing session, use PowerShell with `Remove-Item` to strip the blocking environment variables:

```powershell
foreach ($i in 1..5) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\Users\jason\Business\active\multi-chrome-agent\chrome-agent-$i; Remove-Item Env:\GEMINI_CODE_ENTRYPOINT -ErrorAction SilentlyContinue; Remove-Item Env:\GEMINI_AGENT_SDK_VERSION -ErrorAction SilentlyContinue; Remove-Item Env:\GEMINI_CODE_ENABLE_SDK_FILE_CHECKPOINTING -ErrorAction SilentlyContinue; Remove-Item Env:\GEMINI_CODE_EXPERIMENTAL_AGENT_TEAMS -ErrorAction SilentlyContinue; gemini --dangerously-skip-permissions -p 'You are Agent $i. Read C:\Users\jason\Business\active\multi-chrome-agent\chat.md, find your tasks under Agent $i, and execute them. Use Chrome DevTools MCP to browse websites, search listings, and collect data. Write your findings as a markdown table back to chat.md under the Agent $i section. Mark yourself as [WORKING] while active and [DONE] when finished.'"
    Start-Sleep -Seconds 2
}
```

This opens separate PowerShell windows, each running an independent Gemini session with its own Chrome DevTools MCP.

**Manual fallback:** If script launching doesn't work, tell the user to open $N$ terminal tabs:

```powershell
Tab 1: cd C:\Users\jason\Business\active\multi-chrome-agent\chrome-agent-1; gemini
Tab 2: cd C:\Users\jason\Business\active\multi-chrome-agent\chrome-agent-2; gemini
...

```

### 5. Monitor progress

Read the chat file periodically to check agent status:

```powershell
Get-Content C:\Users\jason\Business\active\multi-chrome-agent\chat.md

```

Look for '[DONE]', '[ERROR]', or '[WORKING]' tags from each agent.

### 6. Cleanup

Once all agents have finished executing and data is successfully collected, tear down the running Chrome instances:

PowerShell
& "C:\Users\jason\Business\active\multi-chrome-agent\kill_chrome.ps1"
