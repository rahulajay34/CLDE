import os
import instructor
import anthropic
from dotenv import load_dotenv
from typing import Type, TypeVar, Optional, Tuple
from pydantic import BaseModel
from core.logger import logger
from core.utils import retry_with_backoff

# Load environment variables
load_dotenv()

T = TypeVar("T", bound=BaseModel)

class StructuredClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found.")
        
        # Initialize the instructor client wrapping Anthropic
        self.client = instructor.from_anthropic(anthropic.Anthropic(api_key=self.api_key))

    @retry_with_backoff(exceptions=(anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError))
    def generate_structured(
        self,
        response_model: Type[T],
        system_prompt: str,
        user_content: str,
        model: str = "claude-3-5-sonnet-20240620",
        max_tokens: int = 4096,
        temperature: float = 0.0
    ) -> Tuple[Optional[T], int, int, float]:
        """
        Generates a structured response based on the provided Pydantic model.
        Returns: (parsed_object, input_tokens, output_tokens, cost)
        """
        try:
            # Instructor's create method returns the parsed object directly
            # To get usage, we might need to access the raw response, but instructor abstraction hides it largely.
            # However, instructor allows `response_model` to be used with standard messages.
            
            # Using the patch, we invoke chat.completions.create
            resp, completion = self.client.chat.completions.create_with_completion(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                response_model=response_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
            )
            
            # Extract usage from the raw completion object if available
            # validation for anthropic usage in instructor might vary, usually it's in usage
            input_tokens = completion.usage.input_tokens
            output_tokens = completion.usage.output_tokens
            
            cost = self.calculate_cost(input_tokens, output_tokens, model)
            
            return resp, input_tokens, output_tokens, cost

        except Exception as e:
            logger.error(f"Structured generation failed: {e}")
            # Depending on severity, we might want to return None or re-raise.
            # For this app, return None letting Orchestrator handle it.
            return None, 0, 0, 0.0

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """
        Calculates cost. Duplicated from client.py or imported. 
         Ideally logic should be centralized.
        """
        # Pricing table (INR Rates) - centralized logic preferred but copying for now strictly as requested in plan (new file).
        # Actually, let's just import it if possible, but circular imports might be an issue.
        # Let's keep it simple and consistent with client.py
        pricing = {
            "claude-sonnet-4-5-20250929": {"input": 300.0, "output": 1500.0},
            "claude-haiku-4-5-20251001": {"input": 100.0, "output": 500.0},
            "claude-opus-4-5-20251101": {"input": 500.0, "output": 2500.0},
            "claude-3-haiku-20240307": {"input": 25.0, "output": 125.0},
            "sonnet": {"input": 300.0, "output": 1500.0},
            "haiku": {"input": 25.0, "output": 125.0},
            "opus": {"input": 500.0, "output": 2500.0},
        }
        
        rates = None
        if model in pricing:
            rates = pricing[model]
        else:
             if "opus" in model: rates = pricing["opus"]
             elif "sonnet" in model: rates = pricing["sonnet"] 
             elif "haiku" in model: rates = pricing["haiku"]
             else: rates = pricing["sonnet"]
        
        cost = (input_tokens / 1_000_000 * rates["input"]) + (output_tokens / 1_000_000 * rates["output"])
        return round(cost, 6)
