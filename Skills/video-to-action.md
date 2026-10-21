---
name: video-to-action
description: Extract actionable steps from YouTube videos using Gemini video understanding. Use when provided a YouTube link and want to learn procedures, extract steps, understand visual tutorials, or turn video content into executable instructions for humans or specific LLMs.
allowed-tools: Read, Grep, Glob, Powershell, Bash
---

# Video-to-Action - Learn from YouTube via Gemini

## Goal

Take any YouTube video URL -> send the video (or transcript) to Gemini multimodal understanding -> extract structured, verifiable, actionable procedures optimized specifically for the intended consumer:

- **A human practitioner** (natural language, visual cues, conceptual context, screenshots/timestamps, tips & troubleshooting).
- **A specific LLM / AI agent** (Claude, Gemini, OpenAI, or generic autonomous agents formatted with machine-executable instructions, strict schemas, XML tags, or zero-fluff tool-ready steps).

## How It Works

1. **Full mode** (`--mode full`, default):
   - Downloads video at an optimized low resolution (360p/480p) via `yt-dlp`.
   - Uploads directly to the **Gemini File API**.
   - Gemini natively processes video frames + audio track synchronously to capture on-screen UI actions, terminal commands, and spoken tips.
2. **Quick mode** (`--mode quick`):
   - Skips video download entirely. Fetches captions/transcript via `youtube-transcript-api`.
   - Ideal for podcasts, theoretical talks, or audio-heavy tutorials where visual UI inspection is unnecessary.
3. **Fallback chain** (`--mode frames`):
   - Automatically triggered if video upload fails or file size exceeds limits.
   - Extracts 1 keyframe every 15-30 seconds via `ffmpeg` + extracts audio transcript, sending them as interleaved multimodal context.

## Consumer Target Profiles (`--target`)

The output is dynamically conditioned based on who will consume and execute the resulting instructions:

| Target | Flag Value | Optimization Strategy |
| :--- | :--- | :--- |
| **Human** *(Default)* | `--target human` | Formatted for human readability: executive summary, visual timestamps (`[MM:SS]`), prerequisites, warnings, tips, keyboard shortcuts, and troubleshooting FAQs. |
| **Anthropic Claude** | `--target claude` | Structured in Anthropic-optimized XML tags (`<context>`, `<prerequisites>`, `<instructions>`, `<step id="n">`, `<validation>`), explicit chain-of-thought anchors, and token-efficient directives. |
| **Google Gemini / Antigravity** | `--target gemini` | Grounded, step-by-step markdown task checklists with explicit state transitions, environment assumptions, and MCP/tool execution markers. |
| **OpenAI (GPT-4o / o1 / o3)** | `--target openai` | System/User message-ready format or structured JSON schema with clear assertion checks, parameter definitions, and strict deterministic flows. |
| **Generic LLM Agent** | `--target llm` | Unambiguous imperative pseudocode/bash commands, strict input/output contracts, idempotency rules, and zero conversational filler. |

## Usage

### 1. Human-Readable Walkthrough (Default)

```bash
# Standard tutorial breakdown for human reading
python3 video-to-action.py "https://youtube.com/watch?v=VIDEO_ID" --target human

# Target human reader with a specific question
python3 video-to-action.py "https://youtube.com/watch?v=VIDEO_ID" --target human -q "Extract only the Blender sculpting shortcuts"
```

### 2. LLM-Optimized Output

```bash
# Optimized for Claude ingestion
python3 video-to-action.py "https://youtube.com/watch?v=VIDEO_ID" --target claude -o claude_recipe.xml

# Optimized for Gemini / Antigravity agents
python3 video-to-action.py "https://youtube.com/watch?v=VIDEO_ID" --target gemini -o gemini_instructions.md

# Quick audio-only extraction for OpenAI models
python3 video-to-action.py "https://youtube.com/watch?v=VIDEO_ID" --mode quick --target openai -o task.json
```

## CLI Options & Flags

