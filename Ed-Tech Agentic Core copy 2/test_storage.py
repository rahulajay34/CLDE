
import storage_manager
import os
import shutil
import pandas as pd

# Clean up
if os.path.exists("generated_content/Test_Topic"):
    shutil.rmtree("generated_content/Test_Topic")

print("Testing Storage Manager...")

# Test 1: Save Metadata
storage_manager.save_metadata("Test Topic", "Subtopic A", "claude-3-haiku")
assert os.path.exists("generated_content/Test Topic/metadata.json"), "Metadata not created"
print("✅ Metadata saved.")

# Test 2: Save Draft
path = storage_manager.save_draft("Test Topic", 1, "# Draft 1")
assert os.path.exists(path), "Draft not created"
print(f"✅ Draft saved at {path}")

# Test 3: Save Quiz
df = pd.DataFrame({"question": ["Q1"], "answer": ["A1"]})
path = storage_manager.save_quiz("Test Topic", df)
assert os.path.exists(path), "Quiz not created"
print(f"✅ Quiz saved at {path}")

# Test 4: List Sessions
sessions = storage_manager.list_saved_sessions()
assert "Test Topic" in sessions, "Test Topic not found in sessions"
print("✅ List sessions working.")

print("All tests passed.")
