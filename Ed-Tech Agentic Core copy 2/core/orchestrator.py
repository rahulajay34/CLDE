import json
import asyncio
import time
import os
from typing import Optional, Dict, Any, List

from core.logger import logger
from core.config import DEFAULT_MODEL
from core.client import AnthropicClient
from core.structured_client import StructuredClient
from core.utils import save_markdown_file, save_metadata, get_timestamp_filename, save_excel
from agents.definitions import (
    CreatorAgent, AuditorAgent, PedagogueAgent, SanitizerAgent, EditorAgent
)
from core.models import (
    AuditResult, PedagogueAnalysis, EditorResponse, AssignmentBatch,
    MCSCBatch, MCMCBatch, SubjectiveBatch
)
from core.version_manager import VersionManager
import re
import difflib

def clean_json_string(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```json\s*|^```\s*|```$", "", text, flags=re.MULTILINE)
    return text.strip()


from core.state_manager import StateManager

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
        """Applies edits with exact, regex, and fuzzy matching."""
        new_text = text
        applied_count = 0
        
        for item in replacements:
            # 1. Exact Match
            if item.target_text in new_text:
                new_text = new_text.replace(item.target_text, item.replacement_text, 1) # Only replace first occurrence
                applied_count += 1
                continue
                
            # 2. Robust Regex (Whitespace agnostic)
            pattern = re.escape(item.target_text)
            pattern = pattern.replace(" ", r"\s+") 
            match = re.search(pattern, new_text)
            if match:
                 new_text = new_text[:match.start()] + item.replacement_text + new_text[match.end():]
                 applied_count += 1
                 continue
                 
            # 3. Fuzzy Match (Sliding Window)
            target_len = len(item.target_text)
            if target_len < 10: # Skip fuzzy for very short targets to avoid false positives
                 logger.warning(f"Editor target not found (Too short for fuzzy): {item.target_text[:30]}...")
                 continue

            best_ratio = 0.0
            best_idx = -1
            
            # Helper to check a window
            def check_window(idx):
                window = new_text[idx : idx + target_len]
                return difflib.SequenceMatcher(None, window, item.target_text).ratio()

            # Coarse scan (Step 10% of length)
            step = max(1, int(target_len * 0.1))
            for i in range(0, len(new_text) - target_len + 1, step):
                ratio = check_window(i)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_idx = i
            
            # Fine alignment around best match
            if best_idx != -1:
                start_scan = max(0, best_idx - step)
                end_scan = min(len(new_text) - target_len, best_idx + step)
                for i in range(start_scan, end_scan + 1):
                    ratio = check_window(i)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_idx = i

            threshold = 0.80
            if best_ratio >= threshold:
                logger.info(f"Fuzzy match applied ({best_ratio:.2f}) for: {item.target_text[:20]}...")
                new_text = new_text[:best_idx] + item.replacement_text + new_text[best_idx + target_len:]
                applied_count += 1
            else:
                logger.warning(f"Editor target not found (Best match: {best_ratio:.2f}): {item.target_text[:30]}...")

        return new_text, applied_count

    def yield_event(self, agent_name, model_name, status, content=None, tokens=None, cost=0.0, **kwargs):
        event = {
            "type": kwargs.get("type", "step"),
            "agent": agent_name,
            "model": model_name,
            "status": status,
            "content": content,
            "tokens": tokens or (0,0),
            "cost": cost
        }
        # Merge extra kwargs
        for k, v in kwargs.items():
            if k != "type":
                event[k] = v
        return event

    def _update_costs(self, cost, model):
        self.state["costs"] += cost
        self.state["used_models"].add(model)

    async def run_loop(self, topic: str, subtopics: str, transcript: str = None, mode: str = "Lecture Notes", target_audience: str = "General Student", **kwargs):
        """
        Main execution loop implemented as a State Machine.
        """
        # Reset State
        self.state["draft"] = ""
        self.state["iteration"] = 0
        self.state["costs"] = 0.0
        self.state["used_models"] = set()
        
        assignment_config = kwargs.get("assignment_config", {})
        self.state["assignment_config"] = assignment_config
        
        max_iterations = self.config.max_iterations
        
        # --- Node 1: Creator ---
        async for event in self._node_creator(topic, subtopics, transcript, mode):
            yield event
            
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
                
                # Check for stop signal
                if StateManager.get_session_val("stop_signal"):
                    yield self.yield_event("Orchestrator", "System", "Generation stopped by user.")
                    break

                # --- Node 2: Parallel Critique (Auditor & Pedagogue) ---
                # Detailed status moved inside the node
                async for event in self._node_critique_parallel(transcript, target_audience, run_pedagogue):
                    yield event
                
                # --- Node 3: Decision Gate ---
                if self._should_stop_early():
                    yield self.yield_event("Orchestrator", "System", "Critique Clean. Breaking loop.")
                    break
                
                if self.state["iteration"] == max_iterations:
                    yield self.yield_event("Orchestrator", "System", "Max iterations reached. Skipping final edit.")
                    break

                # --- Node 4: Editor ---
                # --- Node 4: Editor ---
                # Status yielded inside _node_editor for granularity
                async for event in self._node_editor():
                    yield event

            # --- Node 5: Sanitizer REMOVED for Cost Optimization ---

        # --- Node 6: Save & Return ---
        async for event in self._node_save_and_finalize(topic, mode):
            yield event

    # ==========================
    # Node Implementations
    # ==========================

    async def _node_creator(self, topic, subtopics, transcript, mode):
        try:
            # Create a concise subtopic summary (first 3 words of first 2 subtopics)
            sub_preview = ", ".join([s.strip()[:20] for s in subtopics.split(",")[:2]]) if subtopics else topic
            yield self.yield_event("Creator", self.creator.model, f"Drafting: {mode} covering {sub_preview}...")
            
            if mode == "Assignment":
                 # Structured Batch Generation based on Config
                 assignment_config = self.state.get("assignment_config", {})
                 
                 # Default if empty
                 if not assignment_config:
                     assignment_config = {"mcsc": 5, "mcmc": 0, "subjective": 0}

                 all_questions = []
                 total_cost = 0.0

                 # 1. MCSC (Multiple Choice Single Correct)
                 n_mcsc = assignment_config.get("mcsc", 0)
                 if n_mcsc > 0:
                     prompt = f"""Create {n_mcsc} Multiple Choice Questions (Single Correct) for:
Topic: {topic}
Subtopics: {subtopics}
Ensure 4 options per question."""
                     yield self.yield_event("Creator", self.creator.model, f"Drafting {n_mcsc} MCSC questions...")
                     resp, _, _, cost = await self.structured_client.generate_structured(
                        response_model=MCSCBatch,
                        system_prompt=self.creator.get_system_prompt(),
                        user_content=prompt,
                        model=self.creator.model,
                        cache_content=transcript
                     )
                     if resp and resp.questions:
                         for q in resp.questions:
                             q_dict = q.model_dump()
                             all_questions.append(q_dict)
                     total_cost += cost

                 # 2. MCMC (Multiple Choice Multi Correct)
                 n_mcmc = assignment_config.get("mcmc", 0)
                 if n_mcmc > 0:
                     prompt = f"""Create {n_mcmc} Multiple Choice Questions (Multi Correct) for:
Topic: {topic}
Subtopics: {subtopics}
Ensure 4 options per question."""
                     yield self.yield_event("Creator", self.creator.model, f"Drafting {n_mcmc} MCMC questions...")
                     resp, _, _, cost = await self.structured_client.generate_structured(
                        response_model=MCMCBatch,
                        system_prompt=self.creator.get_system_prompt(),
                        user_content=prompt,
                        model=self.creator.model,
                        cache_content=transcript
                     )
                     if resp and resp.questions:
                         for q in resp.questions:
                             q_dict = q.model_dump()
                             all_questions.append(q_dict)
                     total_cost += cost

                 # 3. Subjective
                 n_subj = assignment_config.get("subjective", 0)
                 if n_subj > 0:
                     prompt = f"""Create {n_subj} Subjective/Descriptive Questions for:
Topic: {topic}
Subtopics: {subtopics}"""
                     yield self.yield_event("Creator", self.creator.model, f"Drafting {n_subj} Subjective questions...")
                     resp, _, _, cost = await self.structured_client.generate_structured(
                        response_model=SubjectiveBatch,
                        system_prompt=self.creator.get_system_prompt(),
                        user_content=prompt,
                        model=self.creator.model,
                        cache_content=transcript
                     )
                     if resp and resp.questions:
                         for q in resp.questions:
                             q_dict = q.model_dump()
                             all_questions.append(q_dict)
                     total_cost += cost
                 
                 draft = json.dumps(all_questions, indent=2)
                 self._update_costs(total_cost, self.creator.model)
                 self.state["draft"] = draft
                 yield self.yield_event("Creator", self.creator.model, f"Batch Generated ({len(all_questions)} items)", content=draft, cost=total_cost)
                 return
            
            elif mode == "Pre-read Notes":
                # Special Pre-read Prompt
                creator_prompt = self.creator.format_preread_prompt(topic, subtopics)
                draft = ""
                in_tok = 0
                
                async for chunk in self.client.generate_stream(
                    system_prompt=self.creator.get_system_prompt(),
                    user_content=creator_prompt,
                    model=self.creator.model
                ):
                    draft += chunk
                    yield {"type": "stream", "content": chunk, "agent": "Creator"}
                    
                in_tok = len(creator_prompt) // 4
                out_tok = len(draft) // 4

            else:
                creator_prompt = self.creator.format_user_prompt(topic, subtopics)
                draft = ""
                in_tok = 0
                
                async for chunk in self.client.generate_stream(
                    system_prompt=self.creator.get_system_prompt(),
                    user_content=creator_prompt,
                    model=self.creator.model
                ):
                    draft += chunk
                    yield {"type": "stream", "content": chunk, "agent": "Creator"}
                    
                in_tok = len(creator_prompt) // 4
                out_tok = len(draft) // 4
                
            if not draft:
                logger.error("Creator failed to generate draft.")
                yield {"type": "error", "message": "Failed to generate draft."}
                return
    
            cost = self.client.calculate_cost(in_tok, out_tok, self.creator.model)
            self._update_costs(cost, self.creator.model)
            
            self.state["draft"] = draft
            yield self.yield_event("Creator", self.creator.model, "Draft Generated", content=draft, tokens=(in_tok, out_tok), cost=cost)

        except Exception as e:
            logger.error(f"Creator Node Error: {e}", exc_info=True)
            yield {"type": "error", "message": f"Critical Error in Creator: {str(e)}"}

    async def _node_critique_parallel(self, transcript, target_audience, run_pedagogue=True):
        # Yield status with specific checks
        yield self.yield_event("Auditor", self.auditor.model, "Auditing: checking facts, code, and structure...")
        if run_pedagogue:
             yield self.yield_event("Pedagogue", self.pedagogue.model, f"Analyzing: engagement for '{target_audience}'...")

        # Async parallel execution using asyncio.gather with robustness
        # 2.1 Caching Strategy: Combine transcript and draft into structured XML
        cache_payload = ""
        if transcript:
            cache_payload += f"<transcript>\n{transcript}\n</transcript>\n"
        cache_payload += f"<current_draft>\n{self.state['draft']}\n</current_draft>"

        # Async parallel execution using asyncio.gather with robustness
        tasks = [self._run_audit_structured(self.state["draft"], transcript, cache_context=cache_payload)]
        if run_pedagogue:
            tasks.append(self._run_pedagogue_structured(self.state["draft"], target_audience, cache_context=cache_payload))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 1. Handle Auditor Result
        audit_res = results[0]
        if isinstance(audit_res, Exception):
            logger.error(f"Auditor failed: {audit_res}")
            # Fallback to empty result, preventing crash
            audit_res = {"data": None, "cost": 0.0}
            
        self.state["audit_result"] = audit_res["data"]
        self._update_costs(audit_res["cost"], self.auditor.model)
        
        # 2. Handle Pedagogue Result
        pedagogue_res = None
        if run_pedagogue and len(results) > 1:
            pedagogue_res = results[1]
            if isinstance(pedagogue_res, Exception):
                 logger.error(f"Pedagogue failed: {pedagogue_res}")
                 pedagogue_res = {"data": None, "cost": 0.0}

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

    def _compress_feedback(self, audit_result):
        """Refines feedback to top 5 prioritized issues."""
        if not audit_result or not audit_result.critiques:
            return "No issues found."

        severity_map = {"Critical": 0, "Major": 1, "Minor": 2, "Nitpick": 3}
        
        # 1. Flatten and Prioritize
        candidates = []
        for c in audit_result.critiques:
            prio = severity_map.get(c.severity, 4)
            # Ultra-compact format: "Section: Issue -> Fix"
            compact_text = f"{c.section}: {c.issue} -> {c.suggestion}"
            candidates.append({"prio": prio, "text": compact_text, "original": c})

        # 2. Sort by Severity
        candidates.sort(key=lambda x: x["prio"])
        
        # 3. Prune (Keep top 5)
        top_items = candidates[:5]
        
        return "\n".join([f"- {item['text']}" for item in top_items])

    async def _node_editor(self):
        try:
            # OPTIMIZATION: Prune Feedback to save tokens and prevent context pollution
            audit_data = self.state["audit_result"]
            ped_data = self.state["pedagogue_result"]
    
            # Use compressed feedback
            feedback_summary = self._compress_feedback(audit_data)
            
            # Status update (Use top issues)
            if audit_data and audit_data.critiques:
                 top_issues = [f"{c.section} ({c.issue})" for c in audit_data.critiques if c.severity in ["Critical", "Major"]][:3]
                 if top_issues:
                     yield self.yield_event("Editor", self.editor.model, f"Fixing: {' • '.join(top_issues)}")
                 else:
                     yield self.yield_event("Editor", self.editor.model, "Polishing: Improving clarity...")
            else:
                 yield self.yield_event("Editor", self.editor.model, "Polishing: Improving clarity...")
    
            pedagogue_feedback_summary = ""
            # Optimize Pedagogue Feedback as well to avoid pollution
            if ped_data and ped_data.engagement_score < 80:
                 # Extract specific points if available, otherwise fallback to assessment, limit to top 3
                 if hasattr(ped_data, "points") and ped_data.points:
                     ped_points = [f"- {p.suggestion}" for p in ped_data.points if p.feedback_type in ["Engagement", "Clarity"]]
                     pedagogue_feedback_summary = "PEDAGOGICAL IMPROVEMENTS:\n" + "\n".join(ped_points[:3]) 
                 else:
                     pedagogue_feedback_summary = f"PEDAGOGICAL NOTE: {ped_data.overall_assessment}"
    
            editor_prompt = self.editor.format_user_prompt(
                draft=self.state["draft"],
                audit_feedback=feedback_summary, 
                pedagogue_feedback=pedagogue_feedback_summary 
            )
            
            # Structured Call
            resp, in_tok, out_tok, cost = await self.structured_client.generate_structured(
                response_model=EditorResponse,
                system_prompt=self.editor.get_system_prompt(),
                user_content=editor_prompt,
                model=self.editor.model
            )
            
            self._update_costs(cost, self.editor.model)
            
            if not resp:
                # GRACEFUL DEGRADATION: If structured editor fails, keep previous draft
                logger.warning("Editor API returned None. Skipping edits.")
                yield self.yield_event("Editor", self.editor.model, status="Warning", content="Editor API failed. Skipping iteration.")
                return
    
            # Apply edits (Robust)
            replacements = resp.replacements
            if not replacements:
                logger.info("Editor proposed no changes.")
                yield self.yield_event("Editor", self.editor.model, "No changes needed.")
                return

            new_draft, applied_count = self._apply_robust_edits(self.state["draft"], replacements)
            
            # Determine success based on applied edits
            if applied_count == 0 and replacements:
                 logger.warning("Editor proposed changes but none could be applied (Target Mismatch).")
                 yield self.yield_event("Editor", self.editor.model, status="Warning", content="Could not apply strict edits. Keeping draft.")
            else:
                 self.state["draft"] = new_draft
                 yield self.yield_event("Editor", self.editor.model, f"Applied {applied_count} fixes", 
                                       content=resp.model_dump_json(indent=2), tokens=(in_tok, out_tok), cost=cost)
                 yield self.yield_event("Orchestrator", "System", "Draft Updated", content=new_draft)

        except Exception as e:
            logger.error(f"Editor Node Error: {e}", exc_info=True)
            # Fallback: maintain current draft
            yield self.yield_event("Editor", self.editor.model, status="Error", content=f"Editor logic failed: {str(e)}. Keeping draft.")

    async def _node_sanitizer(self):
        sanitizer_prompt = self.sanitizer.format_user_prompt(self.state["draft"])
        final_content, in_tok, out_tok = await self.client.generate_response(
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

    async def _node_save_and_finalize(self, topic, mode):
        """
        Saves the file to disk and returns the final result.
        Now also creates a Version History checkpoint.
        """
        content = self.state["draft"]
        
        filepath = ""
        
        if mode == "Assignment":
            # --- CSV Export Logic ---
            try:
                import pandas as pd
                questions = json.loads(content)
                rows = []
                
                for q in questions:
                    row = {
                        "questionType": q.get("type", "mcsc"),
                        "contentType": "markdown",
                        "contentBody": q.get("question_text", ""),
                        "intAnswer": "",
                        "prepTime(in_seconds)": "",
                        "floatAnswer.max": "",
                        "floatAnswer.min": "",
                        "fitbAnswer": "",
                        "mcscAnswer": "",
                        "subjectiveAnswer": "",
                        "option.1": "",
                        "option.2": "",
                        "option.3": "",
                        "option.4": "",
                        "mcmcAnswer": "",
                        "tagRelationships": "",
                        "difficultyLevel": q.get("difficulty", "Medium"),
                        "answerExplanation": q.get("explanation", "")
                    }
                    
                    q_type = q.get("type")
                    
                    if q_type == "mcsc":
                        opts = q.get("options", [])
                        for i, opt in enumerate(opts):
                            if i < 4:
                                row[f"option.{i+1}"] = opt
                        row["mcscAnswer"] = q.get("correct_option_index", "")
                        
                    elif q_type == "mcmc":
                        opts = q.get("options", [])
                        for i, opt in enumerate(opts):
                            if i < 4:
                                row[f"option.{i+1}"] = opt
                        indices = q.get("correct_option_indices", [])
                        if isinstance(indices, list):
                            row["mcmcAnswer"] = ", ".join(map(str, indices))
                        else:
                            row["mcmcAnswer"] = str(indices)
                            
                    elif q_type == "subjective":
                        row["subjectiveAnswer"] = q.get("model_answer", "")
                        
                    rows.append(row)
                    
                df = pd.DataFrame(rows)
                
                # Reorder columns to match template exactly
                cols = ["questionType", "contentType", "contentBody", "intAnswer", "prepTime(in_seconds)", 
                        "floatAnswer.max", "floatAnswer.min", "fitbAnswer", "mcscAnswer", "subjectiveAnswer", 
                        "option.1", "option.2", "option.3", "option.4", "mcmcAnswer", "tagRelationships", 
                        "difficultyLevel", "answerExplanation"]
                
                # Ensure all cols exist
                for c in cols:
                    if c not in df.columns:
                        df[c] = ""
                        
                df = df[cols]
                
                filename = f"{topic.replace(' ', '_')}_Assignment_{int(time.time())}.csv"
                filepath = os.path.join("storage", filename)
                os.makedirs("storage", exist_ok=True)
                df.to_csv(filepath, index=False)
                
            except Exception as e:
                logger.error(f"Failed to export CSV: {e}")
                # Fallback to json dump
                filename = f"{topic.replace(' ', '_')}_{int(time.time())}.json"
                filepath = os.path.join("storage", filename)
                os.makedirs("storage", exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
        else:
            # 1. Clean up excessive newlines
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            # 2. Local File Save
            filename = f"{topic.replace(' ', '_')}_{int(time.time())}.md"
            filepath = os.path.join("storage", filename)
            os.makedirs("storage", exist_ok=True)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
        # 3. Version Control Checkpoint
        VersionManager.save_version(topic, content, mode, summary="Finalized Generation")
        
        # 4. Final Event
        yield self.yield_event("System", "Done", "Final content generated.", content=content, type="FINAL_RESULT", path=filepath)
        yield self.yield_event("Orchestrator", "System", "Complete!")
        
        yield {
            "content": content,
            "cost": self.state["costs"],
            "type": "FINAL_RESULT",
            "path": filepath
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

    async def _run_audit_structured(self, draft, transcript, cache_context=None):
        prompt_draft = draft
        prompt_transcript = transcript or "No transcript provided."
        
        pass_cache = None
        
        if cache_context:
            # Point to cached content to save tokens in the prompt
            prompt_draft = "(Refer to <current_draft> block in cached context)"
            if transcript:
                prompt_transcript = "(Refer to <transcript> block in cached context)"
            pass_cache = cache_context
        elif transcript:
             # Legacy/Fallback behavior just for transcript
             pass_cache = transcript

        prompt = self.auditor.format_user_prompt(prompt_draft, prompt_transcript)
        
        resp, in_tok, out_tok, cost = await self.structured_client.generate_structured(
            response_model=AuditResult,
            system_prompt=self.auditor.get_system_prompt(),
            user_content=prompt,
            model=self.auditor.model,
            cache_content=pass_cache
        )
        return {"data": resp, "cost": cost}

    async def _run_pedagogue_structured(self, draft, target_audience, cache_context=None):
        prompt_draft = draft
        pass_cache = None
        
        if cache_context:
             prompt_draft = "(Refer to <current_draft> block in cached context)"
             pass_cache = cache_context

        prompt = self.pedagogue.format_user_prompt(prompt_draft, target_audience)
        
        resp, in_tok, out_tok, cost = await self.structured_client.generate_structured(
            response_model=PedagogueAnalysis,
            system_prompt=self.pedagogue.get_system_prompt(),
            user_content=prompt,
            model=self.pedagogue.model,
            cache_content=pass_cache
        )
        return {"data": resp, "cost": cost}

    async def refine_content(self, current_draft: str, instruction: str):
        """
        Single-shot refinement based on user instruction.
        Returns: (new_draft, cost)
        """
        prompt = self.editor.format_instruction_prompt(current_draft, instruction)
        
        resp, in_tok, out_tok, cost = await self.structured_client.generate_structured(
            response_model=EditorResponse,
            system_prompt=self.editor.get_system_prompt(),
            user_content=prompt,
            model=self.editor.model
        )
        
        if not resp:
            return current_draft, 0.0
            
        new_draft, count = self._apply_robust_edits(current_draft, resp.replacements)
        
        return new_draft, cost