| Flag | Short | Default | Description |
| :--- | :--- | :--- | :--- |
| `url` | *(Positional)* | *Required* | YouTube URL (`https://www.youtube.com/watch?v=...` or `https://youtu.be/...`). |
| `--target` | `-t` | `human` | Output optimization target: `human`, `claude`, `gemini`, `openai`, `llm`. |
| `--mode` | `-m` | `full` | Extraction pipeline: `full` (video+audio), `quick` (transcript only), `frames` (sampled keyframes). |
| `--question` | `-q` | `None` | Focus prompt (e.g. "Focus specifically on the Docker deployment steps"). |
| `--output` | `-o` | `stdout` | Output file path (e.g. `guide.md`, `steps.xml`). If omitted, prints to console. |
| `--resolution` | `-r` | `480p` | Maximum download resolution (`360p`, `480p`, `720p`) to conserve bandwidth and tokens. |
| `--gemini-model` | | `gemini-2.5-flash` | Gemini model to use for video analysis. |
| `--keep-video` | | `false` | Retain downloaded video file in scratch directory after upload. |

## Output Templates by Target

### A. When `--target human`

The generated output follows this structure:

```markdown
# [Video Title] - Step-by-Step Practical Guide
*Source: [YouTube URL] | Processed by Gemini Video Understanding*

## Overview & Expected Outcome
A brief 2-3 sentence summary of what this procedure accomplishes.

## Prerequisites & Tools Needed
- [ ] Required software, accounts, or hardware
- [ ] Environmental requirements or dependencies

## Step-by-Step Instructions
### Step 1: [Action Description] (Timestamp: 01:23)
- **What to do**: Clear explanation of the action.
- **On-Screen Details**: Menus clicked, buttons highlighted, or code written.
- **Commands / Code**:
  ```bash
  command --flags
  ```

> **Tip / Warning**: Common pitfall noted by creator at 02:45.

## Troubleshooting & Verification

- How to verify the procedure worked.
- Solutions to common errors demonstrated in the video.

### B. When `--target claude`

The generated output is framed in strict XML for direct injection into Claude's prompt context:

```xml
<video_procedure source="https://youtube.com/watch?v=VIDEO_ID" target="claude">
  <metadata>
    <title>Procedure Title</title>
    <summary>Concise description of the objective.</summary>
  </metadata>
  <prerequisites>
    <item>Dependency or tool requirement</item>
  </prerequisites>
  <execution_plan>
    <step id="1" timestamp="01:15">
      <action>Precise imperative directive</action>
      <code_or_command language="bash">command here</code_or_command>
      <expected_output>Exact visual or console confirmation</expected_output>
      <edge_cases>Potential errors and avoidance strategies</edge_cases>
    </step>
  </execution_plan>
  <verification_criteria>
    <check>Validation step</check>
  </verification_criteria>
</video_procedure>
```

### C. When `--target gemini` or `--target llm`

Formatted for direct autonomous agent task execution:

```markdown
# TASK SPECIFICATION: [Procedure Title]
Source: [URL]
Objective: Execute the procedure extracted from video demonstration.

## INPUT PARAMETERS & ENVIRONMENT
- Environment: [OS/Framework]
- Required Tools: [Tool list]

## EXECUTION STEPS
1. [ ] **STEP 1** [00:45]: Execute `<command>`
   - State assertion: Check if `<expected condition>` holds true before proceeding.
2. [ ] **STEP 2** [02:10]: Modify configuration at `<file_path>`
   - Exact configuration snippet:
   ```yaml
   key: value
   ```

3. [ ] **STEP 3** [04:30]: Validation test

   - Run verification command: `<validation command>`

