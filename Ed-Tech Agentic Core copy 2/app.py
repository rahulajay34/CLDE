import streamlit as st
import os
from core.state_manager import StateManager
from core.config import PAGE_TITLE, PAGE_ICON, LAYOUT
from core.logger import logger
from ui.layout import render_sidebar, load_css
from ui.components import render_header
from ui.views import render_dashboard, render_editor, render_settings

# --- APP SETUP ---
st.set_page_config(page_title=PAGE_TITLE, layout=LAYOUT, page_icon=PAGE_ICON)

# Initialize State Logic
StateManager.initialize_state()

# Load Global CSS (Glassmorphism, Resets)
load_css()

# --- RAG INITIALIZATION ---
try:
    from core.rag import RAGManager
    # Initialize only if not present to avoid reloading heavy models
    if "rag_manager" not in st.session_state:
        st.session_state.rag_manager = RAGManager()
except ImportError:
    st.session_state.rag_manager = None
except Exception as e:
    logger.error(f"RAG Init Error: {e}")
    st.session_state.rag_manager = None

# --- SIDEBAR (NAVIGATION) ---
# render_sidebar handles valid navigation state changes via StateManager
rag_enabled = render_sidebar()
st.session_state.rag_enabled = rag_enabled

# --- FILE INGESTION (Linear Process) ---
if "uploaded_files" in st.session_state and st.session_state.rag_manager:
    for uploaded_file in st.session_state["uploaded_files"]:
        # Save temp to ingest
        temp_path = os.path.join("storage", uploaded_file.name)
        os.makedirs("storage", exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Ingest
        st.session_state.rag_manager.ingest_document(temp_path, uploaded_file.name)
        st.toast(f"Ingested {uploaded_file.name} into Knowledge Base")
    
    del st.session_state["uploaded_files"] # Clear queue

# --- MAIN LAYOUT ---
# Header is global
render_header()

# Router Logic
current_view = st.session_state.get("view", "dashboard")

# Dynamic View Rendering
if current_view == "dashboard":
    render_dashboard()
elif current_view == "editor":
    render_editor()
elif current_view == "settings":
    render_settings()
else:
    # Fallback
    render_dashboard()