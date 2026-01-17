import json
import threading
from concurrent.futures import ThreadPoolExecutor

from core.logger import logger
from core.config import DEFAULT_MODEL
from core.client import AnthropicClient
from core.utils import save_markdown_file, save_metadata, get_timestamp_filename, save_excel
from agents.definitions import (
    CreatorAgent, AuditorAgent, PedagogueAgent, SanitizerAgent, EditorAgent
)

class Orchestrator:
    def __init__(self, api_key=None, base_model=DEFAULT_MODEL):
        logger.info(f"Initializing Orchestrator with model: {base_model}")
        self.client = AnthropicClient(api_key)
        
        # Use base_model for all agents to ensure consistency and avoid 404s
        self.creator = CreatorAgent(model=base_model)
        self.auditor = AuditorAgent(model=base_model)
        self.pedagogue = PedagogueAgent(model=base_model)
        self.editor = EditorAgent(model=base_model)
        self.sanitizer = SanitizerAgent(model=base_model)
    
    def run_loop(self, topic: str, subtopics: str, transcript: str = None, mode: str = "Lecture Notes", max_iterations: int = 3):
        """
        Main execution loop.
        Yields status updates to the UI.
        Last yield is the final result dict.
        """
        costs = 0.0
        used_models = set()
        
        def yield_event(agent_name, model_name, status, content=None, tokens=None, cost=0.0):
            return {
                "type": "step",
                "agent": agent_name,
                "model": model_name,
                "status": status,
                "content": content,
                "tokens": tokens or (0,0),
                "cost": cost
            }
        
        # 1. Drafting
        yield yield_event("Creator", self.creator.model, f"Creating V1 Draft ({mode})...")
        
        if mode == "Assignment":
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
            cache_content=transcript # Cache transcript if provided
        )
        
        if not draft:
            yield {"type": "error", "message": "Failed to generate draft (API Error)."}
            return

        step_cost = self.client.calculate_cost(in_tok, out_tok, self.creator.model)
        costs += step_cost
        used_models.add(self.creator.model)
        
        yield yield_event("Creator", self.creator.model, "Draft Generated", content=draft, tokens=(in_tok, out_tok), cost=step_cost)
        
        current_draft = draft
        iteration = 0
        
        if mode == "Assignment":
            # Just sanitize/validate JSON
            yield yield_event("Orchestrator", "System", "Validating Assignment JSON...", content=current_draft)
             
        else:
            # Normal Text Loop
            while iteration < max_iterations:
                iteration += 1
                yield yield_event("Orchestrator", "System", f"Iteration {iteration}: Critiquing...")
                
                # 2. Parallel Critique
                with ThreadPoolExecutor(max_workers=2) as executor:
                    future_audit = executor.submit(self._run_audit, current_draft, transcript)
                    future_pedagogue = executor.submit(self._run_pedagogue, current_draft)
                    
                    audit_result = future_audit.result()
                    pedagogue_result = future_pedagogue.result()
                
                # Report Costs & Findings
                costs += audit_result['cost']
                costs += pedagogue_result['cost']
                used_models.add(self.auditor.model)
                used_models.add(self.pedagogue.model)
                
                yield yield_event("Auditor", self.auditor.model, f"Found {len(audit_result['json'])} issues", 
                                  content=json.dumps(audit_result['json'], indent=2), cost=audit_result['cost'])
                                  
                yield yield_event("Pedagogue", self.pedagogue.model, "Analysis Complete",
                                  content=json.dumps(pedagogue_result['json'], indent=2), cost=pedagogue_result['cost'])
                
                audit_json = audit_result['json']
                pedagogue_json = pedagogue_result['json']
                
                # 3. Decision Gate
                has_errors = len(audit_json) > 0
                
                if not has_errors and iteration > 1:
                    yield yield_event("Orchestrator", "System", "Critique Clean. Breaking loop.")
                    break
                    
                if iteration == max_iterations:
                    yield yield_event("Orchestrator", "System", "Max iterations reached.")
                    break

                # 4. Refining
                yield yield_event("Orchestrator", "System", f"Iteration {iteration}: Refining...")
                
                editor_prompt = self.editor.format_user_prompt(
                    draft=current_draft,
                    audit_feedback=json.dumps(audit_json, indent=2),
                    pedagogue_feedback=json.dumps(pedagogue_json, indent=2)
                )
                
                edits_json_str, in_tok, out_tok = self.client.generate_response(
                    system_prompt=self.editor.get_system_prompt(),
                    user_content=editor_prompt,
                    model=self.editor.model
                )
                
                if not edits_json_str:
                    yield yield_event("Editor", self.editor.model, "Editor failed to respond.", status="Error")
                    continue

                step_cost = self.client.calculate_cost(in_tok, out_tok, self.editor.model)
                costs += step_cost
                used_models.add(self.editor.model)
                
                try:
                    edits = json.loads(edits_json_str)
                    replacements = edits.get("replacements", [])
                    new_draft = current_draft
                    applied_count = 0
                    for item in replacements:
                        if item["target_text"] in new_draft:
                            new_draft = new_draft.replace(item["target_text"], item["replacement_text"])
                            applied_count += 1
                    current_draft = new_draft
                    
                    yield yield_event("Editor", self.editor.model, f"Applied {applied_count} fixes", 
                                      content=json.dumps(edits, indent=2), tokens=(in_tok, out_tok), cost=step_cost)
                                      
                    yield yield_event("Orchestrator", "System", "Draft Updated", content=current_draft)

                except json.JSONDecodeError:
                    yield yield_event("Editor", self.editor.model, "Failed to parse edits", cost=step_cost)

            # 5. Final Polish (Sanitizer)
            yield yield_event("Sanitizer", self.sanitizer.model, "Final Polish...")
            sanitizer_prompt = self.sanitizer.format_user_prompt(current_draft)
            final_content, in_tok, out_tok = self.client.generate_response(
                system_prompt=self.sanitizer.get_system_prompt(),
                user_content=sanitizer_prompt,
                model=self.sanitizer.model
            )
            
            if final_content:
                step_cost = self.client.calculate_cost(in_tok, out_tok, self.sanitizer.model)
                costs += step_cost
                used_models.add(self.sanitizer.model)
                current_draft = final_content
                yield yield_event("Sanitizer", self.sanitizer.model, "Polish Complete", content=final_content, tokens=(in_tok, out_tok), cost=step_cost)
            else:
                yield yield_event("Sanitizer", self.sanitizer.model, "Sanitizer failed (API Error).", status="Error")
            
        # 6. Save & Return
        filename_base = get_timestamp_filename(topic, mode.replace(" ", ""))
        
        full_path = ""
        if mode == "Assignment":
            try:
                data = json.loads(current_draft)
                full_path = save_excel(data, filename_base)
                save_markdown_file(current_draft, filename_base.replace(".xlsx", ".json"), "Assignments")
            except:
                yield yield_event("Orchestrator", "System", "Error converting to Excel. Saving as Markdown.")
                full_path = save_markdown_file(current_draft, filename_base.replace(".xlsx", ".md"), "Assignments")
        else:
            full_path = save_markdown_file(current_draft, filename_base)
        
        metadata = {
            "models_used": list(used_models),
            "total_cost": round(costs, 4),
            "transcript_source": "User Upload" if transcript else "None",
            "iterations": iteration
        }
        
        save_metadata(metadata, filename_base, subfolder="Assignments" if mode == "Assignment" else "Lecture-Notes")
        yield yield_event("Orchestrator", "System", "Complete!")
        
        # Final Yield is the Result Dict
        yield {
            "content": current_draft,
            "cost": costs,
            "path": full_path,
            "metadata": metadata,
            "type": "FINAL_RESULT"
        }

    def _repair_json(self, json_str):
        """
        Attempts to repair and parse a broken JSON string.
        """
        if not json_str: return None
        
        # 0. Simple attempt
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
            
        # 1. Strip markdown code blocks (standard)
        clean = json_str.replace("```json", "").replace("```", "").strip()
        
        # 2. Aggressive Cleanup: Remove any text before the first '[' or '{'
        # Often LLMs say "Here is the JSON: \n [..."
        import re
        
        # Find first [ or {
        match = re.search(r'[\[\{]', clean)
        if match:
            clean = clean[match.start():]
        
        # Find last ] or }
        # We need to cover both cases (list or dict)
        last_bracket = clean.rfind("]")
        last_brace = clean.rfind("}")
        
        cutoff = max(last_bracket, last_brace)
        if cutoff != -1:
             clean = clean[:cutoff+1]
        
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            return None

    def _run_audit(self, draft, transcript):
        if not transcript:
            return {'json': [], 'cost': 0.0}
            
        prompt = self.auditor.format_user_prompt(draft, transcript)
        resp, in_tok, out_tok = self.client.generate_response(
            system_prompt=self.auditor.get_system_prompt(),
            user_content=prompt,
            model=self.auditor.model
        )
        cost = self.client.calculate_cost(in_tok, out_tok, self.auditor.model)
        
        parsed = self._repair_json(resp)
        if parsed is not None:
             return {'json': parsed, 'cost': cost}
        
        return {'json': [{"error": "Failed to parse Auditor output", "raw": resp}], 'cost': cost}

    def _run_pedagogue(self, draft):
        prompt = self.pedagogue.format_user_prompt(draft)
        resp, in_tok, out_tok = self.client.generate_response(
            system_prompt=self.pedagogue.get_system_prompt(),
            user_content=prompt,
            model=self.pedagogue.model
        )
        cost = self.client.calculate_cost(in_tok, out_tok, self.pedagogue.model)
        
        parsed = self._repair_json(resp)
        if parsed is not None:
             return {'json': parsed, 'cost': cost}
             
        return {'json': {"error": "Failed to parse Pedagogue output", "raw": resp}, 'cost': cost}
