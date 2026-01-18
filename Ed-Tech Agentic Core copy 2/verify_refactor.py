import sys
import os

sys.path.append(os.getcwd())

try:
    from core.models import OrchestratorConfig, AgentConfig
    print("Models imported successfully.")
    
    config = OrchestratorConfig(
        creator=AgentConfig(model="test"),
        auditor=AgentConfig(model="test"),
        pedagogue=AgentConfig(model="test"),
        editor=AgentConfig(model="test"),
        sanitizer=AgentConfig(model="test"),
        max_iterations=1,
        human_in_the_loop=False
    )
    print("Config created successfully.")
    
    # Lazy import orchestrator to see if that's the issue
    from core.orchestrator import Orchestrator
    print("Orchestrator imported successfully.")
    
    orchestrator = Orchestrator(config=config)
    print("Orchestrator initialized.")

except Exception as e:
    print(f"Failed: {e}")
    sys.exit(1)
