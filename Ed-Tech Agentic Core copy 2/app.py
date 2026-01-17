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

# Optional LMS Import
try:
    from lms_automation import publish_to_lms
except ImportError:
    publish_to_lms = None

# --- APP SETUP ---
StateManager.initialize_state()
st.set_page_config(page_title=PAGE_TITLE, layout=LAYOUT, page_icon=PAGE_ICON)
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
render_header()

# Tabs
tab1, tab2 = st.tabs(["Workspace", "Advanced Config"])

with tab1:
    # Input Area
    topic, subtopics, transcript_text, mode = render_input_area()
    
    # Generate Button Logic with Confirmation
    if "trigger_generation" not in st.session_state:
        st.session_state.trigger_generation = False
        
    col_gen, col_reset = st.columns([3, 1])
    with col_gen:
        if st.button("✨ Generate Content", type="primary", use_container_width=True):
            if not topic:
                st.error("Please enter a topic first.")
            elif "generated_content" in st.session_state:
                st.session_state.show_confirm = True
            else:
                st.session_state.trigger_generation = True
    
    with col_reset:
        if st.button("🔄 Reset", help="Clear current session"):
            for key in ["generated_content", "generated_mode", "show_confirm"]:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

    # Confirmation Dialog
    if st.session_state.get("show_confirm"):
        st.warning("⚠️ You have active content in this session. Generating new content will overwrite it.")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("Yes, Overwrite"):
                st.session_state.trigger_generation = True
                st.session_state.show_confirm = False
                st.rerun()
        with col_c2:
            if st.button("Cancel"):
                st.session_state.show_confirm = False
                st.rerun()

    # --- GENERATION LOGIC ---
    if st.session_state.trigger_generation:
        st.session_state.trigger_generation = False # Reset immediately
        
        if not os.getenv("ANTHROPIC_API_KEY"):
            st.error("ANTHROPIC_API_KEY not found. Please set it in your local .env file.")
        else:
            # Show skeleton while initializing
            loader_placeholder = st.empty()
            with loader_placeholder:
                render_skeleton_loader()
                # Initialize Orchestrator
                orchestrator = Orchestrator(base_model=creator_model)
                logger.info(f"Starting generation for topic: {topic}, mode: {mode}")
            
            # Clear skeleton before showing status
            loader_placeholder.empty()
                
            # Retrieve Context if RAG Enabled
            rag_context = ""
            if rag_enabled and st.session_state.rag_manager:
                query = f"{topic} {subtopics}"
                rag_context = st.session_state.rag_manager.retrieve_context(query)
                if rag_context:
                    logger.info("RAG Context Retrieved successfully.")
                    st.info(f"📚 Retrieved {len(rag_context)} chars of context.")

            # Run Loop
            # We append RAG context to transcript if it exists, or treat it as transcript
            # Or pass it explicitly. For now, appending to transcript variable seems easiest 
            # as transcript is treated as "Reference Material" in creating/auditing.
            
            combined_context = transcript_text or ""
            if rag_context:
                combined_context += f"\n\n[KNOWLEDGE BASE CONTEXT]:\n{rag_context}"

            final_result = render_generation_status(orchestrator, topic, subtopics, combined_context, mode, target_audience)
            
            if final_result:
                st.balloons()
                st.success(f"Success! Total Cost: ₹{final_result['cost']:.4f}")
                StateManager.add_cost(final_result['cost'])
                
                # Persist State
                st.session_state["generated_content"] = final_result
                st.session_state["generated_mode"] = mode
                st.rerun() # Rerun to show editor immediately

    # --- RESULTS DISPLAY ---
    if "generated_content" in st.session_state:
        result = st.session_state["generated_content"]
        mode_saved = st.session_state.get("generated_mode", "Lecture Notes")
        
        st.divider()
        st.subheader("📝 Content Editor & Preview")
        
        # --- EDITOR LOGIC ---
        # (Preserving existing editor logic but keeping it cleaner)
        if mode_saved == "Assignment":
            try:
                content_data = result['content']
                if isinstance(content_data, str):
                    content_data = json.loads(content_data)
                
                if isinstance(content_data, list):
                    df = pd.DataFrame(content_data)
                    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="assignment_editor")
                    
                    # Exports
                    json_str = edited_df.to_json(orient="records", indent=2)
                    
                    import io
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        edited_df.to_excel(writer, index=False)
                    excel_data = excel_buffer.getvalue()
                    
                    col_actions = st.columns([1, 1, 2])
                    with col_actions[0]:
                        st.download_button("📥 Download JSON", json_str, file_name="assignment.json", mime="application/json")
                    with col_actions[1]:
                        st.download_button("📥 Download Excel", excel_data, file_name="assignment.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.warning("Raw JSON Data")
                    st.code(json.dumps(content_data, indent=2))
            except Exception as e:
                st.error(f"Error rendering assignment editor: {e}")
        
        else:
            # Markdown Editor
            col_edit, col_prev = st.columns(2)
            
            # Sync session state for manual edits
            if "manual_editor" not in st.session_state:
                st.session_state.manual_editor = result['content']
            
            with col_edit:
                # We use key="manual_editor" to persist user changes
                # distinct from result['content'] until saved/refused
                edited_content = st.text_area(
                    "Markdown Source", 
                    value=st.session_state.manual_editor,
                    height=600, 
                    label_visibility="collapsed",
                    key="manual_editor_widget",
                    on_change=lambda: st.session_state.update({"manual_editor": st.session_state.manual_editor_widget})
                )
            with col_prev:
                st.markdown(edited_content)
            
            st.download_button("📥 Download Markdown", edited_content, file_name="lecture_notes.md", mime="text/markdown")

            # --- Chat to Refine ---
            st.divider()
            st.subheader("💬 Chat to Refine")
            
            # Show Diff if previous version exists
            if "previous_content" in st.session_state:
                with st.expander("🔄 Compare with Previous Version", expanded=False):
                    render_diff_view(st.session_state["previous_content"], edited_content)
            
            user_instruction = st.chat_input("Ask for changes (e.g., 'Make the tone more enthusiastic', 'Fix the typo in section 2')")
            
            if user_instruction:
                with st.spinner("Refining based on instruction..."):
                    # Initialize Orchestrator (lazy)
                    # Use last used model or creator model
                    orch = Orchestrator(base_model=creator_model)
                    
                    new_text, cost = orch.refine_content(edited_content, user_instruction)
                    
                    # Update State
                    st.session_state["previous_content"] = edited_content
                    
                    # Update manual editor backing state
                    st.session_state["manual_editor"] = new_text 
                    
                    # Force widget update by clearing its session state provided key
                    # This prompts Streamlit to re-read 'value' on the next run
                    if "manual_editor_widget" in st.session_state:
                         del st.session_state["manual_editor_widget"]
                    
                    # Also update main result
                    result['content'] = new_text
                    result['cost'] += cost
                    StateManager.add_cost(cost)
                    
                    st.session_state["generated_content"] = result
                    st.rerun()

        # LMS Section
        st.divider()
        if publish_to_lms:
            st.subheader("🚀 Publish to LMS")
            lms_email = st.secrets.get("LMS_EMAIL", os.getenv("LMS_EMAIL", ""))
            lms_password = st.secrets.get("LMS_PASSWORD", os.getenv("LMS_PASSWORD", ""))
            
            if st.button("🚀 Push to Masai LMS"):
                if not lms_email or not lms_password:
                    st.error("Missing LMS Credentials")
                else:
                    with st.spinner("Automating LMS..."):
                        # Use edited content if available, else original
                        content_to_push = result['content']
                        # Note: st.text_area doesn't update st.session_state.result automatically unless key matches
                        # Ideally we'd capture the return of text_area but complex state mgmt needed.
                        # For now, using the original or whatever logic was there. 
                        # To improve: we should use `edited_content` variable if we are in Lecture Notes mode.
                        if mode_saved != "Assignment" and 'edited_content' in locals():
                             content_to_push = edited_content
                             
                        res = publish_to_lms(lms_email, lms_password, content_to_push)
                        if res["success"]: st.success(res["message"])
                        else: st.error(res["message"])

with tab2:
    st.subheader("System Configuration")
    st.info("Edit `agents/definitions.py` to modify system prompts.")
    try:
        from agents.definitions import CreatorAgent, AuditorAgent
        with st.expander("Creator Agent Prompt"):
            st.code(CreatorAgent(model=DEFAULT_MODEL).get_system_prompt())
        with st.expander("Auditor Agent Prompt"):
            st.code(AuditorAgent(model=DEFAULT_MODEL).get_system_prompt())
    except Exception as e:
        st.error(f"Could not load prompts: {e}")