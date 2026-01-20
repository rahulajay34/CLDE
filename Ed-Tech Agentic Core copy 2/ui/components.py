import streamlit as st
import streamlit.components.v1 as components
import time
import html
from core.config import PAGE_TITLE, PAGE_ICON
from ui.diff_viewer import render_diff_view

class ProgressTracker:
    def __init__(self, expected_steps=8):
        self.start_time = time.time()
        self.step_start_time = time.time()
        self.completed_steps = 0
        self.expected_steps = expected_steps
        self.step_durations = []

    def mark_step_complete(self):
        now = time.time()
        duration = now - self.step_start_time
        self.step_durations.append(duration)
        self.completed_steps += 1
        self.step_start_time = now

    def get_remaining_seconds(self):
        remaining = self.expected_steps - self.completed_steps
        if remaining <= 0: return 0
        # Average of last 3 steps or default 8s
        recent = self.step_durations[-3:] if self.step_durations else []
        avg = sum(recent) / len(recent) if recent else 8.0
        return int(remaining * avg)

    def get_percent(self):
        return min(100, int((self.completed_steps / self.expected_steps) * 100))

def render_mermaid(code: str, height=500):
    """
    Renders a Mermaid diagram using a custom HTML component.
    """
    # Escaping is CRITICAL to prevent HTML parsing from breaking the diagram syntax (e.g. arrows -> become HTML tags)
    escaped_code = html.escape(code)
    
    html_code = f"""
    <div class="mermaid" style="text-align: center;">
        {escaped_code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.9.3/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
    </script>
    """
    components.html(html_code, height=height, scrolling=True)

