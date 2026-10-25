---
name: reverse-prompt
description: Before implementing any non-trivial build, ask the user 5+ dynamically generated clarifying questions to surface non-obvious preferences, assumptions, and constraints. Triggers on build/implementation requests - new features, new skills, new scripts, refactors, or any task that produces code or configuration.
allowed-tools: AskUserQuestion
---

# Reverse Prompt

## When to Trigger

Invoke this skill **before starting implementation** whenever the user asks to build, create, implement, or refactor something non-trivial. Do NOT trigger for:

- Simple lookups, research, or information gathering
- Single-line fixes, typos, or obvious bugs
- Tasks where the user has given exhaustive, specific instructions
- Direct follow-ups or tweaks to work completed earlier in the same session

## Process

### 1. Analyze the Request

Before generating questions, silently identify:

- **Stated requirements**: What the user explicitly asked for
- **Implicit assumptions**: What you are about to assume without being told
- **Decision points**: Where there are multiple valid architectural or design approaches
- **Failure modes**: What could go wrong or feel counter-intuitive to the user
- **Taste-dependent choices**: Where personal preference determines the "right" answer

### 2. Generate 5+ Questions

Questions must satisfy four criteria:

1. **Non-intuitive** — Do not ask things the user already specified or that are obvious from context or the existing codebase.  
   - *Weak*: "What language should we use?" (already obvious from repo)  
   - *Strong*: "If the sync process encounters an invalid row, should it halt immediately or skip and write errors to a quarantine file?"

2. **High-impact** — Every question must meaningfully change the code architecture, data model, or behavior. Skip anything that doesn't change the implementation.

3. **Concrete** — Ground questions in specific scenarios rather than abstract design theory.  
   - *Weak*: "How should errors be handled?"  
   - *Strong*: "When an upstream rate limit (HTTP 429) is hit, should we retry with exponential backoff (up to 3 times), queue the task for a background worker, or fail immediately?"

4. **Opinionated** — Always provide a recommended default for every question so the user can easily accept your proposal with a single affirmative response. Frame as: `"Default: [Recommendation] — want something different?"`

**Categories to draw from** (select the 5+ most relevant to the task):

- **Edge case behavior**: What happens when things fail, timeout, or receive malformed input
- **Scope boundaries**: What is explicitly out of scope for this pass
- **Integration points**: How this interfaces with existing modules, databases, or third-party APIs
- **Output format & style**: Terminal output, log verbosity, JSON vs. table layout
- **Performance vs. simplicity tradeoffs**: In-memory vs. persistent storage, parallel vs. sequential processing
- **Naming & structural conventions**: Directory placement, class/file naming patterns
- **Dependencies & tooling**: Permitted external libraries, framework choices
- **Security & privacy**: Secret management, sanitization, data retention
- **Idempotency & state management**: Can operations be re-run safely; where is intermediate state stored
- **User-facing copy & tone**: CLI feedback, error messaging, logging style

---

### 3. Format and Present the Questions

Present the questions in a clean, easily answerable structure. Include an explicit **fast-track escape hatch** so the user can approve all defaults in a single message.

#### Presentation Template

```markdown
Before implementing **[Feature / Task Name]**, here are a few clarifying questions to lock down key architectural decisions and assumptions:

1. **[Question Topic / Scenario]**
   - **Recommended Default:** [Option A - Description and rationale]
   - **Alternative B:** [Description]
   - **Alternative C:** [Description]

2. **[Question Topic / Scenario]**
   - **Recommended Default:** [Option A - Description and rationale]
   - **Alternative B:** [Description]

... [Questions 3 through 5+]

> 💡 **Fast Track:** If you agree with all recommended defaults, simply reply **"proceed with defaults"** (or specify changes like *"use Option B for #2, defaults for the rest"*).
```

*Note: If an interactive prompt tool (such as `AskUserQuestion`) is available, you may render these questions interactively, ensuring the recommended choice is pre-selected or listed first.*

---

### 4. Process the Responses

Handle user responses according to these scenarios:

- **Full Approval ("Proceed with defaults", "Looks good", "Yes")**:
  - Immediately adopt all recommended defaults.
  - Do not ask follow-ups.
  - Move directly to Step 5.

- **Selective Overrides (e.g., "Change #2 to B, rest look good")**:
  - Apply the requested override to question #2.
  - Apply the recommended defaults to all remaining questions.
  - Only ask a follow-up if an override introduces an irreconcilable conflict.

- **Partial Answers (user answers questions 1 and 3, skips 2, 4, 5)**:
  - Honor the explicit answers.
  - Silently apply the recommended defaults to any unaddressed questions.
  - Note the adopted defaults when presenting the brief plan.

- **Bypass / Impatience ("Just do it", "Skip questions", "Start building")**:
  - Do not argue or insist on an interrogation.
  - Adopt all recommended defaults immediately and begin implementation.

---

### 5. Transition to Implementation

Once answers are resolved:

1. **Lock the Specification**: State in 2–3 bullet points the decisions finalized (requirements + selected defaults/overrides).
2. **Execute**: Begin implementation immediately without extra conversational rounds.

---

## Example Walkthrough

### User Request

> *"Write a Python script that monitors an S3 bucket for incoming JSON payloads and loads them into a Postgres database."*

### Generated Clarifying Questions

1. **Failure & Quarantine Strategy**  
   - **Recommended Default:** If a payload fails schema validation, move the S3 object to an `s3://[bucket]/quarantine/` prefix and log an alert to STDERR.  
   - **Alternative B:** Abort execution immediately and leave the file in place.  
   - **Alternative C:** Skip invalid rows, load valid records, and write an error summary back to S3.

2. **Duplicate & Re-run Handling (Idempotency)**  
   - **Recommended Default:** Use an upsert (`ON CONFLICT (id) DO UPDATE`) keyed on the payload's primary ID so re-processing the same file is safe.  
   - **Alternative B:** Reject duplicates with an error.  
   - **Alternative C:** Append only (assume all incoming events are unique).

3. **Database Connection & Concurrency**  
   - **Recommended Default:** Use a single persistent connection pool with `psycopg3` processing files sequentially to minimize connection churn.  
   - **Alternative B:** Parallel worker pool (multiprocessing or asyncio) for high-throughput ingestion.

4. **State Tracking & Ingestion Trigger**  
   - **Recommended Default:** Poll the bucket at a configurable interval (e.g., every 60s) and track processed object `ETag`s in an internal `_ingestion_log` Postgres table.  
   - **Alternative B:** Listen for AWS SQS notifications emitted by S3 Event Notifications.  
   - **Alternative C:** One-shot execution (process whatever is currently in the bucket and exit).

5. **Secrets & Environment Configuration**  
   - **Recommended Default:** Read credentials (`DATABASE_URL`, AWS access keys) strictly from standard environment variables with `.env` fallback via `python-dotenv`.  
   - **Alternative B:** Pass credentials via CLI flags (`argparse`).  
   - **Alternative C:** Read from AWS Secrets Manager / Parameter Store directly.

---

## Anti-Patterns and Guardrails

- **The Interrogation Trap**: Limit questions to a single round of 5–7 questions. Never initiate a back-and-forth loop unless the user explicitly asks for further discussion.
- **The Obvious Inquiry**: Never ask about existing standards already established in the codebase (e.g., "Should we use pytest or unittest?" when `pytest.ini` already exists).
- **The Empty Choice**: Never present an open-ended question without proposing a concrete recommended default.
- **Stalling**: If the user skips or provides vague feedback, do not block progress. Pick the most sensible default and start building.
