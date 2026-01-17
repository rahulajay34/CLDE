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
    render_generation_status, render_skeleton_loader
)

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

# --- SIDEBAR ---
creator_model, cost_placeholder = render_sidebar()

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
                
            # Run Loop
            final_result = render_generation_status(orchestrator, topic, subtopics, transcript_text, mode)
            
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
            with col_edit:
                edited_content = st.text_area("Markdown Source", value=result['content'], height=600, label_visibility="collapsed")
            with col_prev:
                st.markdown(edited_content)
            
            st.download_button("📥 Download Markdown", edited_content, file_name="lecture_notes.md", mime="text/markdown")

        st.caption(f"Saved at: `{result['path']}`")

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