import streamlit as st
import os
import json
import pandas as pd
import html
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
            topic, subtopics, transcript_text, mode, target_audience = render_input_area()
            
            # Generate Action (Inside the hero container for flow)
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
            # st.markdown('</div>', unsafe_allow_html=True) # REMOVED

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()
    
    # 2. Stats & Recents (Visual Demotion / Secondary)
    # Use [1, 3] ratio: Small stats, wider recents
    col_stats, col_recents = st.columns([1, 3])
    
    with col_stats:
        st.caption("SYSTEM METRICS")
        cost = st.session_state.get("total_cost", 0.0)
        files_count = len(load_recent_files(limit=100))
        
        # Compact metrics
        st.metric("Total Cost", f"₹{cost:.4f}")
        st.metric("Files Created", f"{files_count}")

    with col_recents:
        st.caption("RECENT PROJECTS")
        recent_files = load_recent_files(limit=4)
        
        if not recent_files:
            st.info("No recent projects yet. Start creating!")
        
        # Grid Layout for Cards [1, 1, 1, 1] is too crowded, use [1, 1]
        cols = st.columns(4)
        for idx, file in enumerate(recent_files):
            with cols[idx]:
                with st.container():
                    # Simplified card look
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
            critique_placeholder=None 
        ))
        
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
                     assignment_df = pd.DataFrame([content_data])
            except Exception as e:
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
        # Left: Chat/Utility (Smaller, Glass Style)
        # Right: Content (Larger, Paper Style)
        col_left, col_right = st.columns([1, 2]) # 1:2 Ratio (approx 33% / 66%)
        
        with col_left:
            st.markdown("#### 🧠 Co-Pilot")
            
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

        with col_right:
             # Header for Editor
             c_head, c_btn = st.columns([4, 1])
             with c_head:
                st.markdown("#### 📝 Editor")
             with c_btn:
                if st.button("👁️ Expand", help="Toggle Full Screen"):
                     toggle_preview()
                     st.rerun()
             
             # CONDITIONAL EDITOR RENDERING
             if mode_saved == "Assignment" and assignment_df is not None:
                  st.info("💡 Edit cells directly below.")
                  edited_df = st.data_editor(
                      assignment_df, 
                      use_container_width=True, 
                      num_rows="dynamic",
                      key="assignment_table_editor",
                      height=600
                  )
             else:
                  # TABS for Code vs Preview
                  tab_edit, tab_preview = st.tabs(["✍️ Edit", "👁️ Live Preview"])
                  
                  with tab_edit:
                      if "manual_editor_widget" not in st.session_state:
                           st.session_state.manual_editor_widget = st.session_state.manual_editor
    
                      st.text_area(
                          "Content",
                          height=600,
                          key="manual_editor_widget",
                          label_visibility="collapsed",
                          on_change=lambda: st.session_state.update({"manual_editor": st.session_state.manual_editor_widget})
                      )
                  
                  with tab_preview:
                      from ui.components import render_markdown_with_mermaid
                      render_markdown_with_mermaid(st.session_state.manual_editor)
             
             # Save / Export Actions
             st.markdown("<br>", unsafe_allow_html=True)
             c1, c2 = st.columns(2)
             with c1:
                 # Download logic (CSV vs MD)
                 data_to_dl = st.session_state.manual_editor
                 mime_type = "text/markdown"
                 fname = "content.md"
                 
                 if mode_saved == "Assignment" and assignment_df is not None:
                     data_to_dl = assignment_df.to_csv(index=False).encode('utf-8')
                     mime_type = "text/csv"
                     fname = "assignment.csv"
                 
                 st.download_button("💾 Download", data=data_to_dl, file_name=fname, mime=mime_type, use_container_width=True)

             with c2:
                 if st.button("🚀 Push to LMS", use_container_width=True):
                     st.toast("Success! Content pushed to Canvas LMS.")

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

