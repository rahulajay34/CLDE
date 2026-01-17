Review the following draft for flow, tone, and difficulty.
Draft:
{draft}

# SCORING RUBRIC

- **90-100:** Production Ready. Excellent depth, creative headers, masterful analogy, complex visual.
- **75-89:** Solid technical content, but generic headers or visual is too simple.
- **60-74:** Good basics, but lacks "Edge Cases" or "Advanced Application".
- **< 60:** **Reject**. Wrong facts, jargon soup, inconsistent analogy, or missing code.

# OUTPUT INSTRUCTIONS (STRICT JSON)

Output a JSON object:
{{
  "score": <0-100>,
  "level": "Beginner" | "Intermediate" | "Advanced",
  "issues": ["list of structural/flow/pedagogical issues"],
  "suggestions": ["list of specific improvements"],
  "audit_report": {{
        "depth_quality": "Elite/Average/Shallow",
        "visual_complexity": "High/Low",
        "header_creativity": "Creative/Generic"
    }}
}}
