"""
Tests for OpenAI client service.
"""

from unittest.mock import Mock, patch

import pytest
from openai.types import Model
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from app.services.openai_client import OpenAIClient


@pytest.fixture
def openai_client():
    """Create OpenAI client instance."""
    return OpenAIClient(
        api_key="test-api-key",
        model="gpt-4",
        max_tokens=2000,
        temperature=0.7,
        timeout=60,
    )


@pytest.fixture
def openai_client_with_base_url():
    """Create OpenAI client instance with custom base URL."""
    return OpenAIClient(
        api_key="test-api-key",
        model="gpt-4",
        base_url="https://custom-api.example.com",
        max_tokens=1500,
        temperature=0.5,
        timeout=30,
    )


@pytest.fixture
def mock_chat_completion():
    """Create mock chat completion response."""
    return ChatCompletion(
        id="chatcmpl-123",
        object="chat.completion",
        created=1234567890,
        model="gpt-4",
        choices=[
            Choice(
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content="This is a test response",
                ),
                finish_reason="stop",
            )
        ],
        usage=CompletionUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
    )


@pytest.fixture
def mock_chat_completion_with_no_content():
    """Create mock chat completion response with no content."""
    return ChatCompletion(
        id="chatcmpl-124",
        object="chat.completion",
        created=1234567891,
        model="gpt-4",
        choices=[
            Choice(
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=None,
                ),
                finish_reason="stop",
            )
        ],
        usage=CompletionUsage(
            prompt_tokens=10,
            completion_tokens=0,
            total_tokens=10,
        ),
    )


@pytest.fixture
def mock_models_list():
    """Create mock models list response."""
    return Mock(
        data=[
            Model(
                id="gpt-4",
                object="model",
                created=1234567890,
                owned_by="openai",
            ),
            Model(
                id="gpt-3.5-turbo",
                object="model",
                created=1234567891,
                owned_by="openai",
            ),
        ]
    )


