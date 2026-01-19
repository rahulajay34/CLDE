import os
import json
import time
import uuid

class VersionManager:
    """
    Manages version control for generated content.
    Stores versions as JSON files in 'storage/versions/{topic_sanitized}'.
    """
    
    @staticmethod
    def get_version_dir(topic):
        # Sanitize topic for directory name
        safe_topic = "".join([c if c.isalnum() else "_" for c in topic]).strip().lower()[:50]
        # Use a fallback if empty
        if not safe_topic: center_topic = "untitled"
        
        path = f"storage/versions/{safe_topic}"
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def save_version(topic, content: str, mode: str, summary: str = ""):
        """
        Saves a distinct version of the content.
        """
        version_id = str(uuid.uuid4())[:8]
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        data = {
            "version_id": version_id,
            "timestamp": timestamp,
            "topic": topic,
            "mode": mode,
            "content": content,
            "summary": summary
        }
        
        # Determine filename: v_{timestamp}_{id}.json
        filename = f"{int(time.time())}_{version_id}.json"
        save_path = os.path.join(VersionManager.get_version_dir(topic), filename)
        
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return version_id
        except Exception as e:
            print(f"Error saving version: {e}")
            return None

    @staticmethod
    def list_versions(topic):
        """
        Returns a sorted list of versions (newest first).
        """
        path = VersionManager.get_version_dir(topic)
        if not os.path.exists(path):
            return []
            
        versions = []
        for f in os.listdir(path):
            if f.endswith(".json"):
                full_path = os.path.join(path, f)
                try:
                    with open(full_path, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        versions.append(data)
                except:
                    pass
        
        # Sort by timestamp descending
        versions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return versions

    @staticmethod
    def restore_version(topic, version_id):
        """
        Retrieves a specific version content.
        """
        versions = VersionManager.list_versions(topic)
        for v in versions:
            if v["version_id"] == version_id:
                return v
        return None
