from .base_agent import BaseAgent
import os

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")

def read_prompt(filename):
    try:
        with open(os.path.join(PROMPTS_DIR, filename), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: Prompt file {filename} not found."

# --- 1. The Creator ---
class CreatorAgent(BaseAgent):
    def __init__(self, model="claude-sonnet-4-5-20250929"):
        super().__init__("Creator", model)

    def get_system_prompt(self, mode: str = "Lecture Notes") -> str:
        if mode == "Pre-read Notes":
            return read_prompt("creator_preread_system.md")
        elif mode == "Assignment":
            return read_prompt("creator_assignment_system.md")
        else: # Default or "Lecture Notes"
            return read_prompt("creator_lecture_system.md")

    def format_user_prompt(self, topic: str, subtopics: str, mode: str = "Lecture Notes", **kwargs) -> str:
        if mode == "Pre-read Notes":
            template = read_prompt("creator_preread_user.md")
            prerequisites = kwargs.get("prerequisites", "None")
            return template.replace("{topic}", topic)\
                           .replace("{subtopics}", subtopics)\
                           .replace("{prerequisites}", prerequisites)
        
        elif mode == "Assignment":
            template = read_prompt("creator_assignment_user.md")
            return template.replace("{topic}", topic)\
                           .replace("{subtopics}", subtopics)\
                           .replace("{question_type}", kwargs.get("question_type", "MCSC"))\
                           .replace("{difficulty}", kwargs.get("difficulty", "Medium"))\
                           .replace("{count}", str(kwargs.get("count", 5)))
            
        else: # Lecture Notes
            template = read_prompt("creator_lecture_user.md")
            prerequisites = kwargs.get("prerequisites", "None")
            return template.replace("{topic}", topic)\
                           .replace("{subtopics}", subtopics)\
                           .replace("{prerequisites}", prerequisites)

    def format_preread_prompt(self, topic: str, subtopics: str) -> str:
        # DEPRECATED: Use format_user_prompt with mode="Pre-read Notes"
        return self.format_user_prompt(topic, subtopics, mode="Pre-read Notes")


# --- 2. The Auditor (Accuracy) ---
class AuditorAgent(BaseAgent):
    def __init__(self, model="claude-sonnet-4-5-20250929"):
        super().__init__("Auditor", model)

    def get_system_prompt(self) -> str:
        return read_prompt("auditor_system.md")

    def format_user_prompt(self, draft: str, transcript: str) -> str:
        template = read_prompt("auditor_user.md")
        return template.replace("{draft}", draft).replace("{transcript}", transcript)


# --- 3. The Pedagogue (Flow/Difficulty) ---
class PedagogueAgent(BaseAgent):
    def __init__(self, model="claude-sonnet-4-5-20250929"):
        super().__init__("Pedagogue", model)

    def get_system_prompt(self) -> str:
        return read_prompt("pedagogue_system.md")

    def format_user_prompt(self, draft: str, target_audience: str = "General Student") -> str:
        template = read_prompt("pedagogue_user.md")
        # Inject audience at the top or bottom
        audience_instruction = f"\n\nIMPORTANT: Assess this content specifically for a '{target_audience}' audience."
        return template.replace("{draft}", draft) + audience_instruction


# --- 4. The Editor (Diff-Based) ---
class EditorAgent(BaseAgent):
    def __init__(self, model="claude-sonnet-4-5-20250929"):
        super().__init__("Editor", model)

    def get_system_prompt(self) -> str:
        return read_prompt("editor_system.md")

    def format_user_prompt(self, draft: str, audit_feedback: str, pedagogue_feedback: str) -> str:
        template = read_prompt("editor_user.md")
        return template.replace("{draft}", draft)\
                       .replace("{audit_feedback}", audit_feedback)\
                       .replace("{pedagogue_feedback}", pedagogue_feedback)

    def format_instruction_prompt(self, draft: str, instruction: str) -> str:
        template = read_prompt("editor_instruction.md")
        return template.replace("{draft}", draft).replace("{instruction}", instruction)


# --- 5. The Sanitizer ---
class SanitizerAgent(BaseAgent):
    def __init__(self, model="claude-haiku-4-5-20251001"):
        super().__init__("Sanitizer", model)

    def get_system_prompt(self) -> str:
        return read_prompt("sanitizer_system.md")

    def format_user_prompt(self, text: str) -> str:
        template = read_prompt("sanitizer_user.md")
        return template.replace("{text}", text)


# --- 6. The Checker (Assignment Validation) ---
class CheckerAgent(BaseAgent):
    def __init__(self, model="claude-haiku-4-5-20251001"):
        super().__init__("Checker", model)

    def get_system_prompt(self) -> str:
        return read_prompt("checker_assignment_system.md")

    def format_user_prompt(self, question_data: str) -> str:
        template = read_prompt("checker_assignment_user.md")
        return template.replace("{question_data}", question_data)

