import os
import json
import time
import random
import functools
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Callable, Type
from core.logger import logger
from core.config import MAX_RETRIES, INITIAL_BACKOFF, BACKOFF_FACTOR

def retry_with_backoff(
    retries: int = MAX_RETRIES,
    initial_backoff: float = INITIAL_BACKOFF,
    backoff_factor: float = BACKOFF_FACTOR,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry a function with exponential backoff.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            backoff = initial_backoff
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries - 1:
                        logger.error(f"Function {func.__name__} failed after {retries} attempts. Error: {e}")
                        raise e
                    
                    sleep_time = backoff + random.uniform(0, 0.1) # Add jitter
                    logger.warning(f"Attempt {attempt+1}/{retries} for {func.__name__} failed: {e}. Retrying in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    backoff *= backoff_factor
            return None # Should be unreachable
        return wrapper
    return decorator

def get_timestamp_filename(topic: str, file_type: str) -> str:
    """Generates a filename like 2026-01-18_Fetch-API_LectureNotes.md"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    sanitized_topic = topic.replace(" ", "-").replace("/", "-")
    return f"{date_str}_{sanitized_topic}_{file_type}.md"

def save_markdown_file(content: str, filename: str, subfolder: str = "Lecture-Notes"):
    """Saves markdown content to the specified storage subfolder."""
    base_path = os.path.join(os.getcwd(), "storage", subfolder)
    os.makedirs(base_path, exist_ok=True)
    full_path = os.path.join(base_path, filename)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return full_path

def save_metadata(metadata: Dict[str, Any], filename: str, subfolder: str = "Lecture-Notes"):
    """Saves a sidecar JSON metadata file."""
    base_path = os.path.join(os.getcwd(), "storage", subfolder)
    json_filename = filename.replace(".md", ".json")
    full_path = os.path.join(base_path, json_filename)
    
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    return full_path

def save_excel(data: list, filename: str, subfolder: str = "Assignments"):
    """Saves assignment data to Excel."""
    base_path = os.path.join(os.getcwd(), "storage", subfolder)
    os.makedirs(base_path, exist_ok=True)
    xlsx_filename = filename.replace(".md", ".xlsx")
    full_path = os.path.join(base_path, xlsx_filename)
    
    df = pd.DataFrame(data)
    df.to_excel(full_path, index=False)
    
    return full_path

def load_recent_files(limit: int = 5):
    """Scans storage directories for recent markdown files."""
    files = []
    storage_path = os.path.join(os.getcwd(), "storage")
    
    for root, _, filenames in os.walk(storage_path):
        for name in filenames:
            if name.endswith(".md"):
                full_path = os.path.join(root, name)
                files.append({
                    "name": name,
                    "path": full_path,
                    "time": os.path.getmtime(full_path)
                })
    
    # Sort by modification time desc
    files.sort(key=lambda x: x["time"], reverse=True)
    return files[:limit]
