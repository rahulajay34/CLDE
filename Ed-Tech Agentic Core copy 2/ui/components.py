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
    # Sync with persistent state if available
    if "topic" in st.session_state and "topic_input" not in st.session_state:
        st.session_state.topic_input = st.session_state.topic
    if "subtopics" in st.session_state and "subtopic_input" not in st.session_state:
        st.session_state.subtopic_input = st.session_state.subtopics
        
    if "topic_input" not in st.session_state: st.session_state.topic_input = ""
    if "subtopic_input" not in st.session_state: st.session_state.subtopic_input = ""

    # Helper to set state
    def set_example(t, s):
        st.session_state.topic_input = t
        st.session_state.subtopic_input = s
        # Update persistent mirror immediately for better UX
        st.session_state.topic = t
        st.session_state.subtopics = s

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
    # Callback to sync with persistent state identifiers
    def sync_inputs():
        st.session_state.topic = st.session_state.topic_input
        st.session_state.subtopics = st.session_state.subtopic_input

    col1, col2 = st.columns([2, 1])
    
    with col1:
        topic = st.text_input("Topic", placeholder="e.g. Photosynthesis", key="topic_input", on_change=sync_inputs)
        subtopics = st.text_area("Subtopics / Context", placeholder="e.g. Key concepts to cover...", height=100, key="subtopic_input", on_change=sync_inputs)
    
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
def render_generation_status(orchestrator, topic, subtopics, transcript_text, mode, target_audience="General Student", status_placeholder=None, preview_placeholder=None, critique_placeholder=None):
    """
    Handles the generation loop with a compact, real-time status ticker.
    """
    # Use passed placeholder or create one if missing (fallback)
    if status_placeholder is None:
        status_placeholder = st.empty()
    
    # We want the progress bar and ticker INSIDE this placeholder
    with status_placeholder.container():
        # Create elements
        ticker_area = st.empty()
        # Progress bar needs to be updated, so keep a reference. 
        # But st.progress cannot be easily updated if created inside a container without 'empty' trick?
        # Actually st.progress returns an object we can update.
        progress_bar = st.progress(0, text="Initializing...")
    
    # Simple progress heuristic based on typical steps
    # Creator -> Auditor -> Pedagogue -> (Loop) -> Sanitizer -> Editor
    # Roughly 5-6 major steps per iteration.
    progress_value = 0
    
    def update_ticker(agent, status, progress_v):
        # Concise ticker style
        # e.g., "🟢 [Creator] Drafting content..." 
        icon = "🟢" if agent != "Done" else "✅"
        msg = f"**{agent}** | {status}"
        
        # Determine color/style based on agent
        color_map = {
            "Creator": "blue",
            "Auditor": "orange",
            "Pedagogue": "violet",
            "Sanitizer": "green", 
            "Editor": "blue",
            "Done": "green",
            "System": "gray"
        }
        color = color_map.get(agent, "gray")
        
        ticker_html = f"""
        <div style="
            background-color: #F3F4F6; 
            border: 1px solid #E5E7EB; 
            border-radius: 8px; 
            padding: 8px 16px; 
            display: flex; 
            align-items: center; 
            gap: 12px; 
            margin-bottom: 20px;
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            color: #1F2937;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        ">
            <span style="font-size: 1.2rem;">{icon}</span>
            <span style="font-weight: 600; color: {color}; min-width: 80px;">{agent}</span>
            <span style="color: #6B7280; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 600px;">{status}</span>
        </div>
        """
        ticker_area.markdown(ticker_html, unsafe_allow_html=True)
        progress_bar.progress(min(progress_v, 100))

    # Helpers for Animation
    def simulate_typing(text, speed=0.005):
        """Yields words from text to simulate typing."""
        tokens = text.split(" ")
        for token in tokens:
            yield token + " "
            time.sleep(speed)

    def generate_diff_html(old_text, new_text):
        """Generates HTML with animations for changes."""
        import difflib
        matcher = difflib.SequenceMatcher(None, old_text.split(), new_text.split())
        html = []
        for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
            if opcode == 'equal':
                html.append(" ".join(old_text.split()[a0:a1]))
            elif opcode == 'insert':
                inserted = " ".join(new_text.split()[b0:b1])
                html.append(f'<span class="highlight-anim diff-add">{inserted}</span>')
            elif opcode == 'delete':
                # We can choose to show deleted text or not. For "cleaning", show it?
                # User asked for "cleaning it", so showing removal is cool.
                deleted = " ".join(old_text.split()[a0:a1])
                html.append(f'<span class="highlight-anim diff-remove">{deleted}</span>')
            elif opcode == 'replace':
                deleted = " ".join(old_text.split()[a0:a1])
                inserted = " ".join(new_text.split()[b0:b1])
                html.append(f'<span class="highlight-anim diff-remove">{deleted}</span> <span class="highlight-anim diff-add">{inserted}</span>')
        return " ".join(html)

    # Track data
    current_draft = ""
    # We maintain previous_content to compute surgical diffs
    previous_content = ""
    
    final_result = None
    audit_log = [] 

    try:
        update_ticker("System", "Initializing agents...", 5)

        for event in orchestrator.run_loop(topic, subtopics, transcript_text, mode=mode, target_audience=target_audience):
            
            if not isinstance(event, dict): continue
            audit_log.append(event)
                
            if event.get("type") == "FINAL_RESULT":
                final_result = event
                update_ticker("Done", "Process Complete", 100)
                # Final render
                if preview_placeholder and event.get("content"):
                    preview_placeholder.markdown(event.get("content"))
                break
            
            if event.get("type") == "error":
                st.error(event.get("message"))
                continue

            # Render Step Event
            if event.get("type") == "step":
                agent = event.get("agent", "System")
                status = event.get("status", "Working...")
                content = event.get("content")
                
                # Heuristic Progress Update
                if agent == "Creator": progress_value = 20
                elif agent == "Auditor": progress_value = 40
                elif agent == "Pedagogue": progress_value = 60
                elif agent == "Sanitizer": progress_value = 80
                elif agent == "Editor": progress_value = 90
                
                update_ticker(agent, status, progress_value)
                
                # ANIMATION LOGIC
                if content and preview_placeholder:
                    # Filter out non-draft content (JSONs etc)
                    if isinstance(content, str) and len(content) > 50 and not content.strip().startswith("{"):
                        
                        # CREATOR: Typewriter Effect (only if new)
                        if agent == "Creator" and content != current_draft:
                            current_draft = content
                            # Clear and stream
                            preview_placeholder.empty()
                            # st.write_stream is standard for this
                            preview_placeholder.write_stream(simulate_typing(content))
                            previous_content = content
                        
                        # EDITOR/SANITIZER: Surgical Diff Animation
                        elif agent in ["Editor", "Sanitizer"] and content != current_draft:
                             current_draft = content
                             # Compute Diff HTML
                             diff_html = generate_diff_html(previous_content, content)
                             
                             # Render Diff
                             preview_placeholder.markdown(diff_html, unsafe_allow_html=True)
                             
                             # Wait for animation to play (2s)
                             time.sleep(2.5)
                             
                             # Replace with Clean Markdown
                             preview_placeholder.markdown(content)
                             previous_content = content
                        
                        else:
                            # Fallback
                            preview_placeholder.markdown(content)

                
                # Show Critiques (Compact)
                if agent == "Auditor" and content and critique_placeholder:
                    try:
                        import json
                        audit_data = json.loads(content)
                        critiques = audit_data.get("critiques", [])
                        if critiques:
                             pass 
                    except:
                        pass 

        # Cleanup
        progress_bar.empty()
        
        if "audit_log" not in st.session_state:
            st.session_state.audit_log = []
        st.session_state.audit_log = audit_log
        
        return final_result

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None
