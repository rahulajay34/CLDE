import streamlit as st
import time
from core.config import PAGE_TITLE, PAGE_ICON

def render_header():
    """Renders the main application header."""
    st.title(f"{PAGE_ICON} {PAGE_TITLE}")
    st.caption("The Gold Standard in Educational Content Generation")

def render_skeleton_loader():
    """
    Renders a skeleton loading state using CSS animation.
    Requires corresponding CSS in styles.css.
    """
    # Simple shimmering block representation
    skeleton_html = """
    <div class="skeleton-container">
        <div class="skeleton-header"></div>
        <div class="skeleton-text"></div>
        <div class="skeleton-text"></div>
        <div class="skeleton-text" style="width: 80%;"></div>
    </div>
    """
    st.markdown(skeleton_html, unsafe_allow_html=True)

def render_metric_card(label, value, delta=None):
    """Renders a styled metric card."""
    st.metric(label=label, value=value, delta=delta)

def render_input_area():
    """
    Renders the input fields for Topic and Subtopics with a 'Hero' style.
    Returns: (topic, subtopics, transcript_text, mode)
    """
    # 1. Mode Switch (Hero Segmented Control)
    # Using columns to center or style it, or just a prominent radio/pills
    st.write("### 🎯 Choose your Goal")
    mode = st.radio("Content Type", ["Lecture Notes", "Assignment"], horizontal=True, label_visibility="collapsed", key="mode_selector")
    
    st.divider()

    # 2. Quick Start Chips
    st.caption("🚀 Quick Start Examples")
    cols_chips = st.columns([1, 1, 1, 1])
    
    # Initialize session state for inputs if not present
    if "topic_input" not in st.session_state: st.session_state.topic_input = ""
    if "subtopic_input" not in st.session_state: st.session_state.subtopic_input = ""

    # Helper to set state
    def set_example(t, s):
        st.session_state.topic_input = t
        st.session_state.subtopic_input = s

    with cols_chips[0]:
        if st.button("🌿 Photosynthesis"): 
            set_example("Photosynthesis", "Light-dependent reactions, Calvin Cycle, Chloroplast structure")
    with cols_chips[1]:
        if st.button("⚔️ French Rev."):
            set_example("The French Revolution", "Causes (Social, Economic), The Storming of the Bastille, Reign of Terror")
    with cols_chips[2]:
        if st.button("⚛️ Quantum Mech."):
            set_example("Intro to Quantum Mechanics", "Wave-particle duality, Schrödinger equation, Uncertainty principle")
    with cols_chips[3]:
        if st.button("🧬 DNA Replication"):
            set_example("DNA Replication", "Helicase, Primase, DNA Polymerase, Leading vs Lagging strand")

    st.markdown("<br>", unsafe_allow_html=True) # Spacer

    # 3. Main Inputs
    col1, col2 = st.columns([2, 1])
    
    with col1:
        topic = st.text_input("Topic", placeholder="e.g. Photosynthesis", key="topic_input")
        subtopics = st.text_area("Subtopics / Context", placeholder="e.g. Key concepts to cover...", height=100, key="subtopic_input")
    
    with col2:
        transcript_file = st.file_uploader("Upload Transcript (Optional)", type=["txt", "md"])
        transcript_text = None
        if transcript_file:
            with st.spinner("Ingesting file..."):
                transcript_text = transcript_file.read().decode("utf-8")
            st.success(f"Loaded {len(transcript_text)} characters")

    st.divider()
    
    # 4. Target Audience (Moved from Sidebar)
    st.caption("🎯 Target Audience")
    target_audience = st.selectbox(
        "Who is this for?",
        ["General Student", "Beginner (EL5)", "Advanced/Expert", "Researcher", "Child (Grade 1-5)"],
        index=0,
        label_visibility="collapsed"
    )

    return topic, subtopics, transcript_text, mode, target_audience

