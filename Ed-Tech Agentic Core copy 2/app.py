import streamlit as st
import os
import asyncio
import json
import pandas as pd
from core.state_manager import StateManager
from core.models import OrchestratorConfig, AgentConfig
from core.orchestrator import Orchestrator
from core.config import PAGE_TITLE, PAGE_ICON, LAYOUT
from core.logger import logger
from ui.layout import render_sidebar, load_css
from ui.components import (
    render_header, render_input_area, 
    render_generation_status, render_skeleton_loader
)
from ui.diff_viewer import render_diff_view

# --- APP SETUP ---
st.set_page_config(page_title=PAGE_TITLE, layout=LAYOUT, page_icon=PAGE_ICON)


# Optional LMS Import
try:
    from lms_automation import publish_to_lms
except ImportError:
    publish_to_lms = None

# --- APP SETUP ---
StateManager.initialize_state()
load_css()
logger.info("Application Started")

# optional: Initialize RAG
try:
    from core.rag import RAGManager
    if "rag_manager" not in st.session_state:
        st.session_state.rag_manager = RAGManager()
except Exception as e:
    logger.error(f"RAG Init Error: {e}")
    st.session_state.rag_manager = None

# --- SIDEBAR ---
model_config, cost_placeholder, rag_enabled = render_sidebar()

