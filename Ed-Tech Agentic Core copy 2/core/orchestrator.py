import json
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, List

from core.logger import logger
from core.config import DEFAULT_MODEL
from core.client import AnthropicClient
from core.structured_client import StructuredClient
from core.utils import save_markdown_file, save_metadata, get_timestamp_filename, save_excel
from agents.definitions import (
    CreatorAgent, AuditorAgent, PedagogueAgent, SanitizerAgent, EditorAgent
)
from core.models import AuditResult, PedagogueAnalysis, EditorResponse
import re

def clean_json_string(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```json\s*|^```\s*|```$", "", text, flags=re.MULTILINE)
    return text.strip()


class Orchestrator:
    def __init__(self, config: "OrchestratorConfig", api_key=None): # Type hint quoted for forward ref or import
        # If config is not passed (legacy support), create a default one
        if not hasattr(config, "creator"):
            from core.models import OrchestratorConfig, AgentConfig
            logger.warning("Legacy initialization detected. Using default config.")
            base_model = config if isinstance(config, str) else DEFAULT_MODEL
            config = OrchestratorConfig(
                creator=AgentConfig(model=base_model),
                auditor=AgentConfig(model=base_model),
                pedagogue=AgentConfig(model=base_model),
                editor=AgentConfig(model=base_model),
                sanitizer=AgentConfig(model=DEFAULT_MODEL if "haiku" in DEFAULT_MODEL else "claude-3-haiku-20240307"),
                max_iterations=3,
                human_in_the_loop=False
            )

        self.config = config
        logger.info(f"Initializing Orchestrator with config: {config.model_dump_json(indent=2)}")
        
        self.client = AnthropicClient(api_key) 
        self.structured_client = StructuredClient(api_key) 
        
        # Initialize agents with specific models from config
        self.creator = CreatorAgent(model=config.creator.model)
        self.auditor = AuditorAgent(model=config.auditor.model)
        self.pedagogue = PedagogueAgent(model=config.pedagogue.model)
        self.editor = EditorAgent(model=config.editor.model)
        self.sanitizer = SanitizerAgent(model=config.sanitizer.model)
        
        # State
        self.state = {
            "draft": "",
            "iteration": 0,
            "costs": 0.0,
            "used_models": set(),
            "audit_result": None,
            "pedagogue_result": None,
            "history": [] 
        }

    def _apply_robust_edits(self, text, replacements):
        """Applies edits with exact and fuzzy matching."""
        new_text = text
        applied_count = 0
        
        for item in replacements:
            if item.target_text in new_text:
                new_text = new_text.replace(item.target_text, item.replacement_text)
                applied_count += 1
            else:
                # Robust Regex for Python 3.8+ (Handles newlines/tabs in target)
                pattern = re.escape(item.target_text)
                pattern = pattern.replace(" ", r"\s+") 
                
                # Use re.sub with count=1 to replace only the first occurrence found
                new_text, n = re.subn(pattern, item.replacement_text, new_text, count=1)
                if n > 0:
                    applied_count += 1
                else:
                    logger.warning(f"Editor target not found: {item.target_text[:30]}...")
        return new_text, applied_count

    def yield_event(self, agent_name, model_name, status, content=None, tokens=None, cost=0.0):
        return {
            "type": "step",
            "agent": agent_name,
            "model": model_name,
            "status": status,
            "content": content,
            "tokens": tokens or (0,0),
            "cost": cost
        }

    def _update_costs(self, cost, model):
        self.state["costs"] += cost
        self.state["used_models"].add(model)

    def run_loop(self, topic: str, subtopics: str, transcript: str = None, mode: str = "Lecture Notes", target_audience: str = "General Student"):
        """
        Main execution loop implemented as a State Machine.
        """
        # Reset State
        self.state["draft"] = ""
        self.state["iteration"] = 0
        self.state["costs"] = 0.0
        self.state["used_models"] = set()
        
        max_iterations = self.config.max_iterations
        
        # --- Node 1: Creator ---
        yield from self._node_creator(topic, subtopics, transcript, mode)
        if not self.state["draft"]:
            return # Critical failure

        if mode == "Assignment":
             # Shortcut for Assignment mode - just sanitization implicitly or direct save
             yield self.yield_event("Orchestrator", "System", "Validating Assignment...")
             # Assignment logic remains simple for now, can be structured later
        else:
            # --- Loop: Critique & Refine ---
            while self.state["iteration"] < max_iterations:
                self.state["iteration"] += 1
                
                # OPTIMIZATION: Pedagogue only runs on first iteration to establish tone/difficulty
                run_pedagogue = (self.state["iteration"] == 1)
                
                yield self.yield_event("Orchestrator", "System", f"Iteration {self.state['iteration']}: Critiquing...")
                
                # --- Node 2: Parallel Critique (Auditor & Pedagogue) ---
                yield from self._node_critique_parallel(transcript, target_audience, run_pedagogue)
                
                # --- Node 3: Decision Gate ---
                if self._should_stop_early():
                    yield self.yield_event("Orchestrator", "System", "Critique Clean. Breaking loop.")
                    break
                
                if self.state["iteration"] == max_iterations:
                    yield self.yield_event("Orchestrator", "System", "Max iterations reached. Skipping final edit.")
                    break

                # --- Node 4: Editor ---
                yield self.yield_event("Orchestrator", "System", f"Iteration {self.state['iteration']}: Refining...")
                yield from self._node_editor()

            # --- Node 5: Sanitizer REMOVED for Cost Optimization ---

        # --- Node 6: Save & Return ---
        yield from self._node_save_and_finalize(topic, mode, transcript)

    # ==========================
    # Node Implementations
    # ==========================

    def _node_creator(self, topic, subtopics, transcript, mode):
        yield self.yield_event("Creator", self.creator.model, f"Creating V1 Draft ({mode})...")
        
        if mode == "Assignment":
             # Keep assignment separate for now, it returns a JSON list string
             creator_prompt = f"""Create a comprehensive Assignment (Quiz) for the following:
Topic: {topic}
Subtopics: {subtopics}

Output strictly as a JSON list of objects with keys: ["Question", "Options", "Correct Answer", "Explanation", "Bloom's Level"].
Example: [{{"Question": "...", "Options": "A)... B)...", ...}}]
Do not include markdown formatting or 'Here is the JSON' prefix. Just the pure JSON."""
        else:
            creator_prompt = self.creator.format_user_prompt(topic, subtopics)
            
        draft, in_tok, out_tok = self.client.generate_response(
            system_prompt=self.creator.get_system_prompt(),
            user_content=creator_prompt,
            model=self.creator.model,
            cache_content=transcript # Client handles caching logic
        )
        
        if not draft:
            yield {"type": "error", "message": "Failed to generate draft (API Error)."}
            return

        cost = self.client.calculate_cost(in_tok, out_tok, self.creator.model)
        self._update_costs(cost, self.creator.model)
        
        self.state["draft"] = draft
        yield self.yield_event("Creator", self.creator.model, "Draft Generated", content=draft, tokens=(in_tok, out_tok), cost=cost)

    def _node_critique_parallel(self, transcript, target_audience, run_pedagogue=True):
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_audit = executor.submit(self._run_audit_structured, self.state["draft"], transcript)
            
            future_pedagogue = None
            if run_pedagogue:
                future_pedagogue = executor.submit(self._run_pedagogue_structured, self.state["draft"], target_audience)
            
            audit_res = future_audit.result()
            self.state["audit_result"] = audit_res["data"]
            self._update_costs(audit_res["cost"], self.auditor.model)
            
            pedagogue_res = None
            if future_pedagogue:
                pedagogue_res = future_pedagogue.result()
                self.state["pedagogue_result"] = pedagogue_res["data"]
                self._update_costs(pedagogue_res["cost"], self.pedagogue.model)
        
        # Serialize for UI
        audit_json = audit_res["data"].model_dump() if audit_res["data"] else {}
        pedagogue_json = {}
        if self.state["pedagogue_result"]:
             pedagogue_json = self.state["pedagogue_result"].model_dump()

        yield self.yield_event("Auditor", self.auditor.model, f"Quality Score: {audit_json.get('quality_score', 'N/A')}", 
                              content=json.dumps(audit_json, indent=2), cost=audit_res["cost"])
        
        if run_pedagogue and pedagogue_json:
            yield self.yield_event("Pedagogue", self.pedagogue.model, f"Engagement: {pedagogue_json.get('engagement_score', 'N/A')}",
                                  content=json.dumps(pedagogue_json, indent=2), cost=pedagogue_res["cost"] if pedagogue_res else 0)

    def _node_editor(self):
        # OPTIMIZATION: Prune Feedback to save tokens
        audit_data = self.state["audit_result"]
        ped_data = self.state["pedagogue_result"]

        # Filter only Critical/Major severity issues
        critical_feedback = []
        if audit_data:
            critical_feedback = [
                f"- {c.section}: {c.suggestion} (Issue: {c.issue})" 
                for c in audit_data.critiques 
                if c.severity in ["Critical", "Major"]
            ]
        
        # Construct a lighter prompt context
        feedback_summary = "CRITICAL ISSUES TO FIX:\n" + "\n".join(critical_feedback) if critical_feedback else "No critical issues found."
        
        pedagogue_feedback_summary = ""
        if ped_data and ped_data.engagement_score < 80:
             pedagogue_feedback_summary = f"PEDAGOGICAL ISSUES: {ped_data.overall_assessment}"

        editor_prompt = self.editor.format_user_prompt(
            draft=self.state["draft"],
            audit_feedback=feedback_summary, # Sending summary, not full JSON
            pedagogue_feedback=pedagogue_feedback_summary # Sending summary
        )
        
        # Structured Call
        resp, in_tok, out_tok, cost = self.structured_client.generate_structured(
            response_model=EditorResponse,
            system_prompt=self.editor.get_system_prompt(),
            user_content=editor_prompt,
            model=self.editor.model
        )
        
        self._update_costs(cost, self.editor.model)
        
        if not resp:
            yield self.yield_event("Editor", self.editor.model, status="Error", content="Editor failed.")
            return

        # Apply edits (Robust)
        replacements = resp.replacements
        new_draft, applied_count = self._apply_robust_edits(self.state["draft"], replacements)
        self.state["draft"] = new_draft
        
        yield self.yield_event("Editor", self.editor.model, f"Applied {applied_count} fixes", 
                              content=resp.model_dump_json(indent=2), tokens=(in_tok, out_tok), cost=cost)
        
        yield self.yield_event("Orchestrator", "System", "Draft Updated", content=new_draft)

    def _node_sanitizer(self):
        sanitizer_prompt = self.sanitizer.format_user_prompt(self.state["draft"])
        final_content, in_tok, out_tok = self.client.generate_response(
            system_prompt=self.sanitizer.get_system_prompt(),
            user_content=sanitizer_prompt,
            model=self.sanitizer.model
        )
        
        if final_content:
            cost = self.client.calculate_cost(in_tok, out_tok, self.sanitizer.model)
            self._update_costs(cost, self.sanitizer.model)
            self.state["draft"] = final_content
            yield self.yield_event("Sanitizer", self.sanitizer.model, "Polish Complete", content=final_content, tokens=(in_tok, out_tok), cost=cost)
        else:
            yield self.yield_event("Sanitizer", self.sanitizer.model, status="Error", content="Sanitizer failed.")

    def _node_save_and_finalize(self, topic, mode, transcript):
        filename_base = get_timestamp_filename(topic, mode.replace(" ", ""))
        final_draft = self.state["draft"]
        full_path = ""
        
        if mode == "Assignment":
            try:
                data = json.loads(clean_json_string(final_draft))
                # Smart Unwrapping
                if isinstance(data, dict):
                    # Check for common keys LLMs use to wrap lists
                    for key in ["questions", "quiz", "items", "assignment"]:
                        if key in data and isinstance(data[key], list):
                            data = data[key]
                            break
                    # Fallback: if still dict, wrap in list
                    if isinstance(data, dict):
                         data = [data]
                
                full_path = save_excel(data, filename_base)
                save_markdown_file(final_draft, filename_base.replace(".xlsx", ".json"), "Assignments")
            except Exception as e:
                logger.error(f"Assignment save error: {e}")
                yield self.yield_event("Orchestrator", "System", "Error converting to Excel. Saving as Markdown.")
                full_path = save_markdown_file(final_draft, filename_base.replace(".xlsx", ".md"), "Assignments")
        else:
            full_path = save_markdown_file(final_draft, filename_base)
            
        metadata = {
            "models_used": list(self.state["used_models"]),
            "total_cost": round(self.state["costs"], 4),
            "transcript_source": "User Upload" if transcript else "None",
            "iterations": self.state["iteration"]
        }
        
        save_metadata(metadata, filename_base, subfolder="Assignments" if mode == "Assignment" else "Lecture-Notes")
        yield self.yield_event("Orchestrator", "System", "Complete!")
        
        yield {
            "content": final_draft,
            "cost": self.state["costs"],
            "path": full_path,
            "metadata": metadata,
            "type": "FINAL_RESULT"
        }

    def _should_stop_early(self):
        # Decision Logic: If quality > 90 and critical issues == 0
        if not self.state["audit_result"]: return False
        
        quality = self.state["audit_result"].quality_score
        critiques = self.state["audit_result"].critiques
        
        critical_issues = [c for c in critiques if c.severity == "Critical"]
        
        if quality >= 90 and len(critical_issues) == 0:
            return True
        return False

    def _run_audit_structured(self, draft, transcript):
        prompt_transcript_val = "" 
        if not transcript:
             prompt_transcript_val = "No transcript provided. Critique based on logical flow and general accuracy."
        
        # We pass prompt_transcript_val to the template so explicit text is only there if cache is missing
        prompt = self.auditor.format_user_prompt(draft, prompt_transcript_val)
        
        resp, in_tok, out_tok, cost = self.structured_client.generate_structured(
            response_model=AuditResult,
            system_prompt=self.auditor.get_system_prompt(),
            user_content=prompt,
            model=self.auditor.model,
            cache_content=transcript # This triggers caching prefix
        )
        return {"data": resp, "cost": cost}

    def _run_pedagogue_structured(self, draft, target_audience):
        prompt = self.pedagogue.format_user_prompt(draft, target_audience)
        
        resp, in_tok, out_tok, cost = self.structured_client.generate_structured(
            response_model=PedagogueAnalysis,
            system_prompt=self.pedagogue.get_system_prompt(),
            user_content=prompt,
            model=self.pedagogue.model
        )
        return {"data": resp, "cost": cost}
    def refine_content(self, current_draft: str, instruction: str):
        """
        Single-shot refinement based on user instruction.
        Returns: (new_draft, cost)
        """
        prompt = self.editor.format_instruction_prompt(current_draft, instruction)
        
        resp, in_tok, out_tok, cost = self.structured_client.generate_structured(
            response_model=EditorResponse,
            system_prompt=self.editor.get_system_prompt(),
            user_content=prompt,
            model=self.editor.model
        )
        
        if not resp:
            return current_draft, 0.0
            
        new_draft, count = self._apply_robust_edits(current_draft, resp.replacements)
        
        return new_draft, cost
