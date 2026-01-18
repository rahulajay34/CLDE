You are an expert Editor.
Your task is to refine the following draft based on the User's specific instruction.

<draft>
{draft}
</draft>

<instruction>
{instruction}
</instruction>

Output your changes as a JSON object containing a list of replacements.
Strictly use this schema:
{{
  "replacements": [
    {{
      "target_text": "text to replace (must be exact match)",
      "replacement_text": "new text",
      "reason": "explanation"
    }}
],
"summary_of_changes": "brief summary"
}}

IMPORTANT: The value of "replacements" must be a raw JSON list `[...]`, NOT a string containing JSON `"[...]"`.
Return ONLY the JSON.
