import streamlit as st
import json
import os

STATE_FILE = ".user_state.json"

class StateManager:
    @staticmethod
    def initialize_state():
        # Try to load formatted state from disk first
        StateManager.load_from_disk()

        if "view" not in st.session_state:
            st.session_state.view = "dashboard" # Options: dashboard, editor, settings
        if "active_file" not in st.session_state:
            st.session_state.active_file = None # Tracks the current open project
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "total_cost" not in st.session_state:
            st.session_state.total_cost = 0.0
        if "current_draft" not in st.session_state:
            st.session_state.current_draft = None
        if "status_log" not in st.session_state:
            st.session_state.status_log = []
        if "recent_files" not in st.session_state:
            st.session_state.recent_files = []
        if "model_config" not in st.session_state:
            from core.config import ALLOWED_MODELS
            default_model = ALLOWED_MODELS[0]
            st.session_state.model_config = {
                "creator": default_model,
                "auditor": default_model,
                "editor": default_model,
                "sanitizer": ALLOWED_MODELS[-1] if len(ALLOWED_MODELS) > 1 else default_model,
                "max_iterations": 2
            }

    @staticmethod
    def navigate_to(view_name):
        st.session_state.view = view_name
        StateManager.save_to_disk()
        st.rerun()

    @staticmethod
    def set_active_file(filename):
        st.session_state.active_file = filename
        StateManager.save_to_disk()

    @staticmethod
    def add_cost(amount: float):
        st.session_state.total_cost += amount
        StateManager.save_to_disk()

    @staticmethod
    def log(message: str):
        st.session_state.status_log.append(message)
        
    @staticmethod
    def save_to_disk():
        """Saves critical session state to a local JSON file."""
        state_data = {
            "view": st.session_state.get("view", "dashboard"),
            "model_config": st.session_state.get("model_config", {}),
            "total_cost": st.session_state.get("total_cost", 0.0),
            "topic": st.session_state.get("topic", ""),
            "subtopics": st.session_state.get("subtopics", ""),
            "target_audience": st.session_state.get("target_audience", "General Student"),
            "mode": st.session_state.get("mode", "Lecture Notes"),
            # We avoid saving massive content like generated_content/transcript_text to keep it lightweight,
            # or we can save it if specifically requested. For now, keep settings/nav.
            "generated_mode": st.session_state.get("generated_mode", "Lecture Notes")
        }
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")

    @staticmethod
    def load_from_disk():
        """Loads critical session state from local JSON file."""
        if not os.path.exists(STATE_FILE):
            return
            
        try:
            with open(STATE_FILE, "r") as f:
                saved_state = json.load(f)
            
            # Restore values into session state
            for key, value in saved_state.items():
                if key not in st.session_state:
                    st.session_state[key] = value
        except Exception as e:
            print(f"Error loading state: {e}")
