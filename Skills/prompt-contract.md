---
name: prompt-contract
description: Before implementing any non-trivial task, generate a structured Prompt Contract (GOAL, CONSTRAINT, FORMAT, FAILURE) that defines success, limits, output shape, and explicit failure conditions. Treats the contract as an engineering spec, not a suggestion. Triggers automatically on build/implementation requests - new features, skills, scripts, refactors, or any task that produces code or configuration. Also trigger on "contract", "prompt contract", or /prompt-contract.
allowed-tools: AskUserQuestion, Read, Grep, Glob, Task, Bash, Powershell, Edit, Write, TodoWrite
---

# Prompt Contract

## When to Trigger

Invoke this skill **before starting implementation** whenever the user asks to build, create, implement, or refactor something non-trivial. Do NOT trigger for:

- Simple lookups, research, or information gathering
- Single-line fixes, typos, or obvious bugs
- Tasks where the user has provided an explicit contract already (GOAL/CONSTRAINTS/FORMAT/FAILURE sections)
- Pure conversational or informational requests

## Process

### 1. Analyze the Request (silent - no output to user)

Before generating the contract, silently identify:

- **Success metric**: What does "done" look like? Find a number or concrete deliverable.
- **Implicit assumptions**: What are you about to assume without being told?
- **Hard limits**: Language, dependencies, file count, line count, performance targets.
- **Output shape**: What files, formats, structures will be produced?
- **Failure modes**: What shortcuts would you be tempted to take? What edge cases would you skip? What "technically works but..." outcomes are possible?

### 2. Draft the Contract

Write a 4-section contract based on your analysis:

````text
## Contract

GOAL: [Quantifiable success. Include a number or concrete deliverable. "Working X" is not a goal. "X that handles Y at Z performance" is.]

CONSTRAINTS:
- [Hard limit 1 - language, dependencies, compatibility]
- [Hard limit 2 - performance, size, complexity ceiling]
- [Hard limit 3 - integration requirements, existing patterns to follow]
- [Add more if needed, but 3-5 is typical]