@st.fragment
def render_generation_status(orchestrator, topic, subtopics, transcript_text, mode, target_audience="General Student", preview_placeholder=None, critique_placeholder=None):
    """
    Handles the generation loop and status display using Visual Chain of Custody.
    """
    # Define Agents
    agents = ["Creator", "Auditor", "Pedagogue", "Sanitizer", "Editor"]
    
    # Create the Visual Container
    status_container = st.empty()
    
    # Helper to render the visual chain
    def update_visuals(active_agent, log_message):
        # We build HTML for the chain
        html_content = '<div class="agent-flow-container">'
        
        for agent in agents:
            is_active = (agent == active_agent)
            active_class = "active" if is_active else ""
            
            # Icons mapping
            icons = {"Creator": "✍️", "Auditor": "🔍", "Pedagogue": "🎓", "Sanitizer": "🧹", "Editor": "📝"}
            
            # Use styling to show inactive/active/completed state logic could be added here
            # For now, following the user's pulse logic for active
            
            html_content += f"""
            <div class="agent-node {active_class}" style="text-align:center; flex:1;">
                <div class="agent-icon">{icons.get(agent, "🤖")}</div>
                <div class="agent-label">{agent}</div>
            </div>
            """
        html_content += "</div>"
        
        with status_container.container():
            st.markdown(html_content, unsafe_allow_html=True)
            # Terminal-like log
            st.markdown(f"""
            <div style="font-family: monospace; color: #6B7280; font-size: 0.9rem; padding: 10px; background: #F9FAFB; border-radius: 8px; margin-top: 10px;">
                <span style="color: #6366F1;">➜</span> {log_message}
            </div>
            """, unsafe_allow_html=True)

    # Track drafts
    current_draft = ""
    final_result = None
    audit_log = [] # Capture events for the Audit Trail

    try:
        # Initial State
        update_visuals("Creator", "Initializing ecosystem...")

        for event in orchestrator.run_loop(topic, subtopics, transcript_text, mode=mode, target_audience=target_audience):
            
            if not isinstance(event, dict): 
                continue
            
            # Add to audit log
            audit_log.append(event)
                
            if event.get("type") == "FINAL_RESULT":
                final_result = event
                update_visuals("Done", "Generation Complete! Finalizing...")
                # Ensure final draft is shown
                if preview_placeholder and event.get("content"):
                    preview_placeholder.markdown(event.get("content"))
                break
            
            if event.get("type") == "error":
                st.error(event.get("message"))
                continue

            # Render Step Event
            if event.get("type") == "step":
                agent = event.get("agent", "System")
                status = event.get("status", "")
                content = event.get("content")
                
                # Update Visuals
                update_visuals(agent, status)
                
                # SKELETON LOADER
                # If an agent is active but hasn't produced content yet (and we want to show it working)
                if agent in ["Creator", "Editor", "Sanitizer"] and not content and preview_placeholder:
                    with preview_placeholder.container():
                        render_skeleton_loader()
                
                # HANDLE DRAFT UPDATES (Creator, Editor, Sanitizer)
                if agent in ["Creator", "Editor", "Sanitizer"] and content:
                    # Special handling for Editor JSON
                    if agent == "Editor":
                        try:
                            import json
                            editor_data = json.loads(content)
                            continue 
                        except:
                            pass 
                    
                    if isinstance(content, str) and len(content) > 50 and not content.strip().startswith("{"):
                        current_draft = content
                        if preview_placeholder:
                             preview_placeholder.markdown(content)
                
                # HANDLE CRITIQUES (Auditor)
                if agent == "Auditor" and content and critique_placeholder:
                    try:
                        import json
                        audit_data = json.loads(content)
                        critiques = audit_data.get("critiques", [])
                        
                        if critiques:
                            with critique_placeholder.expander(f"⚠️ {len(critiques)} Critiques", expanded=True):
                                for c in critiques:
                                    severity = c.get("severity", "Info")
                                    color = "red" if severity == "Critical" else "orange"
                                    st.caption(f":{color}[{severity}] **{c.get('section', 'General')}**: {c.get('issue')}")
                    except:
                        pass 

        if "audit_log" not in st.session_state:
            st.session_state.audit_log = []
        st.session_state.audit_log = audit_log
        
        return final_result

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None
