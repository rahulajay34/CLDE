import sys
import os
import unittest
from unittest.mock import MagicMock, ANY

sys.path.append(os.getcwd())

from core.models import OrchestratorConfig, AgentConfig, AuditResult, PedagogueAnalysis, EditorResponse
from core.orchestrator import Orchestrator

class TestCostOptimization(unittest.TestCase):
    def setUp(self):
        # Setup Config
        self.config = OrchestratorConfig(
            creator=AgentConfig(model="test"),
            auditor=AgentConfig(model="test"),
            pedagogue=AgentConfig(model="test"),
            editor=AgentConfig(model="test"),
            sanitizer=AgentConfig(model="test"),
            max_iterations=2, # Run 2 iterations
            human_in_the_loop=False
        )
        self.orchestrator = Orchestrator(config=self.config)
        
        # Mock Clients
        self.orchestrator.client = MagicMock()
        self.orchestrator.structured_client = MagicMock()
        
        # Mock Responses
        self.orchestrator.client.generate_response.return_value = ("Draft Content", 100, 100)
        self.orchestrator.client.calculate_cost.return_value = 0.01

        # Audit Mock
        self.audit_ret = AuditResult(critiques=[], summary="Good", quality_score=85) # < 90 to force loop usage
        
        # Pedagogue Mock
        self.ped_ret = PedagogueAnalysis(points=[], overall_assessment="Good", engagement_score=85)
        
        # Editor Mock
        self.edit_ret = EditorResponse(replacements=[], summary_of_changes="Fixed")

        # Setup side_effects for structured calls
        def structured_side_effect(**kwargs):
            model = kwargs.get('model')
            response_model = kwargs.get('response_model')
            
            if response_model == AuditResult:
                return self.audit_ret, 100, 100, 0.01
            elif response_model == PedagogueAnalysis:
                return self.ped_ret, 100, 100, 0.01
            elif response_model == EditorResponse:
                return self.edit_ret, 100, 100, 0.01
            return None, 0, 0, 0

        self.orchestrator.structured_client.generate_structured.side_effect = structured_side_effect

    def test_run_loop_behavior(self):
        print("Running Loop Verification...")
        # Run the loop
        events = list(self.orchestrator.run_loop("Topic", "Subtopic", transcript="TRANSCRIPT_DATA"))
        
        # 1. Verify Sanitizer REMOVED
        sanitizer_calls = [c for c in self.orchestrator.client.generate_response.call_args_list if "Sanitizer" in str(c)]
        # Actually client.generate_response is used for Creator and Sanitizer. 
        # Creator is called once. Sanitizer should be 0.
        # Let's check agent names in events
        agents_run = set([e.get("agent") for e in events if isinstance(e, dict) and "agent" in e])
        
        print(f"Agents run: {agents_run}")
        self.assertNotIn("Sanitizer", agents_run, "Sanitizer should NOT run")

        # 2. Verify Pedagogue Run Count
        # Should run on Iteration 1, but NOT on Iteration 2
        # Count check logic:
        # call_args_list for generate_structured
        pedagogue_calls = 0
        audit_calls = 0
        
        for call in self.orchestrator.structured_client.generate_structured.call_args_list:
            kwargs = call.kwargs
            if kwargs.get('response_model') == PedagogueAnalysis:
                pedagogue_calls += 1
            if kwargs.get('response_model') == AuditResult:
                audit_calls += 1
                # 3. Verify Caching passed to Auditor
                self.assertEqual(kwargs.get('cache_content'), "TRANSCRIPT_DATA", "Audit must receive cache_content")

        print(f"Pedagogue Calls: {pedagogue_calls}")
        print(f"Audit Calls: {audit_calls}")

        self.assertEqual(pedagogue_calls, 1, "Pedagogue should only run once (Iteration 1)")
        self.assertEqual(audit_calls, 2, "Auditor should run twice (Iteration 1 and 2)")
        
        print("Verification Passed!")

if __name__ == "__main__":
    unittest.main()
