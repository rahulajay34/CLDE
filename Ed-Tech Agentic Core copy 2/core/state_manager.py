import streamlit as st
import json
import os
import uuid

class StateManager:
    @staticmethod
    def get_state_file():
        """Returns the path to the current session's state file."""
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        # Ensure directory exists
        os.makedirs("storage/sessions", exist_ok=True)
        return f"storage/sessions/{st.session_state.session_id}.json"

    @staticmethod
    def initialize_state():
        # Ensure session_id exists immediately
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())

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
            default_model = "claude-3-haiku-20240307"
            # Ensure custom default is in allowed list, otherwise fallback? 
            # Assuming config is robust, but for safety lets specific textual ID if possible or rely on string.
            
            st.session_state.model_config = {
                "creator": default_model,
                "auditor": default_model,
                "editor": default_model,
                "sanitizer": default_model,
                "max_iterations": 3
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
    def save_checkpoint(draft, iteration):
        st.session_state.current_draft = draft
        st.session_state.iteration = iteration
        StateManager.save_to_disk()

    @staticmethod
    def save_to_disk():
        """Saves critical session state to a local JSON file."""
        state_file = StateManager.get_state_file()
        
        state_data = {
            "session_id": st.session_state.session_id,
            "view": st.session_state.get("view", "dashboard"),
            "model_config": st.session_state.get("model_config", {}),
            "total_cost": st.session_state.get("total_cost", 0.0),
            "topic": st.session_state.get("topic", ""),
            "subtopics": st.session_state.get("subtopics", ""),
            "target_audience": st.session_state.get("target_audience", "General Student"),
            "mode": st.session_state.get("mode", "Lecture Notes"),
            "current_draft": st.session_state.get("current_draft", ""),
            "iteration": st.session_state.get("iteration", 0),
            "generated_mode": st.session_state.get("generated_mode", "Lecture Notes")
        }
        try:
            with open(state_file, "w") as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")

    @staticmethod
    def load_from_disk():
        """Loads critical session state from local JSON file."""
        # Getting state file will initialize session_id if missing, which is good.
        # However, if we are loading, we might want to load a specific session?
        # For now, we assume implicit session continuity via cookie/streamlit session.
        # If st.session_state is fresh, we get a new session ID, so we won't load old data unless we implement a way to restore session.
        # But per requirements: "Implement session-based isolation." -> This implies isolation is key.
        state_file = StateManager.get_state_file()
        
        if not os.path.exists(state_file):
            return
            
        try:
            with open(state_file, "r") as f:
                saved_state = json.load(f)
            
            # Restore values into session state
            for key, value in saved_state.items():
                if key not in st.session_state:
                    st.session_state[key] = value
        except Exception as e:
            print(f"Error loading state: {e}")

    @staticmethod
    def clear_session():
        """Clears the current session data from disk and memory."""
        state_file = StateManager.get_state_file()
        if os.path.exists(state_file):
            try:
                os.remove(state_file)
            except Exception as e:
                print(f"Error deleting state file: {e}")
        
        # Clear Session State (keep necessary keys if needed, or just clear all)
        # We should keep session_id to generate a fresh one or just clear.
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        StateManager.initialize_state()

    @staticmethod
    def get_session_val(key, default=None):
        return st.session_state.get(key, default)
