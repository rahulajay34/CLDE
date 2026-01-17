import streamlit as st
import difflib

def render_diff_view(old_text: str, new_text: str):
    """
    Renders a side-by-side or inline diff of the text changes.
    """
    if not old_text or not new_text:
        return

    # Use difflib to generate HTML diff
    d = difflib.HtmlDiff()
    
    # Custom CSS to inject into the HTML diff for better visibility
    # We strip the default header/legend to save space
    html = d.make_file(
        old_text.splitlines(), 
        new_text.splitlines(), 
        context=True, 
        numlines=2
    )
    
    # CSS injection to make it look nicer in Streamlit
    custom_css = """
    <style>
        .diff { font-family: monospace; font-size: 0.9em; width: 100%; }
        .diff td { padding: 2px 5px; }
        .diff_add { background-color: #d4fcd4; color: black; }
        .diff_chg { background-color: #ffffcc; color: black; }
        .diff_sub { background-color: #fcd4d4; color: black; text-decoration: line-through; }
        .diff_header { display: none; } 
    </style>
    """
    
    st.markdown("### 🔄 Change Analysis")
    st.components.v1.html(custom_css + html, height=400, scrolling=True)
