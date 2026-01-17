from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# --- Auditor Models ---

class CritiquePoint(BaseModel):
    section: str = Field(..., description="The section of the text where the issue is found.")
    issue: str = Field(..., description="A concise description of the issue.")
    severity: Literal["Critical", "Major", "Minor", "Nitpick"] = Field(..., description="The severity of the issue.")
    suggestion: str = Field(..., description="A actionable suggestion to fix the issue.")
    quote: Optional[str] = Field(None, description="Exact quote from the text if applicable.")

class AuditResult(BaseModel):
    critiques: List[CritiquePoint]
    summary: str = Field(..., description="A brief summary of the overall quality.")
    quality_score: int = Field(..., description="A score from 0 to 100 representing the quality/accuracy.")

# --- Pedagogue Models ---

class PedagoguePoint(BaseModel):
    section: str = Field(..., description="The section of the text.")
    feedback_type: Literal["Clarity", "Flow", "Tone", "Engagement", "Difficulty"] = Field(..., description="The category of feedback.")
    observation: str = Field(..., description="What was observed.")
    suggestion: str = Field(..., description="How to improve it.")

class PedagogueAnalysis(BaseModel):
    points: List[PedagoguePoint]
    overall_assessment: str = Field(..., description="General assessment of the pedagogical value.")
    engagement_score: int = Field(..., description="0-100 score on how engaging the content is.")

# --- Editor Models ---

class EditAction(BaseModel):
    target_text: str = Field(..., description="The exact text segment in the original draft to be replaced. Must be unique.")
    replacement_text: str = Field(..., description="The new text to replace the target text with.")
    reason: str = Field(..., description="Why this change is being made.")

class EditorResponse(BaseModel):
    replacements: List[EditAction]
    summary_of_changes: str = Field(..., description="Brief summary of what was changed.")

# --- Creator Models (Optional, for future use) ---
# Currently Creator returns raw markdown, but we could enforce structure if needed.
