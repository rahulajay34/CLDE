import streamlit as st

class StateManager:
    @staticmethod
    def initialize_state():
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

    @staticmethod
    def add_cost(amount: float):
        st.session_state.total_cost += amount

    @staticmethod
    def log(message: str):
        st.session_state.status_log.append(message)
