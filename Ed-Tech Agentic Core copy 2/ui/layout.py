import streamlit as st
import os
import streamlit.components.v1 as components
from core.state_manager import StateManager
from core.utils import load_recent_files
from core.config import ALLOWED_MODELS

def inject_keyboard_shortcuts():
    """Injects JS for keyboard shortcuts."""
    js = """
    <script>
    document.addEventListener('keydown', function(e) {
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            const btn = document.querySelector('button[kind="primary"]');
            if (btn) {
                btn.click();
            }
        }
    });
    </script>
    """
    components.html(js, height=0, width=0)

def render_sidebar():
    inject_keyboard_shortcuts()
    with st.sidebar:
        st.header("Control Room")
        st.caption("Environment Configured")
        st.divider()
        
        # Model Selectors
        st.subheader("Model Configuration")
        with st.expander("🤖 Agent Models", expanded=False):
            creator_model = st.selectbox("Creator", ALLOWED_MODELS, index=0, help="High intelligence for drafting.")
            auditor_model = st.selectbox("Auditor", ALLOWED_MODELS, index=0, help="High reasoning for critique.")
            editor_model = st.selectbox("Editor", ALLOWED_MODELS, index=0, help="Precise instruction following.")
            sanitizer_model = st.selectbox("Sanitizer", ALLOWED_MODELS, index=min(3, len(ALLOWED_MODELS)-1), help="Fast model for formatting.")
        
        target_audience = st.selectbox(
            "Target Audience",
            ["General Student", "Beginner (EL5)", "Advanced/Expert", "Researcher", "Child (Grade 1-5)"],
            index=0
        )

        max_iterations = st.slider("Refinement Loops", min_value=1, max_value=5, value=2, help="Max critique iterations.")
        
        st.divider()
        
        # Cost Ticker
        cost = st.session_state.get("total_cost", 0.0)
        cost_placeholder = st.empty()
        cost_placeholder.metric("Session Cost", f"₹{cost:.4f}")
        
        st.divider()
        
        # Recent Files (Paginated)
        st.subheader("Recent Files")
        recent_files = load_recent_files(limit=20) # Load more, but display paginated
        
        # Simple pagination
        ITEMS_PER_PAGE = 5
        if "recent_page" not in st.session_state:
            st.session_state.recent_page = 0
            
        start_idx = st.session_state.recent_page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        
        current_batch = recent_files[start_idx:end_idx]
        
        for file in current_batch:
            if st.button(f"📄 {file['name']}", key=f"btn_{file['path']}", help=file['path'], use_container_width=True):
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
                    st.success(f"Loaded: {file['name']}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not load file: {e}")
        
        # Pagination Controls
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.session_state.recent_page > 0:
                if st.button("Previous", key="prev_page"):
                    st.session_state.recent_page -= 1
                    st.rerun()
                    
        with col_next:
            if end_idx < len(recent_files):
                if st.button("Next", key="next_page"):
                    st.session_state.recent_page += 1
                    st.rerun()

        # Knowledge Base Section
        st.divider()
        st.subheader("🧠 Knowledge Base (RAG)")
        uploaded_files = st.file_uploader(
            "Upload Context (PDF/TXT)", 
            type=["pdf", "txt"], 
            accept_multiple_files=True
        )
        
        rag_enabled = st.checkbox("Enable Retrieval", value=True, help="Use RAG context for generation")
        
        if uploaded_files:
            st.session_state["uploaded_files"] = uploaded_files
        
        model_config = {
            "creator": creator_model,
            "auditor": auditor_model,
            "editor": editor_model,
            "sanitizer": sanitizer_model,
            "max_iterations": max_iterations
        }
        
    return model_config, cost_placeholder, rag_enabled, target_audience

def load_css():
    try:
        with open("ui/styles.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Styles.css not found.")

