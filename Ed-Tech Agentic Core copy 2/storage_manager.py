
import os
import re
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

ROOT_DIR = "generated_content"

def _sanitize_filename(name):
    """Sanitizes the name to remove illegal characters for directory names."""
    if not name:
        return "Untitled_Topic"
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def _get_timestamp():
    """Returns current timestamp string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def initialize_project_root():
    """Creates the root directory if it doesn't exist."""
    if not os.path.exists(ROOT_DIR):
        os.makedirs(ROOT_DIR)

def get_topic_folder(topic):
    """Creates and returns the topic folder path."""
    initialize_project_root()
    safe_topic = _sanitize_filename(topic)
    path = os.path.join(ROOT_DIR, safe_topic)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def save_metadata(topic, subtopic, model, prompt_template=""):
    """Saves metadata.json in the topic folder."""
    folder = get_topic_folder(topic)
    metadata = {
        "topic": topic,
        "subtopic": subtopic,
        "model": model,
        "last_updated": _get_timestamp()
    }
    
    file_path = os.path.join(folder, "metadata.json")
    with open(file_path, "w") as f:
        json.dump(metadata, f, indent=4)

def save_draft(topic, iteration, content):
    """Saves the draft notes."""
    folder = get_topic_folder(topic)
    filename = f"notes_draft_v{iteration}_{_get_timestamp()}.md"
    path = os.path.join(folder, filename)
    
    with open(path, "w", encoding='utf-8') as f:
        f.write(content)
    return path

def save_quiz(topic, quiz_df):
    """Saves the quiz dataframe."""
    folder = get_topic_folder(topic)
    filename = f"quiz_v{_get_timestamp()}.csv"
    path = os.path.join(folder, filename)
    quiz_df.to_csv(path, index=False)
    return path

def list_saved_sessions():
    """Returns a list of topic folders in the root directory."""
    initialize_project_root()
    folders = []
    if os.path.exists(ROOT_DIR):
        for name in os.listdir(ROOT_DIR):
            path = os.path.join(ROOT_DIR, name)
            if os.path.isdir(path):
                folders.append(name)
    return sorted(folders)
