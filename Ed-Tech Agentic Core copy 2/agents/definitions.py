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
    def __init__(self, model="claude-3-5-sonnet-20240620"):
        super().__init__("Creator", model)

    def get_system_prompt(self) -> str:
        return read_prompt("creator_system.md")

    def format_user_prompt(self, topic: str, subtopics: str) -> str:
        template = read_prompt("creator_user.md")
        return template.replace("{topic}", topic).replace("{subtopics}", subtopics)


# --- 2. The Auditor (Accuracy) ---
class AuditorAgent(BaseAgent):
    def __init__(self, model="claude-3-5-sonnet-20240620"):
        super().__init__("Auditor", model)

    def get_system_prompt(self) -> str:
        return read_prompt("auditor_system.md")

    def format_user_prompt(self, draft: str, transcript: str) -> str:
        template = read_prompt("auditor_user.md")
        return template.replace("{draft}", draft).replace("{transcript}", transcript)


# --- 3. The Pedagogue (Flow/Difficulty) ---
class PedagogueAgent(BaseAgent):
    def __init__(self, model="claude-3-5-sonnet-20240620"):
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
    def __init__(self, model="claude-3-5-sonnet-20240620"):
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
    def __init__(self, model="claude-3-haiku-20240307"):
        super().__init__("Sanitizer", model)

    def get_system_prompt(self) -> str:
        return read_prompt("sanitizer_system.md")

    def format_user_prompt(self, text: str) -> str:
        template = read_prompt("sanitizer_user.md")
        return template.replace("{text}", text)
