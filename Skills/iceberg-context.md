---
name: iceberg-context
description: Enforces the Iceberg Principle for context window management. Keeps active context lean, high-signal, and minimal while leaving raw codebases, full documentation, git history, and past sessions submerged in on-demand retrieval tools. Use when working on complex or long-running tasks to prevent premature context compaction and memory loss.
---

# The Iceberg Technique: Context Window Hygiene

> [!IMPORTANT]
> **The Iceberg Principle**: What is visible in the active LLM context window must be only the tip of the iceberg (high-signal, active state, core rules). The vast body of the codebase, raw logs, documentation, and history must remain submerged on disk and queried strictly just-in-time (JIT).

---

## 1. The Separation of Planes

```text
         ACTIVE CONTEXT WINDOW (The Tip)
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  <- Waterline
   • Core Directives & Learned Rules (GEMINI.md)
   • Active Task Goal & Current Execution Step
   • Targeted Code Slices (Only the functions being edited)
   • Immediate Decisions & Output Schema
   ===============================================
         ACCESSIBLE ON-DEMAND (Submerged)
   • Full Workspace Codebase      -> Grep / Glob / ripgrep
   • File Contents                -> read_file (bounded line ranges)
   • Session History & Transcripts-> External markdown logs / memory
   • Skill & API Reference Docs   -> Progressive disclosure / search docs
   • Version Control History      -> git log / git diff via shell
   • Scratchpads & Intermediates  -> Conversation artifacts & scratch files
```

## 2. Mandatory Context Hygiene Protocols

### A. Windowed File Reads (Never Slurp Files Whole)

- **Do not read an entire file** unless it is under 100 lines or fundamentally indivisible.
- Always use `Grep` or search tools first to locate symbols, class definitions, or error lines.
- Always pass `StartLine` and `EndLine` to `read_file` to inspect only the targeted function (plus ~10 lines of surrounding context).

### B. Output Caps on Terminal Commands

- Never run unbounded terminal output commands that can dump hundreds of lines into context (e.g., bare `Get-ChildItem -Recurse`, `cat large.log`, `npm list`).
- Truncate, pipe, or summarize output at the shell level:
  - PowerShell: `| Select-Object -First 20`
  - Bash: `| head -n 30` or `grep -E "pattern"`
- If a command outputs high-volume JSON or logs, redirect it to a scratch file (`> scratch/output.json`) and inspect specific keys using a targeted script.

### C. Externalize Intermediate Working State

- **Do not brainstorm or draft large artifacts in the conversational chat thread.** That text permanently inflates the context for every subsequent turn.
- Store multi-step reasoning, test data, and intermediate matrices in conversation artifacts (`<conversation-id>/scratch/`) or markdown artifacts.
- Keep only the link and a 2-line summary in active context.

### D. Delegate Context-Heavy Research to Subagents

- When broad surveys, multi-file searches, or deep dependency audits are needed, delegate to a `research` or `self` subagent.
- The subagent's noisy exploratory reads stay confined to its isolated sub-thread; only its distilled synthesis returns to your primary context window.

### E. Persist Lessons Out-of-Band (Compaction Insurance)

- Any correction, architectural decision, or bug fix rule must be written immediately to `GEMINI.md` or a project memory file.
- **Never rely on the conversation history to remember lessons.** If the conversation compacts, anything stored only in chat history is lost; anything stored on disk is permanent.

## 3. Self-Check Before Tool Invocation

Before making any tool call, verify:

1. *Am I pulling more than 100 lines into context?* If yes, narrow the query or pipe to a file.
2. *Can I find this exact line with Grep instead of reading the whole module?* If yes, Grep first.
3. *Am I holding draft data in chat that belongs in a scratch file?* If yes, write to scratch.