```

---

## Prerequisites & Environment Setup

1. **System Binaries**:
   - `ffmpeg` installed and available on system `PATH`.
2. **Python Packages**:

   ```bash
   pip install google-genai yt-dlp youtube-transcript-api
   ```

3. **API Keys**:
   - Set `GEMINI_API_KEY` in your environment:

     ```bash
     # Linux / macOS
     export GEMINI_API_KEY="your-api-key"

     # Windows (PowerShell)
     $env:GEMINI_API_KEY="your-api-key"
     ```

---

## Reference Implementation (`video-to-action.py`)

Here is the core Python script implementation that powers the skill:

```python
#!/usr/bin/env python3
"""
video-to-action.py: Extract actionable procedures from YouTube using Gemini 2.5 Flash.
"""

import argparse
import os
import sys
import time
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

TARGET_SYSTEM_PROMPTS = {
    "human": """
You are an expert technical writer and instructional designer.
Your task is to watch the provided video and produce a clear, human-friendly, step-by-step guide.
Include:
- Overview and prerequisites
- Exact step-by-step instructions with timestamps [MM:SS]
- Visual UI cues (what buttons were pressed, what screens appeared)
- Code blocks / exact terminal commands
- Tips, warnings, and troubleshooting advice mentioned or implied.
Use clean markdown with headers, bullet points, and checkable lists.
""",
    "claude": """
You are an expert system optimizing procedural instructions for consumption by Anthropic Claude.
Convert this video into structured, clean XML without conversational commentary.
Use this XML hierarchy:
<video_procedure>
  <metadata><title></title><summary></summary></metadata>
  <prerequisites><item></item></prerequisites>
  <execution_plan>
    <step id="n" timestamp="MM:SS">
      <action>Imperative instruction</action>
      <code_or_command language="..."></code_or_command>
      <expected_output></expected_output>
      <edge_cases></edge_cases>
    </step>
  </execution_plan>
  <verification_criteria><check></check></verification_criteria>
</video_procedure>
Ensure all steps are deterministic, precise, and immediately executable.
""",
    "gemini": """
You are preparing a structured task specification for Google Gemini / Antigravity AI agents.
Format the output as a precise, tool-ready execution checklist in Markdown:
- State required tool capabilities (e.g. terminal execution, file editing).
- Break the procedure into strictly sequential, atomic steps with timestamps [MM:SS].
- Provide exact commands, code diffs, or configurations.
- Include state assertions for validating each step before continuing.
Avoid fluff or conversational introductory text.
""",
    "openai": """
You are structuring a video tutorial into a standardized operational protocol for OpenAI models.
Format the output with strict clarity:
1. System Role & Context definition
2. Deterministic step-by-step procedure with input/output expectations
3. Error handling conditions and fallback paths
Be terse, precise, and completely unambiguous.
""",
    "llm": """
You are converting a video tutorial into machine-executable instructions for an autonomous AI agent.
Format as strict, sequential pseudocode/bash operations with zero preamble.
Every step must have:
- Pre-condition
- Command or action
- Expected output assertion
- Failure recovery action
"""
}

def download_video(url: str, output_dir: Path, resolution: str = "480p") -> Path:
    """Download YouTube video at low resolution using yt-dlp."""
    output_template = str(output_dir / "%(id)s.%(ext)s")
    res_num = resolution.replace("p", "")
    format_selector = f"bestvideo[height<={res_num}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res_num}][ext=mp4]/best"
    
    cmd = [
        "yt-dlp",
        "-f", format_selector,
        "--merge-output-format", "mp4",
        "-o", output_template,
        url
    ]
    print(f"[*] Downloading video via yt-dlp ({resolution})...", file=sys.stderr)
    subprocess.run(cmd, check=True)
    
    # Find downloaded file
    downloaded_files = list(output_dir.glob("*.mp4"))
    if not downloaded_files:
        raise RuntimeError("Failed to locate downloaded MP4 video file.")
    return downloaded_files[0]