def render_markdown_with_mermaid(content: str):
    """
    Renders markdown content, automatically detecting and rendering Mermaid diagrams.
    """
    import re
    # More robust regex to capture mermaid blocks
    # Matches ```mermaid ... ``` (dotall)
    parts = re.split(r"(```mermaid\s*[\s\S]*?```)", content)
    
    for part in parts:
        if part.strip().startswith("```mermaid"):
            # Extract code safely
            # Remove first occurrence of ```mermaid and last occurrence of ```
            code = part.strip()
            if code.startswith("```mermaid"):
                code = code[10:]
            if code.endswith("```"):
                code = code[:-3]
            code = code.strip()
            
            st.write("### 🧜‍♀️ Diagram Preview")
            render_mermaid(code, height=600)
        else:
            if part.strip():
                 st.markdown(part)

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
    Returns: (topic, subtopics, transcript_text, mode, target_audience)
    """
    # 1. Mode Selection (Visual Pills)
    # Center this visually if possible
    st.markdown("<div style='text-align: center; margin-bottom: 1rem;'>", unsafe_allow_html=True)
    mode = st.radio(
        "Content Type", 
        ["Lecture Notes", "Assignment", "Pre-read Notes"], 
        horizontal=True, 
        label_visibility="collapsed", 
        key="mode_selector"
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Main Inputs (The "Search Engine" Focus)
    # Callback to sync with persistent state identifiers
    def sync_inputs():
        st.session_state.topic = st.session_state.topic_input
        st.session_state.subtopics = st.session_state.subtopic_input

    # Initialize inputs
    if "topic" in st.session_state and "topic_input" not in st.session_state:
        st.session_state.topic_input = st.session_state.topic
    if "subtopics" in st.session_state and "subtopic_input" not in st.session_state:
        st.session_state.subtopic_input = st.session_state.subtopics

    # Primary Input: Topic
    topic = st.text_input(
        "What do you want to teach?", 
        placeholder="e.g. The French Revolution", 
        key="topic_input", 
        on_change=sync_inputs
    )
    
    # Secondary Input: Context/Subtopics
    subtopics = st.text_area(
        "Key Concepts to Cover", 
        placeholder="e.g. Causes, Key Figures, Outcomes...", 
        height=80, 
        key="subtopic_input", 
        on_change=sync_inputs
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Progressive Disclosure: Advanced Options
    # Hide Audience and File Upload behind a toggle to reduce cognitive load
    transcript_text = None
    target_audience = "General Student" # Default
    assignment_config = {}

    if mode == "Assignment":
        st.markdown("##### 📝 Assignment Configuration")
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            n_mcsc = st.number_input("MCQ (Single)", min_value=0, max_value=20, value=5, help="Multiple Choice Single Correct")
        with ac2:
            n_mcmc = st.number_input("MSQ (Multi)", min_value=0, max_value=20, value=0, help="Multiple Choice Multi Correct")
        with ac3:
            n_subj = st.number_input("Subjective", min_value=0, max_value=10, value=0, help="Descriptive Questions")
        
        assignment_config = {
            "mcsc": n_mcsc,
            "mcmc": n_mcmc,
            "subjective": n_subj,
            "enable_dedup": st.checkbox("Enable Deduplication", value=False, help="Remove questions with >95% similarity")
        }
        st.divider()

    with st.expander("🛠️ Advanced Options (Audience & Files)"):
        # If Pre-read, we only show Audience, NO file upload needed
        if mode == "Pre-read Notes":
            st.caption("Target Audience")
            target_audience = st.selectbox(
                "Who is this for?",
                ["General Student", "Beginner (EL5)", "Advanced/Expert", "Researcher", "Child (Grade 1-5)"],
                index=0,
                label_visibility="collapsed"
            )
            st.info("ℹ️ Transcript upload is disabled for Pre-read Notes.")
        else:
            c1, c2 = st.columns([1, 1])
            
            with c1:
                st.caption("Target Audience")
                target_audience = st.selectbox(
                    "Who is this for?",
                    ["General Student", "Beginner (EL5)", "Advanced/Expert", "Researcher", "Child (Grade 1-5)"],
                    index=0,
                    label_visibility="collapsed"
                )
                
            with c2:
                st.caption("Reference Material")
                transcript_file = st.file_uploader("Upload Transcript/Notes", type=["txt", "md"], label_visibility="collapsed")
                if transcript_file:
                    with st.spinner("Ingesting file..."):
                        transcript_text = transcript_file.read().decode("utf-8")
                    st.success(f"Loaded {len(transcript_text)} characters")

    st.divider()

    # 4. Quick Start Chips (Moved to dropdown)
    with st.expander("💡 Need inspiration? Try an example", expanded=False):
        cols_chips = st.columns(4)
        
        def set_example(t, s):
            st.session_state.topic_input = t
            st.session_state.subtopic_input = s
            st.session_state.topic = t
            st.session_state.subtopics = s
            st.rerun()

        with cols_chips[0]:
            st.button("🌿 Photosynthesis", on_click=set_example, args=("Photosynthesis", "Light-dependent reactions, Calvin Cycle"), use_container_width=True)
        with cols_chips[1]:
            st.button("⚔️ French Rev.", on_click=set_example, args=("The French Revolution", "Causes, Bastille, Reign of Terror"), use_container_width=True)
        with cols_chips[2]:
            st.button("⚛️ Quantum Mech.", on_click=set_example, args=("Intro to Quantum Mechanics", "Wave-particle duality, Schrödinger equation"), use_container_width=True)
        with cols_chips[3]:
            st.button("🧬 DNA Replication", on_click=set_example, args=("DNA Replication", "Helicase, Polymerase, Leading vs Lagging"), use_container_width=True)

    return topic, subtopics, transcript_text, mode, target_audience, assignment_config

def render_custom_error(title, message, details=None):
    """
    Renders a user-friendly error message.
    """
    error_html = f"""
    <div class="error-box">
        <span style="font-size: 1.5rem;">⚠️</span>
        <div>
            <div style="font-weight: 600; font-size: 1.05rem;">{title}</div>
            <div style="margin-top: 4px;">{message}</div>
            {f'<div style="margin-top: 8px; font-size: 0.9rem; opacity: 0.8; font-family: monospace;">{details}</div>' if details else ''}
        </div>
    </div>
    """
    st.markdown(error_html, unsafe_allow_html=True)

def render_typing_indicator():
    return """
    <div style="display: inline-block; margin-left: 8px;">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
    </div>
    """

@st.fragment
async def render_generation_status(orchestrator, topic, subtopics, transcript_text, mode, target_audience="General Student", status_placeholder=None, preview_placeholder=None, critique_placeholder=None, assignment_config=None):
    """
    Handles the generation loop with a compact, real-time status ticker.
    """
    # Use passed placeholder or create one if missing (fallback)
    if status_placeholder is None:
        status_placeholder = st.empty()
    
    # Initialize Tracker
    tracker = ProgressTracker(expected_steps=8) # Approx: Creator + 3*(Audit+Editor) + Save

    # We want the progress bar and ticker INSIDE this placeholder
    with status_placeholder.container():
        # Layout: [Status & Bar] ... [Time]
        c_status, c_time = st.columns([4, 1])
        with c_status:
            ticker_area = st.empty()
            progress_bar = st.progress(0, text="Initializing...")
        with c_time:
            time_display = st.empty()
            cost_display = st.empty() # Add cost display
            
    # Container for iteration history (Diffs) - Separate from status bar
    history_container = st.container()

    def update_ticker(agent, status, step_complete=False, current_cost=0.0):
        if step_complete:
            tracker.mark_step_complete()

        percent = tracker.get_percent()
        # Cap percent at 95% until explicitly "Done"
        if agent != "Done":
            percent = min(95, percent)
            
        rem_sec = tracker.get_remaining_seconds()
        elapsed = int(time.time() - tracker.start_time)
        
        # Update Time & Cost
        time_display.metric("Time", f"{elapsed}s", help=f"Est. remaining: {rem_sec}s")
        cost_display.metric("Cost", f"₹{current_cost:.4f}")

        # Concise ticker style
        icon = "🟢" if agent != "Done" else "✅"
        
        # Determine color/style based on agent
        color_map = {
            "Creator": "var(--color-primary)",
            "Auditor": "var(--color-warning)",
            "Pedagogue": "purple",
            "Sanitizer": "var(--color-success)", 
            "Editor": "var(--color-primary)",
            "Done": "var(--color-success)",
            "System": "gray"
        }
        color = color_map.get(agent, "gray")
        
        # Add shimmer effect for active agents
        shimmer_class = "ticker-shimmer" if agent != "Done" and agent != "System" else ""
        
        ticker_html = f"""
        <div class="{shimmer_class}" style="
            background-color: white; 
            border: 1px solid var(--color-border); 
            border-radius: 8px; 
            padding: 8px 16px; 
            display: flex; 
            align-items: center; 
            gap: 12px; 
            margin-bottom: 20px;
            font-family: var(--font-primary);
            font-size: 0.95rem;
            color: var(--color-text-primary);
            box-shadow: var(--shadow-sm);
        ">
            <span style="font-size: 1.2rem;">{icon}</span>
            <span style="font-weight: 600; color: {color}; min-width: 80px;">{agent}</span>
            <span style="color: var(--color-text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 600px;">{status}</span>
        </div>
        """
        ticker_area.markdown(ticker_html, unsafe_allow_html=True)
        progress_bar.progress(percent, text=f"{percent}% Complete")

    # Helpers for Animation
    def render_typing_indicator():
        return """
        <div style="display: inline-block; margin-left: 8px;">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
        """

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
        diff_html = []
        for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
            if opcode == 'equal':
                text_content = " ".join(old_text.split()[a0:a1])
                diff_html.append(html.escape(text_content))
            elif opcode == 'insert':
                inserted = " ".join(new_text.split()[b0:b1])
                diff_html.append(f'<span class="highlight-anim diff-add">{html.escape(inserted)}</span>')
            elif opcode == 'delete':
                deleted = " ".join(old_text.split()[a0:a1])
                diff_html.append(f'<span class="highlight-anim diff-remove">{html.escape(deleted)}</span>')
            elif opcode == 'replace':
                deleted = " ".join(old_text.split()[a0:a1])
                inserted = " ".join(new_text.split()[b0:b1])
                diff_html.append(f'<span class="highlight-anim diff-remove">{html.escape(deleted)}</span> <span class="highlight-anim diff-add">{html.escape(inserted)}</span>')
        return " ".join(diff_html)

    # Track data
    # Track diff state persistently
    if "diff_previous_content" not in st.session_state:
        st.session_state.diff_previous_content = ""
    
    current_draft = ""
    previous_content = st.session_state.diff_previous_content  # Load from state
    
    final_result = None
    audit_log = [] 
    
    if "total_cost" not in st.session_state:
        st.session_state["total_cost"] = 0.0
    
    current_run_cost = 0.0

    # Track streaming updates to reduce rendering freq
    last_update_time = time.time()
    
    try:
        current_agent = "System"
        current_status = "Initializing agents..."
        update_ticker(current_agent, current_status, current_cost=0.0)

        async for event in orchestrator.run_loop(topic, subtopics, transcript_text, mode=mode, target_audience=target_audience, assignment_config=assignment_config):
            
            if not isinstance(event, dict): continue
            audit_log.append(event)
            
            if "cost" in event and event["cost"] > 0:
                cost = event["cost"]
                st.session_state["total_cost"] += cost
                current_run_cost += cost
                update_ticker(current_agent, current_status, current_cost=current_run_cost)
                
            if event.get("type") == "FINAL_RESULT":
                final_result = event
                update_ticker("Done", "Process Complete", step_complete=True, current_cost=current_run_cost)
                if preview_placeholder and event.get("content"):
                    preview_placeholder.markdown(event.get("content"))
                break
            
            if event.get("type") == "verification_summary":
                 # Persist stats for the View layer
                 st.session_state["verification_summary"] = event.get("stats", {})
                 render_custom_error("Verification Report", event.get("content", ""), details="Check table for flagged issues.")
                 continue
            
            if event.get("type") == "error":
                render_custom_error("Agent Error", event.get("message"), details=f"Agent: {current_agent}")
                continue

            if event.get("type") == "stream":
                 chunk = event.get("content", "")
                 if chunk:
                     current_draft += chunk
                     # Debounce updates: Update if > 0.1s passed or draft grew significantly
                     now = time.time()
                     if now - last_update_time > 0.1: 
                         preview_placeholder.markdown(current_draft + "▌")
                         last_update_time = now
                 # Do not update ticker on every stream chunk to save re-renders
                 # update_ticker(current_agent, current_status, current_cost=current_run_cost)
                 continue

            if event.get("type") == "step":
                agent = event.get("agent", "System")
                status = event.get("status", "Working...")
                content = event.get("content")
                
                current_agent = agent
                current_status = status
                
                # Check if we should add typing indicator
                status_html = status
                if agent not in ["Done", "System"] and "Drafting" in status:
                     status_html += render_typing_indicator()

                # Basic heuristic for step completion
                is_complete_step = False
                if agent in ["Creator", "Editor", "Auditor"] and "Drafting" not in status: 
                     is_complete_step = True
                     
                update_ticker(agent, status_html, step_complete=is_complete_step, current_cost=current_run_cost)
                
                if agent == "Editor" and is_complete_step:
                     with history_container:
                         st.caption(f"Iteration Change")
                         render_diff_view(previous_content, current_draft)
                     # Update persistent state
                     st.session_state.diff_previous_content = current_draft
                     previous_content = current_draft
                
                if content and preview_placeholder and agent != "Creator":
                    if isinstance(content, str) and len(content) > 50 and not content.strip().startswith("{"):
                        if agent in ["Editor", "Sanitizer"] and content != current_draft:
                             diff_html = generate_diff_html(current_draft, content)
                             preview_placeholder.markdown(diff_html, unsafe_allow_html=True)
                             time.sleep(2.5)
                             preview_placeholder.markdown(content)
                             current_draft = content
                        else:
                            preview_placeholder.markdown(content)

                if agent == "Auditor" and content and critique_placeholder:
                    try:
                        import json
                        audit_data = json.loads(content)
                        # critiques = audit_data.get("critiques", []) # Unused
                    except:
                        pass 
        
        # Explicit Done Update ensure 100%
        # update_ticker("Done", "Complete", step_complete=True) # Handled by final_result

        # Cleanup
        progress_bar.empty()
        
        if "audit_log" not in st.session_state:
            st.session_state.audit_log = []
        st.session_state.audit_log = audit_log
        
        return final_result

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

def render_shortcuts():
    """
    Injects global keyboard shortcuts via JS.
    """
    js = """
    <script>
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Enter: Generate
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
             const buttons = Array.from(document.querySelectorAll('button'));
             const genBtn = buttons.find(b => b.innerText.includes('Generate Content'));
             if (genBtn) { 
                 genBtn.click(); 
                 return;
             }
        }
        
        // Ctrl/Cmd + S: Download
        if ((e.metaKey || e.ctrlKey) && e.key === 's') {
            e.preventDefault();
            const buttons = Array.from(document.querySelectorAll('button'));
            const dlBtn = buttons.find(b => b.innerText.includes('Download'));
            if (dlBtn) { dlBtn.click(); }
        }
        
        // Escape: Close Fullscreen / Modal
        if (e.key === 'Escape') {
             const buttons = Array.from(document.querySelectorAll('button'));
             const closeBtn = buttons.find(b => b.innerText.includes('Close') || b.innerText.includes('❌'));
             if (closeBtn) { closeBtn.click(); }
        }
    });
    </script>
    """
    components.html(js, height=0, width=0)