FORMAT:
- [Exact files to produce, with paths]
- [What each file contains]
- [Style: type hints, tests, docstrings - only what's relevant]

FAILURE (any of these = not done):
- [Specific shortcut you'd be tempted to take]
- [Edge case that must be handled, not skipped]
- [Integration point that must actually work, not just compile]
- [The "technically works but..." outcome you must avoid]
````

### 3. Present for Approval

Show the contract to the user using `AskUserQuestion` with two options:

- **"Looks good, build it" (Recommended)** - Proceed with implementation using contract as spec
- **"Needs changes"** - User provides feedback, you revise the contract

Keep the question concise. The contract itself is the detail - the question is just "approve or revise?"

If the user picks "Needs changes", revise and re-present. One revision cycle max - if they have more feedback after that, just incorporate it and go.

### 4. Execute Against the Contract

Once approved:

1. Create a `TodoWrite` task list derived directly from the contract.
2. Implement against the contract as a hard spec - not a guideline.
3. Before marking the task complete, verify every FAILURE condition is avoided.
4. The FAILURE section is a checklist; go through each item and confirm it doesn't apply.

### 5. Self-Verify

Before reporting completion or handing deliverables back to the user, conduct a strict audit:

1. **Deliverables Check (FORMAT)**:
   - Verify every file specified in `FORMAT` exists at the exact path requested.
   - Confirm no debug scripts, temporary scratch files, or unused assets are left behind.
   - Validate syntax, type annotations, schemas, and formatting match project standards.

2. **Metric Verification (GOAL)**:
   - Run tests, benchmarks, or command executions to empirically demonstrate the quantifiable goal is reached.
   - Validate both the primary workflow and critical edge cases end-to-end.

3. **Boundary Verification (CONSTRAINTS)**:
   - Verify zero unapproved external dependencies were added.
   - Confirm runtime, file-size, and compatibility constraints are met.
   - Check that existing integration points and conventions were preserved.

4. **Failure Condition Walkthrough (FAILURE)**:
   - Walk through the `FAILURE` list item by item as an active negative test suite:
     - [ ] Are any stubs, placeholders, or `TODO` comments left behind?
     - [ ] Did I handle missing, null, empty, or malformed inputs?
     - [ ] Did I test actual end-to-end execution rather than assuming it works because it compiled?
     - [ ] Are all identified "shortcuts" completely avoided?

5. **Remediation Loop**:
   - If any verification check fails or any `FAILURE` condition is triggered, **do not declare completion**.
   - Fix the issue immediately, re-run verification, and only notify the user once 100% compliance is established.

## Contract Standards & Authoring Rules

A contract is only as effective as its specificity. Avoid vague generalizations:

### GOAL: Must Be Quantifiable and Testable

- **Weak**: "Add error handling to the API."
- **Weak**: "Make the data processing faster."
- **Strong**: "Refactor `POST /api/v1/checkout` to handle payment processor timeouts with exponential backoff (max 3 retries, 5s timeout), returning HTTP 504 on exhaustion while preserving idempotent database state."

### CONSTRAINTS: Must Be Hard Invariants

- **Weak**: "Write clean and modern code."
- **Strong**: "Python 3.10+ standard library only; zero external pip packages; maximum memory usage under 100MB; all shared-file writes synchronized via `threading.Lock`."

### FORMAT: Must Give Exact Paths and Interfaces

- **Weak**: "Source files and some unit tests."
- **Strong**:
  - `src/core/parser.py`: Implements `LogParser` class with type hints and docstrings.
  - `tests/test_parser.py`: Unit tests covering standard, truncated, and corrupt JSONL records.

### FAILURE: The Pre-Mortem Checklist

The `FAILURE` section is the core differentiator of this skill. It guards against common LLM shortcuts:

- Explicitly target temptations you would otherwise take (e.g., using a dummy mock instead of implementing real parsing, leaving `pass` in an exception block).
- Call out specific regressions (e.g., "Modifying the existing function signature without updating call sites").
- Forbid silent failures (e.g., "Swallowing parsing errors without logging line numbers").

## Handling Scope Changes & Mid-Flight Discoveries

A Prompt Contract is a binding agreement. When unexpected friction or impossible constraints arise:

1. **Never Silently Deviate**: Never unilaterally alter constraints, drop file targets, or skip edge cases.
2. **Halt and Highlight**: Stop execution immediately upon encountering an irreconcilable requirement or breaking external change.
3. **Propose an Amendment**:
   - State the conflict and why the current contract cannot be satisfied as written.
   - Present a concise updated contract diff.
   - Request approval via `AskUserQuestion` before resuming implementation.

## Concrete Examples

### Example 1: New Feature / Script

````text
## Contract

GOAL: Build a CLI log audit tool `tools/audit_logs.py` that processes 100MB+ JSONL files in < 3 seconds, streaming records to aggregate HTTP error rates, and outputs a formatted terminal table.

CONSTRAINTS:
- Python 3.10+ using only standard library (`argparse`, `json`, `sys`, `pathlib`).
- Memory footprint must remain < 50MB regardless of file size (streaming processing).
- Execution time < 3.0 seconds on 100,000 log lines.

FORMAT:
- `tools/audit_logs.py`: Standalone executable CLI script with `--file` and `--threshold` flags.
- `tests/test_audit_logs.py`: Pytest suite verifying valid input, empty files, and malformed JSONL lines.

FAILURE (any of these = not done):
- Reading the entire file into memory at once via `.readlines()` or `.read()`.
- Unhandled `json.JSONDecodeError` crashing the script on corrupt lines.
- Missing `--help` documentation or unhandled missing file argument.
- Leaving placeholder logic or mock data in place of real aggregation.
````

### Example 2: Refactoring & Concurrency Fix

````text
## Contract

GOAL: Refactor `services/event_logger.py` to support thread-safe concurrent writes from up to 20 background workers, eliminating interleaved lines and race conditions.

CONSTRAINTS:
- Use `threading.Lock` with immediate `.flush()` after write operations.
- Preserve backward compatibility with the existing `EventLogger.log_event(dict)` signature.
- Zero added external dependencies.

FORMAT:
- `services/event_logger.py`: Thread-safe logger implementation.
- `tests/test_event_logger_concurrency.py`: Concurrency test with 20 threads writing 1,000 events simultaneously.

FAILURE (any of these = not done):
- Any unsynchronized file write that allows lines to interleave.
- Introducing deadlocks or blocking calling threads indefinitely.
- Breaking existing callers of `EventLogger.log_event()`.
- Omitting a concurrency stress test.
````
