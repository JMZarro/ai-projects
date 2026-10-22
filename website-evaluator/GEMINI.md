# Agent Instructions

Read this entire file before starting any task.

## Self-Correcting Rules Enging

This file contains a growing ruleset that improves over time.  **At session start, read the entire "Learned Rules" section before doing anything.**

### How it works

1. When a user corrects you or you make a mistake **immediately append a new rule** to the "Learned Rules" section at the bottom of this file.
2. Rules are numbered sequentially and written as clear, imperative instructions.
3. Format: 'N. [CATEGORY] Never/Always do X - because Y.'
4. Categories: '[STYLE]', '[CODE]', '[ARCH]', '[TOOL]', '[PROCESS]', '[DATA]', '[UX]', '[OTHER]'
5. Before starting any task, scan all rules below for relevant constraints.
6. If two rules conflict, the higher-numbered (newer) rule wins.
7. Never delete rules.  If a rule becomes obsolete, append a new rule that supersedes it.

### When to add a rule

- User explicitly corrects your output ("no, do it this way")
- User rejects a file, approach, or pattern
- You hit a bug caused by a wrong assuption about this codebase
- User states a preference ("always use X", "never do Y")

### Rule format example

...
14. [CODE] Always use 'bun' instead of 'npm' - user preference, bun is installed globally.
15. [STYLE] Never add emojis to commit messages - project convention.
16. [ARCH] API routes live in 'src/server/routes/', not 'src/api/' - existing codebase pattern.
...

---

## Learned Rules

<!-- New rules are appended below this line.  Do not edit above this section. -->
1. [CODE] Always use a threading.Lock() when multiple threads or subagents log concurrently to shared status files (e.g. .jsonl, .txt) and flush immediately - because concurrent file writes without synchronization cause interleaved lines and corrupt JSON parsing.
2. [CODE] Always handle json.JSONDecodeError per line when streaming or reading JSONL status logs - because a single malformed line must never crash the entire reader or orchestrator status monitoring loop.