# Handle Uploads immediately
if "uploaded_files" in st.session_state and st.session_state.rag_manager:
    for uploaded_file in st.session_state["uploaded_files"]:
        # Save temp to ingest
        temp_path = os.path.join("storage", uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Check if already ingested (naive check, or just ingest)
        # For now, just ingest
        st.session_state.rag_manager.ingest_document(temp_path, uploaded_file.name)
        st.toast(f"Ingested {uploaded_file.name} into Knowledge Base")
    
    del st.session_state["uploaded_files"] # Clear queue

# --- MAIN LAYOUT ---
# --- SIDEBAR EXTRA ---
with st.sidebar:
    st.divider()
    if st.button("🗑️ Clear Session", help="Reset all data", type="secondary"):
        for key in ["generated_content", "generated_mode", "show_confirm", "manual_editor", "previous_content", "chat_history"]:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

# --- MAIN LAYOUT ---
render_header()

# Tabs
tab1, tab2, tab3 = st.tabs(["Workspace", "Advanced Config", "Audit Trail"])

with tab1:
    # --- TOP: INPUTS (HERO SECTION) ---
    # Using a container to create a distinct "Surface"
    # Auto-collapse input if content exists to focus on Editor
    has_content = "generated_content" in st.session_state
    
    with st.expander("📝 Context & Input", expanded=not has_content):
        # topic, subtopics, transcript_text, mode, target_audience = render_input_area()
        # Need to capture target_audience now
        topic, subtopics, transcript_text, mode, target_audience = render_input_area()
        
        # Generator Controls
        col_gen, col_reset = st.columns([4, 1])
        with col_gen:
            if "trigger_generation" not in st.session_state:
                st.session_state.trigger_generation = False
                
            # Generator Controls
        # Only Generate button here now
        if "trigger_generation" not in st.session_state:
            st.session_state.trigger_generation = False
            
        if st.button("✨ Generate Content", type="primary", use_container_width=True):
            if not topic:
                st.error("Please enter a topic first.")
            elif "generated_content" in st.session_state:
                st.session_state.show_confirm = True
            else:
                st.session_state.trigger_generation = True

        # Confirmation Dialog
        if st.session_state.get("show_confirm"):
            st.warning("⚠️ You have active content. Overwrite?")
            if st.button("Yes, Overwrite"):
                st.session_state.trigger_generation = True
                st.session_state.show_confirm = False
                st.rerun()

    st.divider()
    
    # --- SPLIT VIEW LAYOUT ---
    # Editor uses full width now
    doc_preview_area = st.empty()


    # --- GENERATION PLACEHOLDERS ---
    # We need these for the real-time feedback during generation
    copilot_area = st.empty() # Was sidebar, now main area feedback
    
    # --- GENERATION LOGIC ---
    if st.session_state.trigger_generation:
        st.session_state.trigger_generation = False
        
        if not os.getenv("ANTHROPIC_API_KEY"):
            st.error("ANTHROPIC_API_KEY not found.")
        else:
             # Initialize Orchestrator with Config
            config = OrchestratorConfig(
                creator=AgentConfig(model=model_config["creator"]),
                auditor=AgentConfig(model=model_config["auditor"]),
                pedagogue=AgentConfig(model=model_config["auditor"]), 
                editor=AgentConfig(model=model_config["editor"]),
                sanitizer=AgentConfig(model=model_config["sanitizer"]),
                max_iterations=model_config.get("max_iterations", 3),
                human_in_the_loop=False 
            )
            
            orchestrator = Orchestrator(config=config)
            logger.info(f"Starting generation: {topic}")
            
            # Retrieve Context (RAG)
            rag_context = ""
            if rag_enabled and st.session_state.rag_manager:
                with st.spinner("Searching Knowledge Base..."):
                    query = f"{topic} {subtopics}"
                    rag_context = st.session_state.rag_manager.retrieve_context(query)
                    if rag_context: st.info(f"📚 RAG Active ({len(rag_context)} chars)")

            combined_context = transcript_text or ""
            if rag_context:
                combined_context += f"\n\n[KNOWLEDGE BASE CONTEXT]:\n{rag_context}"
            
            # Render Loop (Blocking)
            # using copilot_area for critiques/status if needed, or just let st.status handle it
            final_result = render_generation_status(
                orchestrator, topic, subtopics, combined_context, mode, target_audience=target_audience,
                preview_placeholder=doc_preview_area,
                critique_placeholder=copilot_area
            )
            
            if final_result:
                st.balloons()
                StateManager.add_cost(final_result.get('cost', 0))
                st.session_state["generated_content"] = final_result
                st.session_state["generated_mode"] = mode
                st.rerun()

    # --- POST-GENERATION VIEW (WORKSPACE) ---
    if "generated_content" in st.session_state:
        result = st.session_state["generated_content"]
        mode_saved = st.session_state.get("generated_mode", "Lecture Notes")
        
        st.divider()
        
        # --- ACTION BAR (Sticky-ish Header) ---
        # We place this above the columns
        col_actions = st.columns([0.6, 0.1, 0.1, 0.1, 0.1])
        with col_actions[0]:
            st.caption(f"Editing: **{mode_saved}** | Cost: ₹{result.get('cost', 0):.4f}")
        
        with col_actions[1]:
            if st.button("💾", help="Download Markdown/JSON"):
                pass # Trigger download (handled below or via callback ideally, but for now just a signal)
        with col_actions[2]:
            if publish_to_lms and st.button("🚀", help="Push to LMS"):
                with st.spinner("Pushing..."):
                     res = publish_to_lms(os.getenv("LMS_EMAIL"), os.getenv("LMS_PASSWORD"), st.session_state.manual_editor)
                     if res["success"]: st.toast("Published to LMS!", icon="🚀")
                     else: st.error(res["message"])
        with col_actions[3]:
             if st.button("🔄", help="Reset Workspace"):
                for key in ["generated_content", "generated_mode", "show_confirm", "manual_editor", "previous_content", "chat_history"]:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()
        
        # --- WORKSPACE LAYOUT ---
        # 2-Column Workspace "IDE Feel"
        # Notes Mode: 1.2 vs 1.0
        # Assignment Mode: Full Width
        
        if mode_saved == "Assignment":
             st.subheader("Assignment Data")
             try:
                content_data = result['content']
                if isinstance(content_data, str): 
                     # Robust JSON Extraction
                     import re
                     # 1. Try to find JSON within markdown code blocks
                     json_match = re.search(r"```json\s*(.*?)\s*```", content_data, re.DOTALL)
                     if json_match:
                         content_data = json_match.group(1)
                     elif "```" in content_data:
                         # Fallback for generic blocks
                         json_match = re.search(r"```\s*(.*?)\s*```", content_data, re.DOTALL)
                         if json_match:
                             content_data = json_match.group(1)
                     
                     # 2. Parse
                     content_data = json.loads(content_data)
                
                if isinstance(content_data, list):
                    df = pd.DataFrame(content_data)
                    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="assignment_editor")
                else:
                    st.json(content_data)
             except Exception as e:
                 st.error(f"Assignment Parse Error: {e}")
                 st.warning("Raw Content:")
                 st.code(result.get('content', ''))
                 
        else:
            # TEXT EDITOR MODE
            col_edit, col_view = st.columns([1.2, 1])
            
            with col_edit:
                st.caption("📝 Editor")
                if "manual_editor" not in st.session_state:
                    st.session_state.manual_editor = result['content']
                
                # Editor
                st.text_area(
                    "Content",
                    value=st.session_state.manual_editor,
                    height=None, # Dynamic height or set via st.chat_input placement
                    label_visibility="collapsed",
                    key="manual_editor_widget",
                    on_change=lambda: st.session_state.update({"manual_editor": st.session_state.manual_editor_widget})
                )

                # --- EMBEDDED CHAT / REFINEMENT (Below Editor) ---
                st.divider()
                st.caption("✨ Co-Pilot Chat")
                
                if "chat_history" not in st.session_state:
                    st.session_state.chat_history = []
                
                # Show history in a scrollable container or expander
                if st.session_state.chat_history:
                    with st.expander(f"History ({len(st.session_state.chat_history)})", expanded=False):
                        for msg in st.session_state.chat_history:
                            role_icon = "👤" if msg["role"] == "user" else "🤖"
                            st.markdown(f"**{role_icon}**: {msg['content']}")

                # Chat Input - localized to this column
                refined_promt = st.text_input("Refine this content...", placeholder="Make it shorter, Add a quiz...", key="refine_input")
                if st.button("Refine", help="Apply changes"):
                    if refined_promt:
                        st.session_state.chat_history.append({"role": "user", "content": refined_promt})
                        with st.spinner("Refining..."):
                             # Re-init orchestrator for refinement
                            orch = Orchestrator(config=model_config["creator"]) 
                            current_text = st.session_state.manual_editor if mode_saved != "Assignment" else str(result['content'])
                            new_text, cost = orch.refine_content(current_text, refined_promt)
                            
                            st.session_state.chat_history.append({"role": "assistant", "content": f"Refined: {refined_promt}"})
                            st.session_state["previous_content"] = current_text
                            st.session_state["manual_editor"] = new_text
                            if "manual_editor_widget" in st.session_state: del st.session_state["manual_editor_widget"]
                            
                            result['content'] = new_text
                            result['cost'] += cost
                            StateManager.add_cost(cost)
                            st.session_state["generated_content"] = result
                            
                            # Update audit log for refinement
                            if "audit_log" not in st.session_state: st.session_state.audit_log = []
                            st.session_state.audit_log.append({
                                "type": "step", 
                                "agent": "Creator", 
                                "status": "Refined content with user feedback",
                                "content": refined_promt # Using refined_promt as content for now, as ai_msg is not defined here
                            })
                            
                            st.toast("Refinement Applied! Check the Editor.", icon="✅")
                            st.rerun()

            with col_view:
                st.caption("👁️ Live Preview")
                with st.container(height=700, border=True):
                    st.markdown(st.session_state.manual_editor)
                
                # Render Diff if exists
                if "previous_content" in st.session_state:
                     with st.expander("🔄 see changes"):
                          render_diff_view(st.session_state["previous_content"], st.session_state.manual_editor)
    
    # --- EMPTY STATE / ONBOARDING ---
    elif not st.session_state.get("trigger_generation", False):
        st.markdown(
            """
            <div style="text-align: center; padding: 4rem 2rem; color: #6B7280;">
                <h2 style="color: #4B5563; margin-bottom: 1rem;">👋 Welcome to Agentic Courseware</h2>
                <p style="font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
                    I have 4 autonomous agents ready to write your course content. 
                    <br>Select a <b>Topic</b> above to start the orchestration.
                </p>
                <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 3rem;">
                    <div style="text-align: center;">
                        <span style="font-size: 2rem; background: #EEF2FF; padding: 1rem; border-radius: 50%;">✍️</span>
                        <p style="margin-top: 1rem; font-weight: 500;">Drafting</p>
                    </div>
                    <div style="text-align: center;">
                        <span style="font-size: 2rem; background: #FEF3C7; padding: 1rem; border-radius: 50%;">🔍</span>
                        <p style="margin-top: 1rem; font-weight: 500;">Critiquing</p>
                    </div>
                     <div style="text-align: center;">
                        <span style="font-size: 2rem; background: #D1FAE5; padding: 1rem; border-radius: 50%;">🎓</span>
                        <p style="margin-top: 1rem; font-weight: 500;">Refining</p>
                    </div>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )


with tab2:
    st.subheader("System Configuration")
    try:
        from agents.definitions import CreatorAgent, AuditorAgent
        st.info("System Prompts loaded from `agents/definitions.py`")
        with st.expander("View Prompts"):
             st.text(CreatorAgent(model=DEFAULT_MODEL).get_system_prompt())
    except:
        st.warning("Could not load agent definitions.")

with tab3:
    st.header("📋 Agent Audit Trail")
    if "audit_log" in st.session_state and st.session_state.audit_log:
        for event in st.session_state.audit_log:
            agent = event.get("agent", "System")
            status = event.get("status", "")
            content = event.get("content", "")
            
            with st.expander(f"{agent}: {status}", expanded=False):
                if content:
                    st.code(content, language="markdown")
                else:
                    st.caption("No content payload.")
    else:
        st.info("No audit logs available yet. Generate some content to see the agents in action.")