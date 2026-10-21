---
name: stochastic-multi-agent-consensus
description: Spawn N agents with the same prompt (slight framing variations) to independently analyze a problem, then aggregate results by consensus. Use for decision-making, ranking options, strategic analysis, or any problem where you want to filter hallucinations and surface high-variance ideas. Triggers on "consensus", "poll agents", "stochastic consensus", "spawn N agents to analyze", "multi-agent vote", or /stochastic-multi-agent-consensus. Also triggers on phrases like "what do 10 agents think", "get multiple opinions", or "poll on [topic]".
allowed-tools: Read, Grep, Glob, Bash, Powershell, Task, Write, Edit
---

# Stochastic Multi-Agent Consensus

Spawn N agents (default 10) with identical context and near-identical prompts. Each independently analyzes and produces a structured response. Aggregate by finding consensus (mode), divergences (splits), and outliers (unique ideas).

**Why this works:** Exploits stochastic variation in LLM outputs. Like polling 10 experts instead of asking one. The mode filters out hallucinations and individual biases. Divergences reveal genuine judgement calls. Outliers surface creative ideas a single run would miss.

---

## Execution

### 1. Parse the Request

Extract from the user's message:

- **Problem/question** to analyze.
- **Agent Count $N$** — default 10. User can override ("spawn 5 agents", "poll 20 agents").
- **Output format** — what each agent should produce (rankings, recommendations, binary decisions, scored rubrics).
- **Options list** (if applicable) — predefined options to rank/evaluate, or let agents propose their own.

> [!TIP]
> If the problem is vague or under-specified, ask the user to sharpen it before proceeding. Running $N$ agents on a fuzzy prompt wastes tokens and generates diffuse, unaggregatable noise.

---

### 2. Design the Structured Output Schema

Before spawning, define what each agent must return. The schema must be uniform and strictly parseable to allow objective aggregation:

- **Ranking task**:

  ```markdown
  1. Primary Rank List: Ordered list from 1 (best) to M (worst).
  2. Decisive Factor: 1-sentence explanation for the #1 pick.
  3. Fatal Flaw: 1-sentence reason for the last-place pick.
  ```

- **Open recommendation**:

  ```markdown
  1. Top Pick: Single chosen approach or solution.
  2. Core Rationale: 2–3 bullet points explaining why.
  3. Key Vulnerability: Biggest risk or prerequisite.
  4. Novel Angle: One non-obvious observation or alternative considered.
  ```

- **Binary / Multi-Choice decision**:

  ```markdown
  1. Choice: [Option A | Option B | Option C]
  2. Confidence Score: 1 to 10
  3. Primary Justification: Concise reason for selection.
  4. Red Team Risk: Primary reason this choice could fail.
  ```

- **Weighted scoring rubric**:

  ```markdown
  - Score (1-10) across criteria: [Feasibility, Impact, Maintenance, Security]
  - Overall Recommendation: [Proceed | Defer | Reject]
  ```

---

### 3. Generate Framing Variations (Cognitive Diversity)

To prevent herd behavior and maximize stochastic coverage, assign each of the $N$ agents a distinct cognitive lens while keeping the core problem, data, and constraints identical.

For a standard $N=10$ run, distribute these framing variations:

| Agent # | Cognitive Lens | Framing Instruction Added to Prompt |
| :--- | :--- | :--- |
| **Agent 1** | **Objective Benchmark** | *"Analyze this strictly neutrally, prioritizing balanced industry best practices."* |
| **Agent 2** | **Skeptic / Devil's Advocate** | *"Assume standard assumptions are flawed. Actively search for hidden failure modes, edge cases, and systemic risks."* |
| **Agent 3** | **Pragmatist / Minimalist** | *"Prioritize simplicity, lowest operational overhead, maintainability, and rapid time-to-value."* |
| **Agent 4** | **Growth / High-Upside** | *"Optimize for long-term scalability, maximal upside, strategic leverage, and compounding value."* |
| **Agent 5** | **First-Principles** | *"Disregard standard conventions and buzzwords. Deconstruct the problem to base axioms and rebuild the optimal solution."* |
| **Agent 6** | **Security & Resilience** | *"Focus heavily on failure domains, data safety, blast radius, error recovery, and threat boundaries."* |
| **Agent 7** | **End-User / DX Advocate** | *"Evaluate primarily through the eyes of the end user/developer: ergonomics, friction, adoption, and cognitive load."* |
| **Agent 8** | **Contrarian** | *"Identify what the consensus opinion is likely to be, and stress-test the strongest non-consensus counter-argument."* |
| **Agent 9** | **Cost & Efficiency** | *"Prioritize compute, resource, and token efficiency. Where are resources being wasted unnecessarily?"* |
| **Agent 10** | **Execution Speed** | *"What is the fastest, cleanest path to validation and delivery without accumulating critical tech debt?"* |

