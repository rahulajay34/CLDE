import streamlit as st
import difflib
import html

def render_diff_view(old_text: str, new_text: str):
    """
    Renders a side-by-side or inline diff of the text changes.
    """
    if not old_text or not new_text:
        return

    # Use unified_diff for a cleaner, GitHub-style view
    diff = difflib.unified_diff(
        old_text.splitlines(), 
        new_text.splitlines(), 
        lineterm=''
    )
    
    html_lines = []
    html_lines.append('<div style="font-family: monospace; font-size: 0.85rem; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden;">')
    
    has_changes = False
    for line in diff:
        has_changes = True
        if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
            continue
            
        clean_line = html.escape(line)
        if line.startswith('+'):
            html_lines.append(f'<div style="background-color: #ecfdf5; color: #065f46; padding: 2px 8px; border-left: 3px solid #10b981;">{clean_line}</div>')
        elif line.startswith('-'):
            html_lines.append(f'<div style="background-color: #fef2f2; color: #991b1b; padding: 2px 8px; border-left: 3px solid #ef4444; text-decoration: line-through;">{clean_line}</div>')
        else:
            # show context lines? maybe limit them?
            html_lines.append(f'<div style="color: #6b7280; padding: 2px 8px; border-left: 3px solid transparent;">{clean_line}</div>')
            
    html_lines.append('</div>')
    
    if has_changes:
        with st.expander("🔄 View Changes", expanded=False):
            st.markdown("".join(html_lines), unsafe_allow_html=True)
    else:
        st.info("No text changes detected.")
