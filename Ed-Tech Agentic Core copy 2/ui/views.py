import streamlit as st
import os
import json
import pandas as pd
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

def render_dashboard():
    """
    The Command Center: Inputs, Stats, Recent Projects.
    """
    st.markdown("## 👋 What do you want to create today?")
    
    # 1. Hero / Inputs
    # We reuse render_input_area but wrap it in a surface if needed
    with st.container():
        st.markdown('<div class="surface-container">', unsafe_allow_html=True)
        topic, subtopics, transcript_text, mode, target_audience = render_input_area()
        st.markdown('</div>', unsafe_allow_html=True)

    # Generate Action
    col_gen, col_spacer = st.columns([1, 4])
    with col_gen:
        if st.button("✨ Generate Content", type="primary", use_container_width=True):
            if not topic:
                st.error("Please enter a topic.")
            else:
                # Set Session State for Editor
                st.session_state.topic = topic
                st.session_state.subtopics = subtopics
                st.session_state.transcript_text = transcript_text
                st.session_state.mode = mode
                st.session_state.target_audience = target_audience
                
                st.session_state.trigger_generation = True
                StateManager.navigate_to("editor")

    st.divider()
    
    # 2. Stats & Recents
    col_stats, col_recents = st.columns([1, 2])
    
    with col_stats:
        st.subheader("Your Impact")
        cost = st.session_state.get("total_cost", 0.0)
        # Assuming we can track files generated count in state or calculate it
        files_count = len(load_recent_files(limit=100))
        
        render_metric_card("Total Cost", f"₹{cost:.4f}")
        render_metric_card("Files Generated", f"{files_count}")

    with col_recents:
        st.subheader("Recent Projects")
        recent_files = load_recent_files(limit=4)
        
        # Grid Layout for Cards
        cols = st.columns(2)
        for idx, file in enumerate(recent_files):
            with cols[idx % 2]:
                with st.container():
                    st.markdown(f"""
                    <div class="glass-card">
                        <div style="font-weight:600; margin-bottom:0.5rem;">{file['name'][:25]}...</div>
                        <div style="font-size:0.8rem; color:#6B7280;">{file.get('timestamp', 'Just now')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("Open", key=f"open_{idx}", help=file['path']):
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
                            st.error(f"Error loading file: {e}")


def render_editor():
    """
    The Main Workspace: Chat, Preview, Diff.
    """
    # Check if we have anything to work on
    if not st.session_state.get("trigger_generation", False) and "generated_content" not in st.session_state:
        st.info("No active project. Go to Dashboard to start.")
        if st.button("← Back to Dashboard"):
            StateManager.navigate_to("dashboard")
        return

    # Get Configuration (from Session State or default)
    # Ideally passed in, but we resort to session state glue for now
    model_config = st.session_state.get("model_config", {})
    if not model_config:
         # Fallback if not set (should be set effectively by sidebar defaults in a real app, 
         # but here we might need to rely on what was in app.py or layout.py)
         pass 

    # --- FULL SCREEN PREVIEW TOGGLE ---
    if "fullscreen_preview" not in st.session_state:
        st.session_state.fullscreen_preview = False

    def toggle_preview():
        st.session_state.fullscreen_preview = not st.session_state.fullscreen_preview

    # --- TOP BAR ---
    if not st.session_state.fullscreen_preview:
        col_back, col_title, col_actions = st.columns([1, 4, 2])
        with col_back:
            if st.button("← Dashboard"):
                StateManager.navigate_to("dashboard")
        
        with col_title:
            topic = st.session_state.get("topic", "Untitled Project")
            st.write(f"### {topic}")
    else:
        # Minimal Header for Preview Mode
        col_back, col_actions = st.columns([1, 5])
        with col_back:
            if st.button("❌ Close Preview", on_click=toggle_preview):
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
        final_result = render_generation_status(
            orchestrator, topic, subtopics, combined_context, mode, target_audience=target_audience,
            status_placeholder=status_area,
            preview_placeholder=preview_area,
            critique_placeholder=None 
        )
        
        if final_result:
             st.balloons()
             StateManager.add_cost(final_result.get('cost', 0))
             st.session_state["generated_content"] = final_result
             st.session_state["generated_mode"] = mode
             
             # Reset manual editor state for new content
             if "manual_editor" in st.session_state:
                 del st.session_state["manual_editor"]
             if "manual_editor_widget" in st.session_state:
                 del st.session_state["manual_editor_widget"]
                 
             st.rerun()

    # 2. EDITING / VIEWING LOGIC
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
                if isinstance(content_data, str):
                    import re
                    # Try to find JSON within markdown code blocks
                    json_match = re.search(r"```json\s*(.*?)\s*```", content_data, re.DOTALL)
                    if json_match:
                        content_data = json_match.group(1)
                    elif "```" in content_data:
                         json_match = re.search(r"```\s*(.*?)\s*```", content_data, re.DOTALL)
                         if json_match: content_data = json_match.group(1)
                    
                    content_data = json.loads(content_data)
                
                if isinstance(content_data, list):
                    assignment_df = pd.DataFrame(content_data)
                elif isinstance(content_data, dict):
                     # Handle single object or wrapped structure
                     assignment_df = pd.DataFrame([content_data])
            except Exception as e:
                # Fallback to text if parsing fails
                pass

        # --- FULL SCREEN MODE ---
        if st.session_state.fullscreen_preview:
            if mode_saved == "Assignment" and assignment_df is not None:
                st.subheader("📊 Assignment Table View")
                st.dataframe(assignment_df, use_container_width=True, height=800)
            else:
                st.markdown(st.session_state.manual_editor)
            
            return # Skip the rest of the render

        # --- NORMAL SPLIT MODE ---
        col_left, col_right = st.columns([3, 7])
        
        with col_left:
            st.markdown("### 🧠 Co-Pilot")
            
            # Tabs for Chat vs Info
            tab_chat, tab_info = st.tabs(["Chat & Refine", "Source Info"])
            
            with tab_chat:
                if "chat_history" not in st.session_state: st.session_state.chat_history = []
                
                # Render History
                history_container = st.container(height=400)
                with history_container:
                    if not st.session_state.chat_history:
                        st.caption("No chat history.")
                    for msg in st.session_state.chat_history:
                        role_icon = "👤" if msg["role"] == "user" else "🤖"
                        st.markdown(f"**{role_icon}**: {msg['content']}")
                
                # Refine Input
                refine_input = st.text_input("Refine content...", placeholder="E.g. Make it more concise...")
                if st.button("Refine"):
                     if refine_input:
                        st.session_state.chat_history.append({"role": "user", "content": refine_input})
                        with st.spinner("Refining..."):
                             # FIX: Use correct OrchestratorConfig to respect user settings & save cost
                             models = st.session_state.get("model_config", {})
                             
                             from core.models import OrchestratorConfig, AgentConfig
                             from core.config import DEFAULT_MODEL
                             
                             # Respect user's choice for Editor, or fallback to something reasonable
                             editor_model = models.get("editor", DEFAULT_MODEL)
                             
                             config = OrchestratorConfig(
                                creator=AgentConfig(model=models.get("creator", DEFAULT_MODEL)),
                                auditor=AgentConfig(model=models.get("auditor", DEFAULT_MODEL)),
                                pedagogue=AgentConfig(model=models.get("pedagogue", DEFAULT_MODEL)),
                                editor=AgentConfig(model=editor_model), 
                                sanitizer=AgentConfig(model=models.get("sanitizer", "claude-3-haiku-20240307")),
                                max_iterations=models.get("max_iterations", 3),
                                human_in_the_loop=False 
                             )
                             
                             orch = Orchestrator(config=config)
                             
                             current_text = st.session_state.get("manual_editor", result['content'])
                             if isinstance(current_text, dict): current_text = str(current_text)
                             
                             new_text, cost = orch.refine_content(current_text, refine_input)
                             
                             st.session_state.chat_history.append({"role": "assistant", "content": f"Refined."})
                             StateManager.add_cost(cost)
                             
                             # Update State
                             st.session_state["manual_editor"] = new_text
                             # FIX: Force the widget to update by setting its key directly
                             st.session_state["manual_editor_widget"] = new_text
                             
                             st.session_state["previous_content"] = current_text
                             result['content'] = new_text
                             st.session_state["generated_content"] = result
                             st.rerun()

            with tab_info:
                st.info(f"Mode: {mode_saved}")
                st.caption(f"Cost: ₹{result.get('cost', 0):.4f}")
                if "topic" in st.session_state:
                    st.write(f"**Topic:** {st.session_state.topic}")

        with col_right:
             c_head, c_btn = st.columns([8, 2])
             with c_head:
                st.markdown("### 📝 Editor")
             with c_btn:
                if st.button("👁️ Preview", help="View Full Screen"):
                     toggle_preview()
                     st.rerun()
             
             # CONDITIONAL EDITOR RENDERING
             if mode_saved == "Assignment" and assignment_df is not None:
                  st.info("💡 Edit cells directly below.")
                  edited_df = st.data_editor(
                      assignment_df, 
                      use_container_width=True, 
                      num_rows="dynamic",
                      key="assignment_table_editor"
                  )
                  # TODO: Sync back to manual_editor (JSON) if needed, 
                  # but for now we keep it visual or would need complex reverse-parsing.
             else:
                  # FIX: Avoid "value" + "key" conflict warning.
                  # Initialize widget state if not present (e.g. on first load or after generation)
                  if "manual_editor_widget" not in st.session_state:
                       st.session_state.manual_editor_widget = st.session_state.manual_editor

                  st.text_area(
                      "Content",
                      # value=st.session_state.manual_editor, # REMOVED to avoid conflict
                      height=600,
                      key="manual_editor_widget",
                      label_visibility="collapsed",
                      on_change=lambda: st.session_state.update({"manual_editor": st.session_state.manual_editor_widget})
                  )
             
             # Save / Export Actions
             c1, c2 = st.columns(2)
             with c1:
                 if mode_saved == "Assignment" and assignment_df is not None:
                     # Convert DF to CSV
                     csv_data = assignment_df.to_csv(index=False).encode('utf-8')
                     st.download_button(
                         "💾 Download CSV", 
                         data=csv_data, 
                         file_name=f"assignment.csv", 
                         mime="text/csv"
                     )
                 else:
                     st.download_button(
                         "💾 Download Markdown", 
                         data=st.session_state.manual_editor, 
                         file_name="content.md", 
                         mime="text/markdown"
                     )
             with c2:
                 if st.button("🚀 Push to LMS"):
                     st.info("LMS Push functionality placeholder")

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
        
    iterations = st.slider("Max Refinement Loops", 1, 5, current_config.get("max_iterations", 2))
    
    # Save back to session state to be picked up by other views
    new_config = {
        "creator": creator_model,
        "auditor": auditor_model,
        "editor": editor_model,
        "sanitizer": sanitizer_model,
        "max_iterations": iterations
    }
    
    st.session_state.model_config = new_config
    
    # Explicit Persist Action or Implicit?
    # Since we update session state immediately, navigate_to will catch it.
    # But let's force a save just in case the user refreshes ON this page.
    StateManager.save_to_disk()
    
    if st.button("💾 Save Configuration"):
        StateManager.save_to_disk()
        st.success("Configuration saved to disk.")
    
    st.divider()
    st.subheader("System Prompts")
    st.info("Agent Definitions from `agents/definitions.py`")
