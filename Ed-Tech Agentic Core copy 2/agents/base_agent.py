from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass
    
    def format_user_prompt(self, **kwargs) -> str:
        """Override this to format the specific user input for the agent."""
        pass
