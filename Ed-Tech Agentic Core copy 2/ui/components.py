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
    Renders the input fields for Topic and Subtopics.
    Returns: (topic, subtopics, transcript_text, mode)
    """
    col1, col2 = st.columns([2, 1])
    
    with col1:
        topic = st.text_input("Topic", placeholder="e.g. Photosynthesis")
        subtopics = st.text_area("Subtopics / Context", placeholder="e.g. Light-dependent reactions, Calvin Cycle...", height=100)
    
    with col2:
        transcript_file = st.file_uploader("Upload Transcript (Optional)", type=["txt", "md"])
        transcript_text = None
        if transcript_file:
            with st.spinner("Ingesting file..."):
                transcript_text = transcript_file.read().decode("utf-8")
            st.success(f"Loaded {len(transcript_text)} characters")

        mode = st.radio("Content Type", ["Lecture Notes", "Assignment"], horizontal=True)
        
    return topic, subtopics, transcript_text, mode

@st.fragment
def render_generation_status(orchestrator, topic, subtopics, transcript_text, mode, target_audience="General Student", preview_placeholder=None, critique_placeholder=None):
    """
    Handles the generation loop and status display.
    """
    # 1. VISUAL STEPPER (Mental Model)
    step_map = {"Creator": 0.2, "Auditor": 0.5, "Pedagogue": 0.6, "Editor": 0.8, "Sanitizer": 0.9}
    
    # Create a persistent container for the "Process Story"
    progress_bar = st.progress(0, text="Initializing Agent Swarm...")
    
    # Use a styled container for the "Active Agent" card
    agent_card = st.empty()
    
    # Track latest draft to ensure preview stays updated
    current_draft = ""
    final_result = None

    try:
        for event in orchestrator.run_loop(topic, subtopics, transcript_text, mode=mode, target_audience=target_audience):
            
            if not isinstance(event, dict): 
                continue
                
            if event.get("type") == "FINAL_RESULT":
                final_result = event
                progress_bar.progress(1.0, text="Generation Complete!")
                agent_card.empty() # Prepare for result
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
                
                icon = "🤖"
                if agent == "Creator": icon = "✍️"
                elif agent == "Auditor": icon = "🔍"
                elif agent == "Pedagogue": icon = "🎓"
                elif agent == "Sanitizer": icon = "🧹"
                elif agent == "Editor": icon = "📝"
                
                # UPDATE PROGRESS
                progress_val = step_map.get(agent, 0.1)
                progress_bar.progress(progress_val, text=f"**{agent}** is working: {status}")
                
                 # VISUAL CARD instead of Log
                with agent_card.container():
                     # Using a styled box for the active agent
                    st.markdown(f"""
                    <div style="padding: 15px; border-radius: 10px; background: rgba(99, 102, 241, 0.05); border: 1px solid #6366F1; margin-bottom: 20px;">
                        <h3 style="margin:0; font-size:1.1rem;">{icon} {agent}</h3>
                        <p style="margin:0; color: #4B5563;">{status}</p>
                    </div>
                    """, unsafe_allow_html=True)

                # SKELETON LOADER
                # If an agent is active but hasn't produced content yet, show skeleton in preview
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
                            # Do NOT update current_draft with JSON.
                            continue 
                        except:
                            pass # Fallback to default behavior if not JSON
                    
                    # Heuristic: if content is long and NOT json structure, it's likely a draft
                    if isinstance(content, str) and len(content) > 50 and not content.strip().startswith("{"):
                        current_draft = content
                        if preview_placeholder:
                             # Show skeleton or just update
                             preview_placeholder.markdown(f"### 📄 Draft ({agent})\n\n{content}")
                
                # HANDLE CRITIQUES (Auditor)
                if agent == "Auditor" and content and critique_placeholder:
                    try:
                        import json
                        audit_data = json.loads(content)
                        critiques = audit_data.get("critiques", [])
                        
                        if critiques:
                            with critique_placeholder.expander(f"⚠️ {len(critiques)} Critiques Found", expanded=True):
                                for c in critiques:
                                    severity = c.get("severity", "Info")
                                    color = "red" if severity == "Critical" else "orange"
                                    st.caption(f":{color}[{severity}] **{c.get('section', 'General')}**: {c.get('issue')}")
                    except:
                        pass 

        return final_result

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None
