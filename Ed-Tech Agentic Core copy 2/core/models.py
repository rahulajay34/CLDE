from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional, Union

# --- Configuration Models ---

class AgentConfig(BaseModel):
    model: str = Field(..., description="The model ID to use for this agent.")
    temperature: float = Field(0.7, description="Temperature for generation.")
    max_tokens: int = Field(8192, description="Max tokens for generation.")

class OrchestratorConfig(BaseModel):
    creator: AgentConfig
    auditor: AgentConfig
    pedagogue: AgentConfig
    editor: AgentConfig
    sanitizer: AgentConfig
    checker: Optional[AgentConfig] = None  # New Checker Agent
    max_iterations: int = Field(3, description="Maximum number of refinement iterations.")
    human_in_the_loop: bool = Field(False, description="Whether to pause for human approval.")

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

    @field_validator('critiques', mode='before')
    @classmethod
    def parse_critiques(cls, v):
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except:
                return []
        return v

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

    @field_validator('points', mode='before')
    @classmethod
    def parse_points(cls, v):
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except:
                return []
        return v

# --- Editor Models ---

class EditAction(BaseModel):
    target_text: str = Field(..., description="The exact text segment in the original draft to be replaced. Must be unique.")
    replacement_text: str = Field(..., description="The new text to replace the target text with.")
    reason: str = Field(..., description="Why this change is being made.")

class EditorResponse(BaseModel):
    replacements: List[EditAction]
    summary_of_changes: str = Field(..., description="Brief summary of what was changed.")

    @field_validator('replacements', mode='before')
    @classmethod
    def parse_replacements(cls, v):
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except:
                return []
        return v

# --- Checker Models (NEW) ---

class CheckerResponse(BaseModel):
    status: Literal["PASS", "FAIL", "WARNING"] = Field(..., description="Validation status.")
    issues: List[str] = Field(..., description="List of specific issues found.")
    corrected_answer_index: Optional[Union[int, List[int]]] = Field(None, description="Suggested corrected index/indices if wrong.")
    feedback: str = Field(..., description="Brief feedback on quality.")

# --- Assignment Models (UPDATED) ---

# Common Difficulty Enum
DifficultyLevel = Literal["Easy", "Medium", "Hard"]

class MCSCQuestion(BaseModel):
    question_text: str = Field(..., description="The question text.")
    options: List[str] = Field(..., description="List of EXACTLY 4 options.", min_length=4, max_length=4)
    correct_option_index: int = Field(..., description="Index of the correct option (1-4).", ge=1, le=4)
    explanation: str = Field(..., description="Explanation for the correct answer.")
    difficulty: DifficultyLevel
    type: Literal["mcsc"] = Field("mcsc", description="Question type identifier.")

class MCMCQuestion(BaseModel):
    question_text: str = Field(..., description="The question text.")
    options: List[str] = Field(..., description="List of EXACTLY 4 options.", min_length=4, max_length=4)
    correct_option_indices: List[int] = Field(..., description="List of indices for correct options (1-4).")
    explanation: str = Field(..., description="Explanation for the correct answer.")
    difficulty: DifficultyLevel
    type: Literal["mcmc"] = Field("mcmc", description="Question type identifier.")

class SubjectiveQuestion(BaseModel):
    question_text: str = Field(..., description="The question text.")
    model_answer: str = Field(..., description="A model answer/key points.")
    explanation: str = Field(..., description="Additional context or grading criteria.")
    difficulty: DifficultyLevel
    type: Literal["subjective"] = Field("subjective", description="Question type identifier.")

# Wrapper for structured generation
class MCSCBatch(BaseModel):
    questions: List[MCSCQuestion]

class MCMCBatch(BaseModel):
    questions: List[MCMCQuestion]

class SubjectiveBatch(BaseModel):
    questions: List[SubjectiveQuestion]

# Legacy support types
class Question(BaseModel):
    question_text: str
    options: List[str]
    correct_answer: str
    explanation: str
    blooms_level: str

class AssignmentBatch(BaseModel):
    questions: List[Question]
