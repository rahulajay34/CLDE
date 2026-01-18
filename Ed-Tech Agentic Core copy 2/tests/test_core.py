import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import os
import shutil
import tempfile
from core.state_manager import StateManager
from core.orchestrator import Orchestrator

class TestStateManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        # Mock streamlit session state
        self.patcher = patch('core.state_manager.st')
        self.mock_st = self.patcher.start()
        class SessionState(dict):
            def __getattr__(self, item):
                return self.get(item)
            def __setattr__(self, key, value):
                self[key] = value

        self.mock_st.session_state = SessionState()

    def tearDown(self):
        self.patcher.stop()
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_session_isolation(self):
        # Simulate two different sessions
        # Define the SessionState class locally or reuse from setUp if I put it there. 
        # But I need to reset it.
        class SessionState(dict):
            def __getattr__(self, item):
                return self.get(item)
            def __setattr__(self, key, value):
                self[key] = value
        
        self.mock_st.session_state = SessionState()
        StateManager.initialize_state()
        session1 = self.mock_st.session_state["session_id"]
        file1 = StateManager.get_state_file()
        
        # Save data
        self.mock_st.session_state["test"] = 123
        StateManager.save_to_disk()
        self.assertTrue(os.path.exists(file1))
        
        # New Session
        self.mock_st.session_state = SessionState()
        StateManager.initialize_state()
        session2 = self.mock_st.session_state["session_id"]
        file2 = StateManager.get_state_file()
        
        self.assertNotEqual(session1, session2)
        self.assertNotEqual(file1, file2)

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.config_mock = MagicMock()
        self.config_mock.max_iterations = 1
        self.config_mock.creator.model = "test-model"
        # Mock other config fields...
        
    @patch('core.orchestrator.AnthropicClient')
    @patch('core.orchestrator.StructuredClient')
    def test_initialization(self, MockStructured, MockClient):
        orch = Orchestrator(self.config_mock, api_key="test")
        self.assertIsNotNone(orch)

if __name__ == '__main__':
    unittest.main()
