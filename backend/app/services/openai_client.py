"""
OpenAI API client service.
"""

from typing import Any, Optional, cast

import openai
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.completion_create_params import ResponseFormat


class OpenAIClient:
    """Client for interacting with OpenAI API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        base_url: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        timeout: int = 60,
    ):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model to use
            base_url: Custom API endpoint for OpenAI-compatible services
            max_tokens: Maximum tokens per request
            temperature: Temperature for generation
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

        # Initialize OpenAI client with optional custom base URL
        if base_url:
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=float(timeout),
            )
        else:
            self.client = openai.OpenAI(
                api_key=api_key,
                timeout=float(timeout),
            )

    async def test_connection(self) -> bool:
        """Test connection to OpenAI API."""
        try:
            # Try to list models as a connection test
            models = self.client.models.list()
            return len(models.data) > 0
        except Exception:
            return False

    async def generate_completion(
        self,
        prompt: Optional[str] = None,
        messages: Optional[list[ChatCompletionMessageParam]] = None,
        response_format: Optional[dict[str, Any]] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate completion from OpenAI."""
        try:
            # Use provided temperature or default
            temp = temperature if temperature is not None else self.temperature

            # Build messages list
            if messages is None:
                if prompt:
                    messages = [{"role": "user", "content": prompt}]
                else:
                    raise ValueError("Either prompt or messages must be provided")

            # Create completion
            if response_format:
                # Convert dict to ResponseFormat type
                formatted_response_format = cast(ResponseFormat, response_format)
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=temp,
                    response_format=formatted_response_format,
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=temp,
                )

            content = response.choices[0].message.content
            return cast(str, content) if content is not None else ""
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}") from e
