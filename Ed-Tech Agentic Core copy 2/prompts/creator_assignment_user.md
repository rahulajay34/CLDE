Topic: {topic}
Key Concepts: {subtopics}
Question Type: {question_type}
Difficulty: {difficulty}
Number of Questions: {count}

Create {count} {question_type} questions at {difficulty} difficulty level for this topic.

For MCSC questions:

- Write clear, specific question text
- Provide exactly 4 plausible options
- Ensure only one is definitively correct
- Write explanations that teach why the correct answer works and why others don't
- **Constraint**: Before writing the final JSON, internally calculate the answer step-by-step. The explanation field must start with the direct reasoning that leads to the correct option, ensuring no logical jumps.

For MCMC questions:

- Write clear question text that indicates multiple correct answers
- Provide exactly 4 options
- Ensure 2-3 are correct
- Make incorrect options plausible but clearly wrong when analyzed
- Explain why each correct answer is right
- **Constraint**: Before writing the final JSON, internally calculate the answer step-by-step. The explanation field must start with the direct reasoning that leads to the correct option, ensuring no logical jumps.

For Subjective questions:

- Give hard level questions and if the question require latex formatting do that
- Write open-ended questions that require explanation or demonstration
- **model_answer**: Provide the direct, "correct" answer or key points a student should write.
- **explanation**: Provide the detailed, complete answer to the question. This should be a comprehensive explanation of the solution. Do NOT include grading rubrics.

Difficulty guidelines:

- Easy: Direct recall or simple application of one concept
- Medium: Application requiring combining 2-3 concepts or deeper analysis
- Hard: Synthesis, evaluation, or complex application across multiple concepts

Critical: Question text should be direct and clear. Never include meta-language like "Based on what you learned" or "From the session." Just ask the question directly.

**CRITICAL OUTPUT RULE:** The content inside the JSON fields (like `explanation`, `question_text`) must be **final, student-facing content only**. Do NOT include internal notes.
**FORMATTING RULES**:

1. Use **Markdown** for formatting (e.g., **bold**, _italics_, lists).
2. For long text, use `\n\n` (double newline) to separate paragraphs.
3. Keep 1 extra space between multiline sections for better readability.
4. Output **ONLY** a valid JSON list of objects. No markdown fencing around the JSON itself if possible, but code blocks are acceptable.

```json
[
  { "type": "...", "question_text": "...", ... },
  ...
]
```
