Input Draft:
{draft}

Critique (Auditor & Pedagogue):
{audit_feedback}
{pedagogue_feedback}

# TASK

Identify the specific sentences or paragraphs that need fixing based on the feedback.
Create a "Search and Replace" operation to fix them.

# CRITICAL RULES

1. **Uniqueness:** Make sure `target_text` is long enough (10-20 words) to be unique.
2. **Minimalism:** Do not replace the whole document. Replace only the paragraph or section that is wrong.
3. **Safety:** If the changes are too scattered, or you cannot match the text exactly, DO NOT invent matches.

# OUTPUT FORMAT (STRICT JSON)

Output a JSON object:
{{
  "replacements": [
    {{
      "target_text": "The exact text segment from the Input Draft you want to remove. (Must match perfectly)",
      "replacement_text": "The new corrected text segment you want to insert."
    }}
]
}}
