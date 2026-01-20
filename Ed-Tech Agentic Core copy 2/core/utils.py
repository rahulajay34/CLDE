import time
import random
import asyncio
import functools
import os
import io
import json
import re
from datetime import datetime
import logging

logger = logging.getLogger("EdTechCore")

def retry_with_backoff(retries=3, base_delay=1, backoff_factor=2, exceptions=(Exception,)):
    """
    Async decorator for exponential backoff retries.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"Retry {i+1}/{retries} for {func.__name__} due to: {e}")
                    if i == retries - 1:
                        break
                    await asyncio.sleep(delay + random.uniform(0, 0.1))
                    delay *= backoff_factor
            if last_exception:
                raise last_exception
        return wrapper
    return decorator

def get_timestamp_filename(prefix, ext):
    """Generates a filename with current timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{ext}"

def save_markdown_file(content, filename):
    """Saves string content to 'outputs/' directory."""
    output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

def save_metadata(metadata, filename):
    """Saves dictionary as JSON to 'outputs/' directory."""
    output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    return filepath

def save_excel(data, filename):
    """Saves list of dicts to Excel in 'outputs/' directory."""
    import pandas as pd
    output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False)
    return filepath

def clean_meta_commentary(text: str) -> str:
    """
    Removes common internal monologue or meta-commentary phrases 
    that LLMs sometimes leak into final fields.
    """
    if not text:
        return ""
        
    # List of regex patterns to strip out
    patterns = [
        r"Let me adjust.*",
        r"I need to ensure.*",
        r"Note: I have.*",
        r"Correction:.*",
        r"This gives \d+ correct answers.*",
        r"Based on the analysis.*",
        r"After re-evaluating.*",
        r"^Okay, I will.*",
        r"^Here is the corrected.*"
    ]
    
    clean_text = text
    for p in patterns:
        clean_text = re.sub(p, "", clean_text, flags=re.IGNORECASE | re.MULTILINE)
        
    
    return clean_text.strip()

def load_recent_files(directory="outputs", extension=None, limit=5):
    """
    Returns a list of recent files in the given directory.
    """
    output_dir = os.path.join(os.getcwd(), directory)
    if not os.path.exists(output_dir):
        return []
    
    files = []
    with os.scandir(output_dir) as entries:
        for entry in entries:
            if entry.is_file():
                if extension and not entry.name.endswith(extension):
                    continue
                stats = entry.stat()
                files.append({
                    "name": entry.name,
                    "path": entry.path,
                    "ctime": stats.st_ctime,
                    "mtime": stats.st_mtime,
                    "size": stats.st_size
                })
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files[:limit]