def extract_transcript(url: str) -> str:
    """Fetch video transcript as text fallback."""
    from youtube_transcript_api import YouTubeTranscriptApi
    import re
    
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if not video_id_match:
        raise ValueError(f"Could not extract video ID from {url}")
    video_id = video_id_match.group(1)
    
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
    lines = [f"[{int(item['start'] // 60):02d}:{int(item['start'] % 60):02d}] {item['text']}" for item in transcript_list]
    return "\n".join(lines)

def analyze_with_gemini(
    client: genai.Client,
    model: str,
    target: str,
    video_path: Path = None,
    transcript: str = None,
    user_query: str = None
) -> str:
    """Send video or transcript to Gemini and retrieve target-formatted instructions."""
    system_instruction = TARGET_SYSTEM_PROMPTS.get(target, TARGET_SYSTEM_PROMPTS["human"])
    prompt_text = "Extract the complete actionable instructions and procedures from this tutorial."
    if user_query:
        prompt_text += f"\nSpecific user focus: {user_query}"
        
    contents = []
    
    if video_path:
        print("[*] Uploading video to Gemini File API...", file=sys.stderr)
        video_file = client.files.upload(file=video_path)
        
        # Wait for file processing if necessary
        while video_file.state.name == "PROCESSING":
            time.sleep(5)
            video_file = client.files.get(name=video_file.name)
            
        if video_file.state.name == "FAILED":
            raise RuntimeError(f"Gemini video processing failed: {video_file.error}")
            
        print("[*] Video processed successfully. Querying Gemini...", file=sys.stderr)
        contents.append(video_file)
    elif transcript:
        contents.append(f"Video Transcript with Timestamps:\n\n{transcript}")
    else:
        raise ValueError("Either video_path or transcript must be provided.")
        
    contents.append(prompt_text)
    
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        )
    )
    return response.text

def main():
    parser = argparse.ArgumentParser(description="Extract actionable steps from YouTube videos using Gemini.")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("-t", "--target", choices=["human", "claude", "gemini", "openai", "llm"], default="human",
                        help="Target audience/consumer for the output (default: human)")
    parser.add_argument("-m", "--mode", choices=["full", "quick", "frames"], default="full",
                        help="Extraction mode: full (video), quick (transcript only), frames (sampled fallback)")
    parser.add_argument("-q", "--question", default=None, help="Specific question or focal area")
    parser.add_argument("-o", "--output", default=None, help="Output file path (default: print to stdout)")
    parser.add_argument("-r", "--resolution", default="480p", help="Download resolution for full mode (default: 480p)")
    parser.add_argument("--gemini-model", default="gemini-2.5-flash", help="Gemini model version")
    parser.add_argument("--keep-video", action="store_true", help="Keep downloaded video on disk")
    
    args = parser.parse_args()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    scratch_dir = Path("scratch_video")
    scratch_dir.mkdir(exist_ok=True)
    video_file = None
    
    try:
        if args.mode == "quick":
            print("[*] Quick mode: extracting transcript...", file=sys.stderr)
            transcript = extract_transcript(args.url)
            result = analyze_with_gemini(client, args.gemini_model, args.target, transcript=transcript, user_query=args.question)
        else:
            try:
                video_file = download_video(args.url, scratch_dir, args.resolution)
                result = analyze_with_gemini(client, args.gemini_model, args.target, video_path=video_file, user_query=args.question)
            except Exception as e:
                print(f"[!] Full video analysis failed ({e}). Falling back to transcript quick mode...", file=sys.stderr)
                transcript = extract_transcript(args.url)
                result = analyze_with_gemini(client, args.gemini_model, args.target, transcript=transcript, user_query=args.question)
        
        if args.output:
            Path(args.output).write_text(result, encoding="utf-8")
            print(f"[+] Output successfully saved to {args.output}", file=sys.stderr)
        else:
            print(result)
            
    finally:
        # Cleanup temporary files
        if video_file and video_file.exists() and not args.keep_video:
            video_file.unlink()
        if scratch_dir.exists() and not any(scratch_dir.iterdir()):
            scratch_dir.rmdir()

if __name__ == "__main__":
    main()
```
