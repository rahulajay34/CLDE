import streamlit as st
import os
import asyncio
import json
import pandas as pd
from core.state_manager import StateManager
from core.orchestrator import Orchestrator
from core.config import PAGE_TITLE, PAGE_ICON, LAYOUT
from core.logger import logger
from ui.layout import render_sidebar, load_css
from ui.components import (
    render_header, render_input_area, 
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
creator_model, cost_placeholder, rag_enabled, target_audience = render_sidebar()

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
# --- MAIN LAYOUT ---
render_header()

# Tabs
tab1, tab2 = st.tabs(["Workspace", "Advanced Config"])

with tab1:
    # --- TOP: INPUTS ---
    with st.expander("📝 specific Context & Input", expanded=not ("generated_content" in st.session_state)):
        topic, subtopics, transcript_text, mode = render_input_area()
        
        # Generator Controls
        col_gen, col_reset = st.columns([4, 1])
        with col_gen:
            if "trigger_generation" not in st.session_state:
                st.session_state.trigger_generation = False
                
            if st.button("✨ Generate Content", type="primary", use_container_width=True):
                if not topic:
                    st.error("Please enter a topic first.")
                elif "generated_content" in st.session_state:
                    st.session_state.show_confirm = True
                else:
                    st.session_state.trigger_generation = True

        with col_reset:
            if st.button("🔄 Reset", help="Clear current session"):
                for key in ["generated_content", "generated_mode", "show_confirm", "manual_editor", "previous_content"]:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()

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


    # --- CO-PILOT IN SIDEBAR ---
    with st.sidebar:
        st.divider()
        copilot_area = st.container()

    # --- GENERATION LOGIC ---
    if st.session_state.trigger_generation:
        st.session_state.trigger_generation = False
        
        if not os.getenv("ANTHROPIC_API_KEY"):
            st.error("ANTHROPIC_API_KEY not found.")
        else:
            with copilot_area:
                 # Initialize Orchestrator
                orchestrator = Orchestrator(base_model=creator_model)
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
                final_result = render_generation_status(
                    orchestrator, topic, subtopics, combined_context, mode, target_audience,
                    preview_placeholder=doc_preview_area,
                    critique_placeholder=copilot_area
                )
                
                if final_result:
                    st.balloons()
                    StateManager.add_cost(final_result['cost'])
                    st.session_state["generated_content"] = final_result
                    st.session_state["generated_mode"] = mode
                    st.rerun()

    # --- POST-GENERATION VIEW ---
    if "generated_content" in st.session_state:
        result = st.session_state["generated_content"]
        mode_saved = st.session_state.get("generated_mode", "Lecture Notes")
        
        # --- EDITOR AREA (Main Content) ---
        with doc_preview_area.container():
            st.subheader(f"📄 {mode_saved} Editor")
            
            if mode_saved == "Assignment":
                # Data Editor for Assignments
                try:
                    content_data = result['content']
                    if isinstance(content_data, str): content_data = json.loads(content_data)
                    
                    if isinstance(content_data, list):
                        df = pd.DataFrame(content_data)
                        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="assignment_editor")
                        
                        # Store updates (implicit via session state key, but good to track)
                        # Assignment downloads need to be handled here or in right col
                    else:
                        st.json(content_data)
                except Exception as e:
                     st.error(f"Assignment Parse Error: {e}")
            else:
                # Markdown Editor with Split View
                if "manual_editor" not in st.session_state:
                    st.session_state.manual_editor = result['content']
                
                # Create columns within the editor area
                col_edit, col_prev = st.columns(2)
                
                with col_edit:
                    st.caption("✏️ Editor")
                    edited_content = st.text_area(
                        "Content",
                        value=st.session_state.manual_editor,
                        height=700,
                        label_visibility="collapsed",
                        key="manual_editor_widget",
                        on_change=lambda: st.session_state.update({"manual_editor": st.session_state.manual_editor_widget})
                    )
                
                with col_prev:
                    st.caption("👁️ Live Preview")
                    # Use a container with border and scroll for the preview
                    with st.container(height=700, border=True):
                        st.markdown(st.session_state.manual_editor)

        # --- CO-PILOT (Sidebar) ---
        with copilot_area:
            st.subheader("🤖 Co-Pilot")
            
            # 1. Stats
            st.caption(f"Total Cost: ₹{result.get('cost', 0):.4f}")
            
            # 2. Downloads & Actions
            with st.expander("💾 Export & Publish", expanded=True):
                if mode_saved == "Assignment" and 'edited_df' in locals():
                    json_str = edited_df.to_json(orient="records", indent=2)
                    st.download_button("📥 JSON", json_str, "assignment.json", "application/json")
                    # Excel logic could go here
                elif mode_saved != "Assignment":
                    st.download_button("📥 Markdown", st.session_state.manual_editor, "notes.md", "text/markdown")
                
                if publish_to_lms:
                     if st.button("🚀 Push to LMS"):
                        with st.spinner("Pushing..."):
                             res = publish_to_lms(os.getenv("LMS_EMAIL"), os.getenv("LMS_PASSWORD"), st.session_state.manual_editor)
                             if res["success"]: st.success("Published!")
                             else: st.error(res["message"])

            # 3. Chat to Refine
            st.divider()
            st.markdown("#### 💬 Chat to Refine")
            
            # --- PERSISTENT CHAT HISTORY ---
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            
            # Render History
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            user_instruction = st.chat_input("Ex: 'Make it funnier'")
            if user_instruction:
                 # Add User Msg
                 st.session_state.chat_history.append({"role": "user", "content": user_instruction})
                 with st.chat_message("user"):
                     st.markdown(user_instruction)

                 with st.spinner("Refining..."):
                    orch = Orchestrator(base_model=creator_model)
                    # Use current editor state
                    current_text = st.session_state.manual_editor if mode_saved != "Assignment" else str(result['content'])
                    
                    new_text, cost = orch.refine_content(current_text, user_instruction)
                    
                    # Add AI Msg
                    ai_msg = f"Applied refinements. (Cost: ₹{cost:.4f})"
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_msg})
                    with st.chat_message("assistant"):
                        st.markdown(ai_msg)

                    # Store history for diff
                    st.session_state["previous_content"] = current_text
                    
                    # Update State
                    st.session_state["manual_editor"] = new_text
                    if "manual_editor_widget" in st.session_state: del st.session_state["manual_editor_widget"]
                    
                    result['content'] = new_text
                    result['cost'] += cost
                    StateManager.add_cost(cost)
                    st.session_state["generated_content"] = result
                    st.rerun()

            # 4. Diff View (if active)
            if "previous_content" in st.session_state and mode_saved != "Assignment":
                with st.expander("🔄 View Changes", expanded=True):
                    render_diff_view(st.session_state["previous_content"], st.session_state.manual_editor)


with tab2:
    st.subheader("System Configuration")
    try:
        from agents.definitions import CreatorAgent, AuditorAgent
        st.info("System Prompts loaded from `agents/definitions.py`")
        with st.expander("View Prompts"):
             st.text(CreatorAgent(model=DEFAULT_MODEL).get_system_prompt())
    except:
        st.warning("Could not load agent definitions.")