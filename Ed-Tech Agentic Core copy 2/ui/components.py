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
            transcript_text = transcript_file.read().decode("utf-8")
            st.success(f"Loaded {len(transcript_text)} characters")

        mode = st.radio("Content Type", ["Lecture Notes", "Assignment"], horizontal=True)
        
    return topic, subtopics, transcript_text, mode

def render_generation_status(orchestrator, topic, subtopics, transcript_text, mode):
    """
    Handles the generation loop and status display.
    """
    # Placeholder for live activity feed
    activity_placeholder = st.container()
    status_container = st.status("Initializing Agent Swarm...", expanded=True)
    final_result = None
    
    try:
        for event in orchestrator.run_loop(topic, subtopics, transcript_text, mode=mode):
            
            if not isinstance(event, dict): 
                st.info(str(event))
                continue
                
            if event.get("type") == "FINAL_RESULT":
                final_result = event
                break
            
            if event.get("type") == "error":
                st.error(event.get("message"))
                continue

            # Render Step Event
            if event.get("type") == "step":
                agent = event.get("agent", "System")
                model = event.get("model", "")
                status = event.get("status", "")
                cost = event.get("cost", 0.0)
                
                icon = "🤖"
                if agent == "Creator": icon = "✍️"
                elif agent == "Auditor": icon = "🔍"
                elif agent == "Pedagogue": icon = "🎓"
                elif agent == "Sanitizer": icon = "🧹"
                elif agent == "Editor": icon = "📝"
                
                label = f"{icon} **{agent}** ({model}): {status}"
                if cost > 0:
                    label += f" — `₹{cost:.4f}`"
                
                with activity_placeholder.expander(label, expanded=True):
                    if event.get("tokens") != (0,0):
                        in_t, out_t = event["tokens"]
                        st.caption(f"Input Tokens: {in_t} | Output Tokens: {out_t}")
                    
                    content = event.get("content")
                    if content:
                        if isinstance(content, str) and content.strip().startswith(("{", "[")):
                             st.code(content, language="json")
                        else:
                             st.markdown(str(content)[:1000] + ("..." if len(str(content))>1000 else ""))

        status_container.update(label="Generation Complete!", state="complete", expanded=False)
        return final_result

    except Exception as e:
        status_container.update(label="Generation Failed", state="error")
        st.error(f"An unexpected error occurred: {e}")
        return None
