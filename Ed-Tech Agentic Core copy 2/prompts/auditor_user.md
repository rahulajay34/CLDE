Compare the Draft against the Transcript (if provided) and General Quality Standards.

Draft:
{draft}

Transcript:
{transcript}

# YOUR AUDIT PROCESS

**Step 1: The "Lazy Writer" Check (Structure)**

- Did they use generic headers like "### 1. Learning Objectives"? (Penalize).
- Did they use a simple Flowchart instead of a Sequence/State diagram? (Penalize).
- Is the word count sufficient (approx 1200+ words)?

**Step 2: The Depth Check (Content)**

- **The Analogy:** Is it consistent? Or did it drift?
- **The Code:** Is it production-grade? (Comments, Error Handling).
- **Edge Cases:** Did they actually show "Bad Code vs Good Code"?

**Step 3: The "Elite" Tone Check**

- Is it authoritative?
- Is it dense? (Low fluff).

# OUTPUT INSTRUCTIONS (STRICT JSON)

Identify specific factual errors, omissions, or quality failures.
Output purely as a JSON list of objects:
[
{{
"error_type": "Hallucination" | "Omission" | "Fact" | "Quality" | "Tone",
"description": "Specific description of the failure...",
"location": "Quote from text where error occurs..."
}}
]
If no errors, output empty list: [].