class TestOpenAIClient:
    """Test OpenAI client."""

    def test_init_without_base_url(self, openai_client):
        """Test initialization without custom base URL."""
        assert openai_client.api_key == "test-api-key"
        assert openai_client.model == "gpt-4"
        assert openai_client.max_tokens == 2000
        assert openai_client.temperature == 0.7
        assert openai_client.timeout == 60
        assert openai_client.base_url is None

    def test_init_with_base_url(self, openai_client_with_base_url):
        """Test initialization with custom base URL."""
        assert openai_client_with_base_url.api_key == "test-api-key"
        assert openai_client_with_base_url.model == "gpt-4"
        assert openai_client_with_base_url.base_url == "https://custom-api.example.com"
        assert openai_client_with_base_url.max_tokens == 1500
        assert openai_client_with_base_url.temperature == 0.5
        assert openai_client_with_base_url.timeout == 30

    @pytest.mark.asyncio
    async def test_test_connection_success(self, openai_client, mock_models_list):
        """Test successful connection test."""
        with patch.object(
            openai_client.client.models, "list", return_value=mock_models_list
        ):
            result = await openai_client.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, openai_client):
        """Test failed connection test."""
        with patch.object(
            openai_client.client.models, "list", side_effect=Exception("API error")
        ):
            result = await openai_client.test_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_test_connection_empty_models(self, openai_client):
        """Test connection test with empty models list."""
        with patch.object(
            openai_client.client.models, "list", return_value=Mock(data=[])
        ):
            result = await openai_client.test_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_generate_completion_with_prompt(
        self, openai_client, mock_chat_completion
    ):
        """Test generate completion with prompt."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            return_value=mock_chat_completion,
        ):
            result = await openai_client.generate_completion(prompt="Test prompt")
            assert result == "This is a test response"

            # Verify the call
            openai_client.client.chat.completions.create.assert_called_once_with(
                model="gpt-4",
                messages=[{"role": "user", "content": "Test prompt"}],
                max_tokens=2000,
                temperature=0.7,
            )

    @pytest.mark.asyncio
    async def test_generate_completion_with_messages(
        self, openai_client, mock_chat_completion
    ):
        """Test generate completion with messages."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Test prompt"},
        ]

        with patch.object(
            openai_client.client.chat.completions,
            "create",
            return_value=mock_chat_completion,
        ):
            result = await openai_client.generate_completion(messages=messages)
            assert result == "This is a test response"

            # Verify the call
            openai_client.client.chat.completions.create.assert_called_once_with(
                model="gpt-4",
                messages=messages,
                max_tokens=2000,
                temperature=0.7,
            )

    @pytest.mark.asyncio
    async def test_generate_completion_with_response_format(
        self, openai_client, mock_chat_completion
    ):
        """Test generate completion with response format."""
        response_format = {"type": "json_object"}

        with patch.object(
            openai_client.client.chat.completions,
            "create",
            return_value=mock_chat_completion,
        ):
            result = await openai_client.generate_completion(
                prompt="Test prompt", response_format=response_format
            )
            assert result == "This is a test response"

            # Verify the call
            openai_client.client.chat.completions.create.assert_called_once_with(
                model="gpt-4",
                messages=[{"role": "user", "content": "Test prompt"}],
                max_tokens=2000,
                temperature=0.7,
                response_format=response_format,
            )

    @pytest.mark.asyncio
    async def test_generate_completion_with_custom_temperature(
        self, openai_client, mock_chat_completion
    ):
        """Test generate completion with custom temperature."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            return_value=mock_chat_completion,
        ):
            result = await openai_client.generate_completion(
                prompt="Test prompt", temperature=0.2
            )
            assert result == "This is a test response"

            # Verify the call uses custom temperature
            openai_client.client.chat.completions.create.assert_called_once_with(
                model="gpt-4",
                messages=[{"role": "user", "content": "Test prompt"}],
                max_tokens=2000,
                temperature=0.2,
            )

    @pytest.mark.asyncio
    async def test_generate_completion_no_content(
        self, openai_client, mock_chat_completion_with_no_content
    ):
        """Test generate completion when response has no content."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            return_value=mock_chat_completion_with_no_content,
        ):
            result = await openai_client.generate_completion(prompt="Test prompt")
            assert result == ""

    @pytest.mark.asyncio
    async def test_generate_completion_no_prompt_or_messages(self, openai_client):
        """Test generate completion without prompt or messages."""
        with pytest.raises(
            Exception,
            match="OpenAI API error: Either prompt or messages must be provided",
        ):
            await openai_client.generate_completion()

    @pytest.mark.asyncio
    async def test_generate_completion_api_error(self, openai_client):
        """Test generate completion with API error."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            side_effect=Exception("API connection error"),
        ):
            with pytest.raises(
                Exception, match="OpenAI API error: API connection error"
            ):
                await openai_client.generate_completion(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_generate_completion_with_usage(
        self, openai_client, mock_chat_completion
    ):
        """Test generate completion with usage stats."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            return_value=mock_chat_completion,
        ):
            content, usage = await openai_client.generate_completion_with_usage(
                prompt="Test prompt"
            )

            assert content == "This is a test response"
            assert usage == {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }

    @pytest.mark.asyncio
    async def test_generate_completion_with_usage_messages(
        self, openai_client, mock_chat_completion
    ):
        """Test generate completion with usage using messages."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Test prompt"},
        ]

        with patch.object(
            openai_client.client.chat.completions,
            "create",
            return_value=mock_chat_completion,
        ):
            content, usage = await openai_client.generate_completion_with_usage(
                messages=messages
            )

            assert content == "This is a test response"
            assert usage == {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }

    @pytest.mark.asyncio
    async def test_generate_completion_with_usage_no_usage_data(self, openai_client):
        """Test generate completion with usage when no usage data in response."""
        # Create mock response without usage data
        mock_response = ChatCompletion(
            id="chatcmpl-125",
            object="chat.completion",
            created=1234567892,
            model="gpt-4",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content="Test response without usage",
                    ),
                    finish_reason="stop",
                )
            ],
            usage=None,
        )

        with patch.object(
            openai_client.client.chat.completions, "create", return_value=mock_response
        ):
            content, usage = await openai_client.generate_completion_with_usage(
                prompt="Test prompt"
            )

            assert content == "Test response without usage"
            assert usage == {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

    @pytest.mark.asyncio
    async def test_generate_completion_with_usage_response_format(
        self, openai_client, mock_chat_completion
    ):
        """Test generate completion with usage and response format."""
        response_format = {"type": "json_object"}

        with patch.object(
            openai_client.client.chat.completions,
            "create",
            return_value=mock_chat_completion,
        ):
            content, usage = await openai_client.generate_completion_with_usage(
                prompt="Test prompt", response_format=response_format, temperature=0.3
            )

            assert content == "This is a test response"
            assert usage == {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }

            # Verify the call
            openai_client.client.chat.completions.create.assert_called_once_with(
                model="gpt-4",
                messages=[{"role": "user", "content": "Test prompt"}],
                max_tokens=2000,
                temperature=0.3,
                response_format=response_format,
            )

    @pytest.mark.asyncio
    async def test_generate_completion_with_usage_no_prompt_or_messages(
        self, openai_client
    ):
        """Test generate completion with usage without prompt or messages."""
        with pytest.raises(
            Exception,
            match="OpenAI API error: Either prompt or messages must be provided",
        ):
            await openai_client.generate_completion_with_usage()

    @pytest.mark.asyncio
    async def test_generate_completion_with_usage_api_error(self, openai_client):
        """Test generate completion with usage when API error occurs."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            side_effect=Exception("Rate limit exceeded"),
        ):
            with pytest.raises(
                Exception, match="OpenAI API error: Rate limit exceeded"
            ):
                await openai_client.generate_completion_with_usage(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_multiple_sequential_completions(
        self, openai_client, mock_chat_completion
    ):
        """Test multiple sequential completion calls."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            return_value=mock_chat_completion,
        ):
            # First call
            result1 = await openai_client.generate_completion(prompt="First prompt")
            assert result1 == "This is a test response"

            # Second call
            result2 = await openai_client.generate_completion(prompt="Second prompt")
            assert result2 == "This is a test response"

            # Verify both calls were made
            assert openai_client.client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, openai_client):
        """Test handling of rate limit errors."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            side_effect=Exception("Rate limit exceeded: Too many requests"),
        ):
            with pytest.raises(
                Exception, match="OpenAI API error: Rate limit exceeded"
            ):
                await openai_client.generate_completion(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, openai_client):
        """Test handling of authentication errors."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            side_effect=Exception("Invalid API key provided"),
        ):
            with pytest.raises(Exception, match="OpenAI API error: Invalid API key"):
                await openai_client.generate_completion(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_model_not_found_error(self, openai_client):
        """Test handling when model is not found."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            side_effect=Exception("The model 'gpt-5' does not exist"),
        ):
            with pytest.raises(
                Exception, match="OpenAI API error: The model 'gpt-5' does not exist"
            ):
                await openai_client.generate_completion(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, openai_client):
        """Test handling of timeout errors."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            side_effect=Exception("Request timed out"),
        ):
            with pytest.raises(Exception, match="OpenAI API error: Request timed out"):
                await openai_client.generate_completion(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_network_error_handling(self, openai_client):
        """Test handling of network errors."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            side_effect=Exception("Network error: Unable to connect to OpenAI API"),
        ):
            with pytest.raises(Exception, match="OpenAI API error: Network error"):
                await openai_client.generate_completion(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_invalid_request_error(self, openai_client):
        """Test handling of invalid request errors."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            side_effect=Exception(
                "Invalid request: Temperature must be between 0 and 2"
            ),
        ):
            with pytest.raises(Exception, match="OpenAI API error: Invalid request"):
                await openai_client.generate_completion(
                    prompt="Test prompt", temperature=3.0
                )

    @pytest.mark.asyncio
    async def test_context_length_exceeded_error(self, openai_client):
        """Test handling when context length is exceeded."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            side_effect=Exception("This model's maximum context length is 4096 tokens"),
        ):
            with pytest.raises(
                Exception, match="OpenAI API error: This model's maximum context length"
            ):
                await openai_client.generate_completion(
                    prompt="Very long prompt" * 1000
                )

    @pytest.mark.asyncio
    async def test_service_unavailable_error(self, openai_client):
        """Test handling of service unavailable errors."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            side_effect=Exception("Service temporarily unavailable"),
        ):
            with pytest.raises(
                Exception, match="OpenAI API error: Service temporarily unavailable"
            ):
                await openai_client.generate_completion(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_generate_completion_with_usage_timeout_error(self, openai_client):
        """Test generate_completion_with_usage handles timeout errors."""
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            side_effect=Exception("Request timed out after 60 seconds"),
        ):
            with pytest.raises(Exception, match="OpenAI API error: Request timed out"):
                await openai_client.generate_completion_with_usage(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_empty_response_choices(self, openai_client):
        """Test handling when response has no choices."""
        mock_response = ChatCompletion(
            id="chatcmpl-empty",
            object="chat.completion",
            created=1234567890,
            model="gpt-4",
            choices=[],  # Empty choices
            usage=CompletionUsage(
                prompt_tokens=10,
                completion_tokens=0,
                total_tokens=10,
            ),
        )

        with patch.object(
            openai_client.client.chat.completions, "create", return_value=mock_response
        ):
            # This should raise an IndexError wrapped in an Exception
            with pytest.raises(Exception, match="OpenAI API error:"):
                await openai_client.generate_completion(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_malformed_api_response(self, openai_client):
        """Test handling of malformed API responses."""
        # Mock a response that doesn't have the expected structure
        with patch.object(
            openai_client.client.chat.completions,
            "create",
            return_value=Mock(choices=None),  # Missing choices attribute
        ):
            with pytest.raises(Exception, match="OpenAI API error:"):
                await openai_client.generate_completion(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_concurrent_requests_error_handling(self, openai_client):
        """Test handling of errors in concurrent requests scenario."""
        # Simulate different errors for multiple calls
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First request failed")
            elif call_count == 2:
                raise Exception("Second request failed")
            else:
                return Mock(
                    choices=[Mock(message=Mock(content="Success after retries"))],
                    usage=Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                )

        with patch.object(
            openai_client.client.chat.completions, "create", side_effect=side_effect
        ):
            # First call should fail
            with pytest.raises(
                Exception, match="OpenAI API error: First request failed"
            ):
                await openai_client.generate_completion(prompt="First prompt")

            # Second call should also fail
            with pytest.raises(
                Exception, match="OpenAI API error: Second request failed"
            ):
                await openai_client.generate_completion(prompt="Second prompt")

            # Third call should succeed
            result = await openai_client.generate_completion(prompt="Third prompt")
            assert result == "Success after retries"
