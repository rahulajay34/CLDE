import streamlit as st
import os
import json
import pandas as pd
import html
import time
from werkzeug.utils import secure_filename
from core.state_manager import StateManager
from core.models import OrchestratorConfig, AgentConfig
from core.orchestrator import Orchestrator
from core.config import ALLOWED_MODELS
from core.utils import load_recent_files
from ui.components import (
    render_metric_card, render_input_area, 
    render_generation_status, render_skeleton_loader
)
from ui.diff_viewer import render_diff_view
from core.logger import logger
from core.version_manager import VersionManager
from lms_automation import publish_to_lms
from assess_automation import publish_quiz_loop

def render_dashboard():
    """
    The Command Center: Inputs, Stats, Recent Projects.
    Centered Layout ("Search Engine" Style).
    """
    # Spacer for vertical centering
    st.markdown("<div style='height: 5vh;'></div>", unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>What do you want to teach today?</h1>", unsafe_allow_html=True)
    
    # 1. Hero / Inputs (Centered)
    # Use [1, 2, 1] ratio to center the content nicely
    _, col_main, _ = st.columns([1, 2, 1])
    
    with col_main:
        with st.container(border=True):
            # st.markdown('<div class="hero-container">', unsafe_allow_html=True) # REMOVED: Caused layout issues
            topic, subtopics, transcript_text, mode, target_audience, assignment_config = render_input_area()
            
            # Generate Action (Inside the hero container for flow)
            if st.button("✨ Generate Content", type="primary", use_container_width=True):
                # 1. Validation Logic
                error_found = False
                
                # API Key Check
                if not os.getenv("ANTHROPIC_API_KEY"):
                    st.error("API Key not configured. Please add ANTHROPIC_API_KEY to your .env or secrets.")
                    error_found = True
                    
                # Topic Check
                if not topic:
                    st.error("Please enter a topic.")
                    error_found = True
                    
                # Assignment Validation
                if mode == "Assignment" and assignment_config:
                    total_q = assignment_config.get("mcsc", 0) + assignment_config.get("mcmc", 0) + assignment_config.get("subjective", 0)
                    if total_q > 50:
                        st.error("Too many questions! Please reduce total below 50 to prevent timeouts.")
                        error_found = True
                    elif total_q == 0:
                        st.error("Please configure at least one question type.")
                        error_found = True

                if not error_found:
                    # Set Session State for Editor
                    st.session_state.topic = topic
                    st.session_state.subtopics = subtopics
                    st.session_state.transcript_text = transcript_text
                    st.session_state.mode = mode
                    st.session_state.target_audience = target_audience
                    st.session_state.assignment_config = assignment_config
                    
                    st.session_state.trigger_generation = True
                    StateManager.navigate_to("editor")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()
    
    # 2. System Metrics (Moved to Sidebar to reduce noise)
    with st.sidebar:
        st.divider()
        st.caption("SYSTEM METRICS")
        cost = st.session_state.get("total_cost", 0.0)
        files_count = len(load_recent_files(limit=100))
        c1, c2 = st.columns(2)
        c1.metric("Total Cost", f"₹{cost:.4f}")
        c2.metric("Files", f"{files_count}")

    # 3. Recent Projects (Full Width)
    st.caption("RECENT PROJECTS")
    recent_files = load_recent_files(limit=4)
    
    if not recent_files:
        st.info("No recent projects yet. Start creating!")
    
    # Grid Layout for Cards
    cols = st.columns(4)
    for idx, file in enumerate(recent_files):
        with cols[idx]:
            with st.container():
                # Glass card style
                st.markdown(f"""
                <div class="glass-card" style="padding: 1rem; height: 100%;">
                    <div style="font-weight:600; font-size: 0.9rem; margin-bottom:0.3rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{html.escape(file['name'])}</div>
                    <div style="font-size:0.75rem; color:#6B7280;">{file.get('timestamp', 'Just now')}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Open", key=f"open_{idx}", help=file['path'], use_container_width=True):
                     # Load File Logic
                    try:
                        with open(file['path'], 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        mode = "Lecture Notes"
                        if file['path'].endswith(".json"):
                            mode = "Assignment"
                        
                        st.session_state["generated_content"] = {
                            "content": content,
                            "cost": 0.0,
                            "path": file['path'],
                            "type": "FINAL_RESULT"
                        }
                        st.session_state["generated_mode"] = mode
                        StateManager.navigate_to("editor")
                    except Exception as e:
                        st.error(f"Error: {e}")


def render_editor():
    """
    The Main Workspace: Chat, Preview, Diff.
    Layout: Sidebar (Chat/Utility) vs Main (Content).
    """
    # Check if we have anything to work on
    if not st.session_state.get("trigger_generation", False) and "generated_content" not in st.session_state:
        st.info("No active project. Go to Dashboard to start.")
        if st.button("← Back to Dashboard"):
            StateManager.navigate_to("dashboard")
        return

    # Get Configuration
    model_config = st.session_state.get("model_config", {})

    # --- FULL SCREEN PREVIEW TOGGLE ---
    if "fullscreen_preview" not in st.session_state:
        st.session_state.fullscreen_preview = False

    def toggle_preview():
        st.session_state.fullscreen_preview = not st.session_state.fullscreen_preview

    # --- TOP BAR ---
    if not st.session_state.fullscreen_preview:
        col_back, col_title, col_actions = st.columns([1, 6, 2])
        with col_back:
            if st.button("← Back", help="Return to Dashboard"):
                StateManager.navigate_to("dashboard")
        
        with col_title:
             topic = st.session_state.get("topic", "Untitled Project")
             st.markdown(f"<h3 style='margin:0; padding-top: 5px;'>{topic}</h3>", unsafe_allow_html=True)
    else:
        # Minimal Header for Preview Mode
        col_back, col_actions = st.columns([1, 5])
        with col_back:
            if st.button("❌ Close", on_click=toggle_preview):
                pass
        with col_actions:
             st.caption("Press Close or ESC to return to Editor")

    # --- CONTENTS ---
    
    # 1. TRIGGER GENERATION LOGIC
    if st.session_state.get("trigger_generation", False):
        st.session_state.trigger_generation = False # Reset trigger
        
        topic = st.session_state.get("topic")
        subtopics = st.session_state.get("subtopics")
        transcript_text = st.session_state.get("transcript_text")
        mode = st.session_state.get("mode")
        target_audience = st.session_state.get("target_audience")
        
        # Check API Key
        if not os.getenv("ANTHROPIC_API_KEY"):
            st.error("ANTHROPIC_API_KEY not found.")
            return

        # Stop Signal Reset
        st.session_state.stop_signal = False
        
        with st.sidebar:
            if st.button("🛑 Stop Generation", key="stop_gen_btn"):
                st.session_state.stop_signal = True
                # In Streamlit, this triggers a rerun, effectively stopping the script.
                # But we set the flag just in case we want logic to handle it.
            
        # Initialize Orchestrator
        models = st.session_state.get("model_config", {})
        config = OrchestratorConfig(
            creator=AgentConfig(model=models.get("creator", "claude-3-5-sonnet-20241022")),
            auditor=AgentConfig(model=models.get("auditor", "claude-3-5-sonnet-20241022")),
            pedagogue=AgentConfig(model=models.get("auditor", "claude-3-5-sonnet-20241022")), 
            editor=AgentConfig(model=models.get("editor", "claude-3-5-sonnet-20241022")),
            sanitizer=AgentConfig(model=models.get("sanitizer", "claude-3-haiku-20240307")),
            max_iterations=models.get("max_iterations", 3),
            human_in_the_loop=False 
        )
        
        orchestrator = Orchestrator(config=config)
        
        # RAG Logic
        rag_context = ""
        if st.session_state.get("rag_enabled", False) and st.session_state.get("rag_manager"):
             with st.spinner("Searching Knowledge Base..."):
                query = f"{topic} {subtopics}"
                rag_context = st.session_state.rag_manager.retrieve_context(query)
                if rag_context: st.toast(f"Found {len(rag_context)} chars of context")

        combined_context = transcript_text or ""
        if rag_context:
            combined_context += f"\n\n[KNOWLEDGE BASE CONTEXT]:\n{rag_context}"

        # Placeholders
        status_area = st.empty()
        preview_area = st.empty()
        
        # Run Generation
        import asyncio
        final_result = asyncio.run(render_generation_status(
            orchestrator, topic, subtopics, combined_context, mode, target_audience=target_audience,
            status_placeholder=status_area,
            preview_placeholder=preview_area,
            critique_placeholder=None,
            assignment_config=st.session_state.get("assignment_config", {})
        ))
        
        if final_result:
             st.balloons()
             StateManager.add_cost(final_result.get('cost', 0))
             st.session_state["generated_content"] = final_result
             st.session_state["generated_mode"] = mode
             
             st.session_state["generated_content"] = final_result
             st.session_state["generated_mode"] = mode
             
             # RESET manual editor
             if "manual_editor" in st.session_state:
                 del st.session_state["manual_editor"]
             if "manual_editor_widget" in st.session_state:
                 del st.session_state["manual_editor_widget"]
                 
             # Check for verification summary
             if "verification_summary" in st.session_state:
                 summary = st.session_state["verification_summary"]
                 # Display stats balloon-style
                 c1, c2, c3 = st.columns(3)
                 c1.metric("✅ Passed", summary.get("passed", 0))
                 c2.metric("⚠️ Needs Review", summary.get("failed", 0))
                 c3.metric("📊 Total", summary.get("total", 0))
                 time.sleep(3) # Let user see stats before rerun
                 
             st.rerun()

    # 2. EDITING / VIEWING LOGIC
    if "generated_content" in st.session_state:
        result = st.session_state["generated_content"]
        mode_saved = st.session_state.get("generated_mode", "Lecture Notes")
        
        if "manual_editor" not in st.session_state:
             st.session_state.manual_editor = result['content']

        # --- HELPER: PARSE ASSIGNMENT DATA ---
        assignment_df = None
        if mode_saved == "Assignment":
            try:
                content_data = st.session_state.manual_editor
                def parse_assignment_json(content):
                    """Robust JSON extraction with multiple fallback strategies"""
                    # Strategy 1: Direct parse if input is list/dict
                    if isinstance(content, list): return content
                    if isinstance(content, dict): return [content]
                    
                    if not isinstance(content, str):
                        return [] # Should not happen

                    # Strategy 2: Extract from code blocks (standard LLM output)
                    import re
                    json_blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
                    
                    combined = []
                    for block in json_blocks:
                        try:
                            parsed = json.loads(block)
                            if isinstance(parsed, list): combined.extend(parsed)
                            elif isinstance(parsed, dict): combined.append(parsed)
                        except: continue
                    
                    if combined: return combined
                    
                    # Strategy 3: Find raw JSON array
                    array_match = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
                    if array_match:
                        try: return json.loads(array_match.group(0))
                        except: pass

                    # Strategy 4: Try direct parse as last resort
                    try: return json.loads(content)
                    except: pass
                    
                    return []

                content_data = parse_assignment_json(content_data)
                
                if not content_data:
                     # Warn but allow raw editing
                     st.warning("Could not auto-parse assignment JSON. Switching to Markdown view.")
                     assignment_df = None 
                if content_data:
                    # Transform to Template Format
                    if isinstance(content_data, list):
                        rows = []
                        for q in content_data:
                            # Extract basic fields - strict type from model
                            q_type = q.get("type", "mcsc").lower().strip()
                            
                            # Robust Question Text
                            q_text = q.get("question_text") or q.get("question") or q.get("content") or ""
                            
                            # Initialize row with common fields
                            row = {
                                "questionType": q_type,
                                "contentType": "markdown",
                                "contentBody": q_text,
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
                                "answerExplanation": q.get("explanation", ""),
                                "_validation_warning": q.get("_validation_warning", ""), # NEW
                                "_original_issues": str(q.get("_original_issues", "")) # NEW
                            }
                            
                            # Populate specifics based on type
                            if q_type == "mcsc":
                                opts = q.get("options", [])
                                for i, opt in enumerate(opts):
                                    if i < 4:
                                        row[f"option.{i+1}"] = opt
                                
                                # Convert 0-based index to 1-based (Model already returns 1-based, just ensure str)
                                ans_idx = q.get("correct_option_index", "")
                                row["mcscAnswer"] = str(ans_idx)
                                
                            elif q_type == "mcmc":
                                opts = q.get("options", [])
                                for i, opt in enumerate(opts):
                                    if i < 4:
                                        row[f"option.{i+1}"] = opt
                                indices = q.get("correct_option_indices", [])
                                if isinstance(indices, list):
                                    # Model returns 1-based indices
                                    row["mcmcAnswer"] = ", ".join([str(i) for i in indices])
                                else:
                                    row["mcmcAnswer"] = str(indices)
                                    
                            elif q_type == "subjective":
                                # User Request: answerExplanation will contain the Solution of the question
                                # We check multiple keys for the solution/answer
                                solution = q.get("model_answer") or q.get("answer") or q.get("correct_answer") or q.get("explanation") or ""
                                row["answerExplanation"] = solution
                                row["subjectiveAnswer"] = solution # Populate this too just in case
                                
                            rows.append(row)
                        
                        assignment_df = pd.DataFrame(rows)
                        # Set Index to start from 1
                        assignment_df.index = assignment_df.index + 1
                        
                        # Enforce Column Order EXACTLY as per template
                        cols = ["questionType", "contentType", "contentBody", "intAnswer", "prepTime(in_seconds)", 
                                "floatAnswer.max", "floatAnswer.min", "fitbAnswer", "mcscAnswer", "subjectiveAnswer", 
                                "option.1", "option.2", "option.3", "option.4", "mcmcAnswer", "tagRelationships", 
                                "difficultyLevel", "answerExplanation", "_validation_warning"] # Included warning in cols
                        
                        # Add missing columns if any
                        for c in cols:
                            if c not in assignment_df.columns:
                                assignment_df[c] = ""
                        
                        assignment_df = assignment_df[cols]
                        
                        # Ensure all columns are string to prevent PyArrow conversion errors
                        assignment_df = assignment_df.astype(str)
                    else:
                        # Fallback for unexpected structure
                        assignment_df = pd.DataFrame([content_data] if isinstance(content_data, dict) else [])

                # --- DEBUG UI ---
                with st.expander("🛠️ Parsing Debugger (Developer Mode)", expanded=False):
                    st.write(f"Parsed rows: {len(assignment_df) if assignment_df is not None else 'None'}")
                    if assignment_df is not None and not assignment_df.empty:
                        st.dataframe(assignment_df.head())
                    else:
                        st.error("DataFrame is empty or None")
                        st.text("Raw Content Snippet:")
                        st.code(str(st.session_state.manual_editor)[:500])
            except Exception as e:
                logger.error(f"Error parsing assignment JSON: {e}")
                st.error(f"Critical Parsing Error: {e}")
                pass

        # --- FULL SCREEN MODE ---
        if st.session_state.fullscreen_preview:
            # Render Clean View
            if mode_saved == "Assignment" and assignment_df is not None:
                st.subheader("📊 Assignment Table View")
                st.dataframe(assignment_df, use_container_width=True, height=800)
            else:
                # Custom Markdown + Mermaid Rendering
                from ui.components import render_markdown_with_mermaid
                render_markdown_with_mermaid(st.session_state.manual_editor)
            
            return # Skip the rest

        # --- NORMAL SPLIT MODE (Gold Standard Layout) ---
        
        # 0. Sidebar Toggle State
        if "editor_sidebar_collapsed" not in st.session_state:
            st.session_state.editor_sidebar_collapsed = False
            
        def toggle_sidebar():
            st.session_state.editor_sidebar_collapsed = not st.session_state.editor_sidebar_collapsed
            
        # Layout Calculation
        if st.session_state.editor_sidebar_collapsed:
            col_left, col_right = st.columns([0.5, 20])
            left_expanded = False
        else:
            col_left, col_right = st.columns([1, 4]) # Wider Editor area
            left_expanded = True
            
        # --- LEFT COLUMN (Chat / Co-Pilot) ---
        with col_left:
            if not left_expanded:
                # Collapsed State
                st.button("🔍", on_click=toggle_sidebar, help="Expand Co-Pilot")
                st.markdown("<br>"*5, unsafe_allow_html=True)
                # Vertical Text (CSS Hack or just icons)
            else:
                # Expanded State
                c_head, c_btn = st.columns([4, 1])
                c_head.markdown("#### 🧠 Co-Pilot")
                c_btn.button("◀", on_click=toggle_sidebar, help="Collapse")
                
                # Chat Interface
                # Fixed Height Container for Scroll Locking
                chat_container = st.container(height=500, border=True)
                
                with chat_container:
                    if "chat_history" not in st.session_state: st.session_state.chat_history = []
                    
                    if not st.session_state.chat_history:
                        st.caption("No history yet. Ask me to refine the content!")
                    
                    for msg in st.session_state.chat_history:
                        role_icon = "👤" if msg["role"] == "user" else "🤖"
                        bg_color = "rgba(37, 99, 235, 0.1)" if msg["role"] == "assistant" else "transparent"
                        st.markdown(f"""
                        <div style="background:{bg_color}; padding:8px; border-radius:8px; margin-bottom:8px; font-size:0.9rem;">
                            <strong>{role_icon}</strong> {msg['content']}
                        </div>
                        """, unsafe_allow_html=True)
                
                # Chat Input (Bottom of Left Column)
                refine_input = st.chat_input("Refine content (e.g. 'Make it shorter')...")
                if refine_input:
                    st.session_state.chat_history.append({"role": "user", "content": refine_input})
                    
                    # Logic to Refine
                    with st.spinner("Refining..."):
                         models = st.session_state.get("model_config", {})
                         from core.config import DEFAULT_MODEL
                         editor_model = models.get("editor", DEFAULT_MODEL)
                         
                         config = OrchestratorConfig(
                            creator=AgentConfig(model=models.get("creator", DEFAULT_MODEL)),
                            auditor=AgentConfig(model=models.get("auditor", DEFAULT_MODEL)),
                            pedagogue=AgentConfig(model=models.get("pedagogue", DEFAULT_MODEL)),
                            editor=AgentConfig(model=editor_model), 
                            sanitizer=AgentConfig(model=models.get("sanitizer", "claude-3-haiku-20240307")),
                            max_iterations=1,
                            human_in_the_loop=False 
                         )
                         
                         orch = Orchestrator(config=config)
                         current_text = st.session_state.get("manual_editor", result['content'])
                         if isinstance(current_text, dict): current_text = str(current_text)
                         
                         import asyncio
                         new_text, cost = asyncio.run(orch.refine_content(current_text, refine_input))
                         
                         st.session_state.chat_history.append({"role": "assistant", "content": "Updated content based on your request."})
                         StateManager.add_cost(cost)
                         
                         st.session_state["manual_editor"] = new_text
                         st.session_state["manual_editor_widget"] = new_text
                         st.session_state["generated_content"] = {
                             "content": new_text, "cost": result.get("cost", 0) + cost, 
                             "path": result.get("path"), "type": "FINAL_RESULT"
                         }
                         st.rerun()

                # --- VERSION HISTORY (Left Column Bottom) ---
                st.markdown("---")
                with st.expander("clock History / Versions"):
                    topic = st.session_state.get("topic")
                    versions = VersionManager.list_versions(topic)
                    
                    if not versions:
                        st.caption("No history saved yet.")
                    else:
                        for v in versions:
                             ts = v.get("timestamp", "Unknown")
                             v_id = v.get("version_id")
                             summary = v.get("summary", "Snapshot")
                             
                             c_v1, c_v2 = st.columns([3, 1])
                             with c_v1:
                                 st.markdown(f"**{ts}**")
                                 st.caption(summary)
                             with c_v2:
                                 if st.button("Load", key=f"load_v_{v_id}"):
                                     st.session_state.manual_editor = v.get("content")
                                     st.session_state.manual_editor_widget = v.get("content")
                                     st.toast(f"Restored version from {ts}")
                                     st.rerun()

        # --- RIGHT COLUMN (Content) ---
        with col_right:
             # Header for Editor
             if st.session_state.editor_sidebar_collapsed:
                 c_toggle, c_head, c_btn = st.columns([1, 10, 2.5])
                 with c_toggle:
                     if st.button("▶", help="Expand Co-Pilot"):
                         toggle_sidebar()
                         st.rerun()
                 with c_head:
                     st.markdown("#### 📝 Editor & Preview")
                 with c_btn:
                     if st.button("👁️ Fullscreen", help="Toggle Full Screen Overview"):
                         toggle_preview()
                         st.rerun()
             else:
                 c_head, c_btn = st.columns([10, 2])
                 with c_head:
                    st.markdown("#### 📝 Editor & Preview")
                 with c_btn:
                    if st.button("👁️ Fullscreen", help="Toggle Full Screen Overview"):
                         toggle_preview()
                         st.rerun()
             
             # CONDITIONAL EDITOR RENDERING
             if mode_saved == "Assignment" and assignment_df is not None:
                  # Display Validation Warnings
                  if "_validation_warning" in assignment_df.columns:
                       warning_count = assignment_df["_validation_warning"].replace("", pd.NA).dropna().shape[0]
                       if warning_count > 0:
                           st.warning(f"⚠️ {warning_count} questions have validation warnings. Please review the '_validation_warning' column.")

                  st.info("💡 Edit cells directly below.")
                  edited_df = st.data_editor(
                      assignment_df, 
                      use_container_width=True, 
                      num_rows="dynamic",
                      key="assignment_table_editor",
                      height=600,
                      column_config={
                          "_validation_warning": st.column_config.TextColumn(
                              "⚠️ Warnings",
                              help="Validation issues found during generation",
                              width="medium",
                              disabled=True
                          ),
                          "_original_issues": st.column_config.TextColumn(
                                "Debug Info",
                                width="small",
                                disabled=True
                          ),
                          "contentBody": st.column_config.TextColumn(
                                "Question Text",
                                width="large",
                                help="Markdown supported. Use double newlines for paragraphs."
                          ),
                          "answerExplanation": st.column_config.TextColumn(
                                "Explanation / Solution",
                                width="large",
                                help="Markdown supported. Use double newlines for paragraphs."
                          )
                      }
                  )
                  
                  # --- CHECKER INTEGRATION ---
                  c_check, c_export_check = st.columns([1, 4])
                  with c_check:
                      if st.button("🕵️ Run Checker"):
                          from core.checker import AssignmentChecker
                          import asyncio
                          
                          # Retrieve model from config
                          models = st.session_state.get("model_config", {})
                          checker_model = models.get("checker", "claude-haiku-4-5-20251001")
                          
                          checker = AssignmentChecker(model_name=checker_model)
                          
                          # Convert DF back to list of dicts for checking
                          # We need to map back from the CSV format to the JSON format expected by checker
                          # Or we can just pass the "contentBody" and "options" etc.
                          # The CheckerAgent expects the full question JSON.
                          # Let's reconstruct it.
                          
                          questions_to_check = []
                          for idx, row in edited_df.iterrows():
                             q = {
                                 "question_text": row.get("contentBody"),
                                 "options": [row.get(f"option.{i+1}") for i in range(4)],
                                 "correct_answer": row.get("mcscAnswer") if row.get("questionType") == "mcsc" else row.get("mcmcAnswer"),
                                 "explanation": row.get("answerExplanation"),
                                 "type": row.get("questionType")
                             }
                             questions_to_check.append(q)
                             
                          with st.spinner("🕵️ checking for ambiguity and errors..."):
                              report, cost = asyncio.run(checker.check_batch(questions_to_check))
                              StateManager.add_cost(cost)
                              
                          # Display Report
                          st.session_state["checker_report"] = report
                  
                  if "checker_report" in st.session_state:
                      report = st.session_state["checker_report"]
                      error_count = len([r for r in report if r['status'] in ['FAIL', 'ERROR']])
                      warn_count = len([r for r in report if r['status'] == 'WARNING'])
                      
                      if error_count > 0:
                          st.error(f"Found {error_count} Critical Issues!")
                      elif warn_count > 0:
                          st.warning(f"Found {warn_count} Warnings.")
                      else:
                          st.success("All checks passed! ✅")
                          
                      
                      # Auto-Correction Logic
                      actionable_fixes = [item for item in report if item.get("corrected_answer_index") is not None]
                      
                      if actionable_fixes:
                          if st.button(f"✨ Auto-Fix {len(actionable_fixes)} Issues", type="primary"):
                              try:
                                  # 1. Load Current JSON
                                  current_content = st.session_state.manual_editor
                                  if isinstance(current_content, str):
                                      import re
                                      # Extract JSON similar to parsing logic
                                      json_match = re.search(r"```json\s*(.*?)\s*```", current_content, re.DOTALL)
                                      if json_match:
                                          data_str = json_match.group(1)
                                          data = json.loads(data_str)
                                      else:
                                          data = json.loads(current_content)
                                  else:
                                      data = current_content
                                      
                                  # 2. Apply Fixes
                                  # Notes on Indexing:
                                  # - 'idx_0_based': The generic list index for the question mapping (0..N).
                                  # - 'new_ans': The CORRECT OPTION INDEX (1..4) from Checker. 
                                  #   Our data model (MCSCQuestion/MCMC) expects 1-based indexing for options.
                                  
                                  applied_count = 0
                                  changes_log = []
                                  
                                  for fix in actionable_fixes:
                                      idx_1_based = fix.get("index")
                                      idx_0_based = idx_1_based - 1
                                      
                                      if 0 <= idx_0_based < len(data):
                                          # Update Answer
                                          new_ans = fix.get("corrected_answer_index")
                                          q = data[idx_0_based]
                                          old_ans = q.get("correct_option_index", "?")
                                          
                                          if q.get("type") == "mcsc":
                                               q["correct_option_index"] = new_ans
                                               changes_log.append(f"Q{idx_1_based}: Option {old_ans} ➝ Option {new_ans}")
                                               applied_count += 1
                                               
                                          elif q.get("type") == "mcmc":
                                               if isinstance(new_ans, int):
                                                    q["correct_option_indices"] = [new_ans]
                                                    changes_log.append(f"Q{idx_1_based}: Fixed MCMC indices")
                                                    applied_count += 1
                                  
                                  # 3. Save & Refresh
                                  st.session_state.manual_editor = json.dumps(data, indent=2)
                                  # Clear report so we don't show stale errors
                                  del st.session_state["checker_report"]
                                  
                                  if applied_count > 0:
                                      # Show detailed feedback
                                      msg = f"✅ Fixed {applied_count} issues!\n\n" + "\n".join(changes_log)
                                      st.success(msg)
                                      time.sleep(3) # Give time to read before reload
                                  else:
                                      st.warning("No changes needed or indices out of bounds.")
                                      time.sleep(1)
                                      
                                  st.rerun()
                                  
                              except Exception as e:
                                  st.error(f"Failed to apply fixes: {e}")

                      
                      # Dynamic Label for Expander
                      expander_label = f"Detailed Report ({len(report)} items)"
                      with st.expander(expander_label, expanded=True):
                          if not report:
                              st.info("No items in report.")
                          
                          for item in report:
                              status = item.get("status")
                              # Status Icons
                              if status == "PASS":
                                  icon = "✅"
                                  color = "green"
                              elif status == "WARNING":
                                  icon = "⚠️"
                                  color = "orange"
                              else: # FAIL or ERROR
                                  icon = "❌"
                                  color = "red"
                              
                              # Only show issues or failures
                              if status != "PASS":
                                  st.markdown(f":{color}[**Q{item.get('index')} {icon} {status}**]")
                                  
                                  issues = item.get("issues", [])
                                  if issues:
                                      for issue in issues:
                                           st.markdown(f"- {issue}")
                                  else:
                                      st.write("No specific issues text returned.")
                                      
                                  if item.get("corrected_answer_index"):
                                      st.info(f"💡 Suggested Fix: Set Answer to Option {item.get('corrected_answer_index')}")
                                      
                                  if item.get("feedback"):
                                      st.caption(f"Feedback: {item.get('feedback')}")
                                      
                                  st.divider()

             else:
                  # SPLIT VIEW (Side by Side)
                  if "manual_editor_widget" not in st.session_state:
                       st.session_state.manual_editor_widget = st.session_state.manual_editor

                  col_editor, col_preview_pane = st.columns(2)
                  
                  with col_editor:
                      st.markdown("**Markdown Input**")
                      # Live Editor with Ace
                      try:
                          from streamlit_ace import st_ace
                          content = st_ace(
                              value=st.session_state.get("manual_editor", ""),
                              language="markdown",
                              theme="chrome",
                              auto_update=True, # Update on keystroke (debounced)
                              wrap=True, # Enable soft wrapping
                              key="ace_editor_input",
                              height=700
                          )
                          
                          # Sync state
                          if content != st.session_state.get("manual_editor"):
                              st.session_state.manual_editor = content
                              # st.rerun() # Implicitly reruns due to auto_update
                              
                      except ImportError:
                          st.error("streamlit-ace not installed. Please install it.")
                          st.text_area(
                              "Content", 
                              value=st.session_state.get("manual_editor", ""),
                              height=700,
                              key="manual_editor_text_area",
                              on_change=lambda: st.session_state.update({"manual_editor": st.session_state.manual_editor_text_area})
                          )
                  
                  with col_preview_pane:
                      st.markdown("**Live Render**")
                      with st.container(height=700, border=True):
                          # scroll_sync_marker to identify this container in JS
                          st.markdown('<div id="preview-marker"></div>', unsafe_allow_html=True)
                          
                          from ui.components import render_markdown_with_mermaid
                          # Use the latest content from state (updated by Ace above)
                          render_markdown_with_mermaid(st.session_state.get("manual_editor", ""))

                  # --- Scroll Sync Logic (injected JS) ---
                  st.components.v1.html("""
<script>
    // Debounced Scroll Sync Logic
    function setupScrollSync() {
        // 1. Find the Preview Container by looking for our marker
        const marker = window.parent.document.getElementById('preview-marker');
        if (!marker) return;

        // The scrollable container is likely an ancestor of the marker
        let previewContainer = marker.parentElement;
        while (previewContainer && getComputedStyle(previewContainer).overflowY !== 'auto' && getComputedStyle(previewContainer).overflowY !== 'scroll') {
             previewContainer = previewContainer.parentElement;
             if (!previewContainer || previewContainer === window.parent.document.body) return; // Fail safe
        }
        
        // 2. Find the Ace Editor (It's in an iframe)
        const iframes = window.parent.document.getElementsByTagName('iframe');
        let aceScroller = null;
        
        for (let iframe of iframes) {
            try {
                // Access contentDocument (Same Origin assumption)
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                const scroller = doc.querySelector('.ace_scroller');
                if (scroller) {
                    aceScroller = scroller;
                    break;
                }
            } catch (e) {
                // Ignore cross-origin errors if any
            }
        }

        if (aceScroller && previewContainer) {
            // console.log("Scroll Sync Elements Found!"); // Debug
            
            // Sync Editor -> Preview
            aceScroller.addEventListener('scroll', function() {
                const percentage = aceScroller.scrollTop / (aceScroller.scrollHeight - aceScroller.clientHeight);
                const targetScroll = percentage * (previewContainer.scrollHeight - previewContainer.clientHeight);
                previewContainer.scrollTop = targetScroll;
            });
            
            // Sync Preview -> Editor (Optional, can cause loops if not careful, sticking to Editor->Preview for now as requested)
        } else {
            // Retry if not ready
            setTimeout(setupScrollSync, 500);
        }
    }
    
    // Attempt setup
    setTimeout(setupScrollSync, 1000);
</script>
                  """, height=0, width=0)

             # Save / Export Actions - OUTSIDE the else block so it appears for Table Editor too
             st.markdown("<br>", unsafe_allow_html=True)
             c1, c2 = st.columns(2)
             with c1:
                  st.download_button(
                      "💾 Download", 
                      data=st.session_state.get("manual_editor", ""), 
                      file_name=f"{topic}.md", 
                      mime="text/markdown",
                      key="download_btn_manual"
                  )
             with c2:
                  if mode_saved == "Assignment" and assignment_df is not None:
                      # Check if we should render Assess button
                      if st.button("🚀 Push to Assess", use_container_width=True):
                          # Try retrieving from secrets first, then env vars
                          email = st.secrets.get("ASSESS_EMAIL", os.getenv("ASSESS_EMAIL"))
                          password = st.secrets.get("ASSESS_PASSWORD", os.getenv("ASSESS_PASSWORD"))
                          
                          if not email or not password:
                              st.error("⚠️ Please set ASSESS_EMAIL and ASSESS_PASSWORD in .streamlit/secrets.toml or env vars.")
                          else:
                              status_box = st.empty()
                              prog_bar = st.progress(0)
                              
                              def update_status(msg, p):
                                  status_box.info(f"🚀 {msg}")
                                  prog_bar.progress(min(max(p, 0.0), 1.0))
                              
                              try:
                                  with st.spinner("Automating Assessment Creation..."):
                                      res = publish_quiz_loop(email, password, assignment_df, status_callback=update_status)
                                      
                                  if res['success']:
                                      st.success(res['message'])
                                      st.balloons()
                                  else:
                                      st.error(res['message'])
                              except Exception as e:
                                  st.error(f"Automation Error: {str(e)}")
                              
                              time.sleep(2)
                              status_box.empty()
                              prog_bar.empty()
                          
                  else:
                      if st.button("🚀 Push to LMS", use_container_width=True):
                          # Support secrets or env for LMS as well for consistency
                          email = st.secrets.get("LMS_EMAIL", os.getenv("LMS_EMAIL"))
                          password = st.secrets.get("LMS_PASSWORD", os.getenv("LMS_PASSWORD"))
                          
                          if not email or not password:
                              st.error("⚠️ Please set LMS_EMAIL and LMS_PASSWORD in .streamlit/secrets.toml or env vars.")
                          else:
                              try:
                                  with st.spinner("Pushing content to Canvas LMS..."):
                                      res = publish_to_lms(email, password, st.session_state.manual_editor)
                                      
                                  if res['success']:
                                      st.success(res['message'])
                                      st.balloons()
                                  else:
                                      st.error(f"Failed: {res['message']}")
                              except Exception as e:
                                  st.error(f"Unexpected Error: {e}")

def render_settings():
    """
    Settings View: Model Config & System Prompts.
    """
    st.markdown("## ⚙️ Settings")
    
    st.subheader("Model Configuration")
    
    # Load current config
    current_config = st.session_state.get("model_config", {})
    
    # Helper to get index safely
    def get_index(model_name):
        try:
            return ALLOWED_MODELS.index(model_name)
        except ValueError:
            return 0

    c1, c2 = st.columns(2)
    with c1:
        creator_model = st.selectbox("Creator Model", ALLOWED_MODELS, index=get_index(current_config.get("creator")))
        auditor_model = st.selectbox("Auditor Model", ALLOWED_MODELS, index=get_index(current_config.get("auditor")))
    with c2:
        editor_model = st.selectbox("Editor Model", ALLOWED_MODELS, index=get_index(current_config.get("editor")))
        sanitizer_model = st.selectbox("Sanitizer Model", ALLOWED_MODELS, index=get_index(current_config.get("sanitizer")))
        checker_model = st.selectbox("Checker Model", ALLOWED_MODELS, index=get_index(current_config.get("checker", "claude-haiku-4-5-20251001")))
        
    iterations = st.slider("Max Refinement Loops", 1, 5, current_config.get("max_iterations", 2))
    
    # Save back to session state to be picked up by other views
    new_config = {
        "creator": creator_model,
        "auditor": auditor_model,
        "editor": editor_model,
        "sanitizer": sanitizer_model,
        "checker": checker_model,
        "max_iterations": iterations
    }
    
    st.session_state.model_config = new_config
    
    StateManager.save_to_disk()
    
    if st.button("💾 Save Configuration"):
        StateManager.save_to_disk()
        st.success("Configuration saved to disk.")
    
    st.divider()
    
    st.markdown("### 🛑 Danger Zone")
    if st.button("🗑️ Delete History & Reset", type="primary"):
        StateManager.clear_session()
        st.success("History cleared!")
        st.rerun()

    st.subheader("System Prompts")
    st.info("Agent Definitions from `agents/definitions.py`")

