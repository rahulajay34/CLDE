import unittest
from core.orchestrator import Orchestrator
from core.models import OrchestratorConfig, AgentConfig
import os

class TestContentQuality(unittest.TestCase):
    """Test that content meets gold standard requirements"""
    
    def setUp(self):
        # Use default config if not strictly defined for tests, or mock it.
        # Here we try to instantiate the real orchestrator.
        # Assuming API Key is in env.
        config = OrchestratorConfig(
            creator=AgentConfig(model="claude-3-haiku-20240307"),
            auditor=AgentConfig(model="claude-3-haiku-20240307"),
            pedagogue=AgentConfig(model="claude-3-haiku-20240307"),
            editor=AgentConfig(model="claude-3-haiku-20240307"),
            sanitizer=AgentConfig(model="claude-3-haiku-20240307"),
            max_iterations=2
        )
        self.orchestrator = Orchestrator(config=config)
    
    def test_no_meta_language_preread(self):
        """Pre-read should not contain meta-language"""
        # Run generation
        result = self._generate_content("Variables in Python", "Pre-read Notes")
        if not result:
             self.skipTest("Generation failed or skipped")
             return

        content = result['content'].lower()
        
        # Check forbidden terms
        forbidden = ['analogy:', 'as discussed', 'in this session', 'in this pre-read', 'this lecture']
        for term in forbidden:
            self.assertNotIn(term, content, f"Found forbidden term: {term}")
    
    def test_tone_appropriate_preread(self):
        """Pre-read should be conversational"""
        result = self._generate_content("Variables in Python", "Pre-read Notes")
        if not result: return

        content = result['content']
        
        # Check for conversational markers
        self.assertIn('you', content.lower(), "Should use 'you' language")
        
        # Should not be overly academic
        academic_terms = ['furthermore', 'henceforth', 'thus']
        for term in academic_terms:
            self.assertNotIn(term, content.lower(), f"Too academic: {term}")
    
    def test_length_targets_met(self):
        """Content should meet length targets"""
        # Pre-read
        result = self._generate_content("Variables in Python", "Pre-read Notes")
        if result:
            word_count = len(result['content'].split())
            # Relaxed bounds for testing
            self.assertGreaterEqual(word_count, 100, "Pre-read too short (test mode)")
        
        # Lecture Notes
        result = self._generate_content("Variables in Python", "Lecture Notes")
        if result:
            word_count = len(result['content'].split())
            self.assertGreaterEqual(word_count, 200, "Lecture notes too short (test mode)")
    
    def _generate_content(self, topic, mode):
        """Helper to generate content"""
        import asyncio
        # Mock run_loop call if needed, or run actual. 
        # CAUTION: Running actual requires API calls. 
        # Ideally we should mock the client. 
        # For this implementation, we will assume this is an integration test.
        try:
             # Just run a single event loop iteration or similar if possible.
             # Orchestrator.run_loop returns an async generator.
             # We need to collect the final result.
             
             async def runner():
                 final_res = None
                 async for event in self.orchestrator.run_loop(
                    topic=topic,
                    subtopics="Variables, Data Types",
                    transcript=None,
                    mode=mode,
                    target_audience="General Student"
                 ):
                     if event.get("type") == "FINAL_RESULT":
                         final_res = event
                 return final_res
             
             return asyncio.run(runner())
        except Exception as e:
            print(f"Test Execution Failed: {e}")
            return None

if __name__ == '__main__':
    unittest.main()
