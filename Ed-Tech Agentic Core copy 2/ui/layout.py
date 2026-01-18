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
    """
    Renders the persistent Sidebar for Navigation and Global Context.
    """
    inject_keyboard_shortcuts()
    with st.sidebar:
        st.header(f"Agentic Core")
        st.divider()
        
        # --- NAVIGATION ---
        st.caption("NAVIGATION")
        
        # We use full width buttons to act as tabs
        if st.button("📊 Dashboard", use_container_width=True, type="secondary" if st.session_state.get("view") != "dashboard" else "primary"):
            StateManager.navigate_to("dashboard")
            
        if st.button("📝 Editor", use_container_width=True, type="secondary" if st.session_state.get("view") != "editor" else "primary"):
            StateManager.navigate_to("editor")
            
        if st.button("⚙️ Settings", use_container_width=True, type="secondary" if st.session_state.get("view") != "settings" else "primary"):
            StateManager.navigate_to("settings")
            
        st.divider()
        
        # --- GLOBAL CONTEXT ---
        st.caption("GLOBAL CONTEXT")
        
        # Cost Ticker
        cost = st.session_state.get("total_cost", 0.0)
        st.metric("Session Cost", f"₹{cost:.4f}")
        
        st.divider()
        
        # RAG / Knowledge Base
        st.subheader("🧠 Knowledge Base")
        uploaded_files = st.file_uploader(
            "Add Context", 
            type=["pdf", "txt"], 
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        
        rag_enabled = st.checkbox("RAG Enabled", value=True)
        
        if uploaded_files:
            st.session_state["uploaded_files"] = uploaded_files
            
        st.divider()
        
        # Clear Session
        if st.button("🗑️ Clear Session", help="Reset all data"):
            for key in ["generated_content", "generated_mode", "view", "trigger_generation", "chat_history"]:
                if key in st.session_state: del st.session_state[key]
            StateManager.initialize_state()
            st.rerun()

    return rag_enabled

def load_css():
    try:
        with open("ui/styles.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Styles.css not found.")

