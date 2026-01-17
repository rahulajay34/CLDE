import os
import anthropic
from dotenv import load_dotenv
from typing import Optional, Tuple
from core.utils import retry_with_backoff
from core.logger import logger

load_dotenv()

class AnthropicClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            # Logger warning instead of crashing immediately? Or keep crash?
            # Keeping exception as this is critical config.
            raise ValueError("ANTHROPIC_API_KEY not found in environment or passed as argument.")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    @retry_with_backoff(exceptions=(anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError))
    def _make_api_call(self, model, max_tokens, temperature, system_prompt, messages, extra_headers) -> Tuple[str, int, int]:
        """
        Internal method to make the actual API call with retries.
        """
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages,
            extra_headers=extra_headers
        )
        content = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        return content, input_tokens, output_tokens

    def generate_response(
        self,
        system_prompt: str,
        user_content: str,
        model: str = "claude-3-5-sonnet-20240620",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        cache_content: Optional[str] = None
    ) -> Tuple[Optional[str], int, int]:
        """
        Generates a response from Claude, handling prompt caching if 'cache_content' is provided.
        Returns: (content, input_tokens, output_tokens)
        """
        
        # Construct messages
        messages = []
        
        if cache_content:
            # If large context (transcript) triggers caching
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cache_content,
                        "cache_control": {"type": "ephemeral"}
                    },
                    {
                        "type": "text",
                        "text": "\n\n" + user_content
                    }
                ]
            })
        else:
            messages.append({
                "role": "user",
                "content": user_content
            })

        extra_headers = {"anthropic-beta": "prompt-caching-2024-07-31"} if cache_content else None

        try:
            return self._make_api_call(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
                messages=messages,
                extra_headers=extra_headers
            )

        except Exception as e:
            logger.error(f"Error calling Anthropic API after retries: {e}")
            return None, 0, 0

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """
        Calculates cost based on model pricing (approximate).
        Prices per 1M tokens in INR (₹).
        """
        # Pricing table (INR Rates)
        pricing = {
            # New Models
            "claude-sonnet-4-5-20250929": {"input": 300.0, "output": 1500.0},
            "claude-haiku-4-5-20251001": {"input": 100.0, "output": 500.0},
            "claude-opus-4-5-20251101": {"input": 500.0, "output": 2500.0},
            
            # Legacy/Fallback
            "claude-3-haiku-20240307": {"input": 25.0, "output": 125.0},
            
            # Generics (Fallbacks)
            "sonnet": {"input": 300.0, "output": 1500.0},
            "haiku": {"input": 25.0, "output": 125.0},
            "opus": {"input": 500.0, "output": 2500.0},
        }
        
        # Simple lookup
        rates = None
        if model in pricing:
            rates = pricing[model]
        else:
            # Fuzzy match
            if "opus" in model: rates = pricing["opus"]
            elif "sonnet" in model: rates = pricing["sonnet"] 
            elif "haiku" in model: rates = pricing["haiku"]
            else: rates = pricing["sonnet"] # Default
        
        cost = (input_tokens / 1_000_000 * rates["input"]) + (output_tokens / 1_000_000 * rates["output"])
        return round(cost, 6)