*(For $N < 10$, select the top $N$ lenses starting from the top. For $N > 10$, cycle through the list with secondary micro-variations such as strict vs. flexible timeframes or small vs. large team contexts).*

---

### 4. Dispatch the Agents Concurrently

1. Build the base prompt containing:
   - Complete problem statement and context.
   - Assigned framing lens (from Step 3).
   - Strict output schema (from Step 2).
   - Directive: *"Do not acknowledge your assigned persona or output meta-commentary. Output only the requested structured format."*
2. Call `invoke_subagent` in a single tool call containing all $N$ subagents configured to run concurrently.
   - **Model selection**: Set `Model: 'flash'` or `'inherit'` depending on task complexity (`flash` is ideal for rapid aggregation and cost efficiency; `inherit` or `'pro'` for deep mathematical or architectural reasoning).
   - Give each subagent a descriptive role (e.g., `Consensus-Agent-01 (Skeptic)`).

---

### 5. Collect and Validate Responses

1. Await completion of all $N$ subagent invocations.
2. Validate each returned message:
   - Confirm adherence to the output schema.
   - If an agent failed or produced non-conformant output, note the omission or extract the core answer without invalidating the entire pool.
   - Ensure a minimum quorum of $\ge 70\%$ of $N$ valid responses before proceeding to synthesis.

---

### 6. Aggregate and Synthesize

Process the collected responses across four analytical dimensions:

1. **The Consensus (Mode)**:
   - **For Rankings**: Calculate Borda count or average placement rank.
   - **For Discrete Choices**: Calculate vote tally and percentage alignment (e.g., $7/10 = 70\%$).
   - **For Open Recommendations**: Extract common themes mentioned by $\ge 60\%$ of agents.
2. **The Divergence (Splits & Contested Ground)**:
   - Where did agents disagree?
   - What trade-off caused the split (e.g., 6 agents favored speed while 4 favored defensive security)?
3. **Outliers & High-Variance Insights**:
   - Extract unique arguments, non-obvious risks, or creative alternatives raised by only 1–2 agents.
   - Evaluate whether each outlier is an invalid hallucination or a valuable breakthrough.
4. **Consensus Confidence Index**:
   - **High Confidence**: $\ge 80\%$ agreement across diverse framings (strong signal to act).
   - **Moderate Confidence**: $60\% - 79\%$ agreement (actionable, but watch out for known trade-offs).
   - **Low Confidence / Split Decision**: $< 60\%$ agreement (indicates a fundamental business or architectural dilemma requiring explicit user direction).

---

### 7. Generate the Consensus Report

Present the final synthesized report to the user using this markdown structure:

```markdown
# Multi-Agent Consensus Report: [Topic / Question]

**Sample Size**: N = [X] agents | **Confidence Index**: [High / Moderate / Split] ([Y]% alignment)

---

## 1. Executive Summary & Recommended Action
[Clear, direct recommendation derived from the majority consensus and winning trade-offs.]

## 2. Vote & Rank Breakdown
| Option / Approach | Votes / Avg Rank | Key Supporting Lens | Primary Criticism |
| :--- | :--- | :--- | :--- |
| **Option A** | **1st** (8/10) | Pragmatist, Security, Neutral | Higher initial setup |
| **Option B** | **2nd** (2/10) | Growth, High-Upside | Maintenance burden |

## 3. Points of Universal Consensus
- [Item 1: What all or nearly all agents agreed on]
- [Item 2: Invariants and baseline facts]

## 4. Key Divergences & Core Trade-Offs
- **[Divergence Title]**: [Explain the philosophical or technical tension behind the split (e.g., immediate velocity vs. future refactorability)].

## 5. High-Value Outliers & Blind Spots
- **[Agent X - Skeptic]**: [Novel edge case or tail risk identified].
- **[Agent Y - Contrarian]**: [Creative alternative architecture surfaced].

---

<details>
<summary>Click to view raw agent response audit</summary>

- **Agent 1 (Neutral)**: [Summary of output]
- **Agent 2 (Skeptic)**: [Summary of output]
...
</details>
```

---

## Guardrails & Best Practices

- **Zero Information Leakage**: Agents must remain strictly isolated during analysis. Never feed one agent's intermediate thoughts into another.
- **Filter Hallucinations via Plurality**: If a single agent references a non-existent API or library, cross-check against the remaining $N-1$ agents. Do not let solitary hallucinations influence the consensus tier.
- **Honor the Contrarian**: Never dismiss an outlier simply because it had 1 vote. The entire purpose of stochastic polling is to capture high-variance insights that the statistical mode averages out.
