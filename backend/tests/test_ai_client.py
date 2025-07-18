"""
Tests for AI client wrapper module.

This module tests the OpenAI integration wrapper including prompt building,
response parsing, cost calculation, and error handling.
"""

from typing import Dict
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

from app.services.analysis.ai_client import AIClient
from app.services.openai_client import OpenAIClient


class SampleResponse(BaseModel):
    """Sample response model for testing."""

    result: str
    confidence: float
    metadata: Dict[str, str] = {}


class TestAIClientInit:
    """Test cases for AIClient initialization."""

    def test_init_with_client(self):
        """Test initialization with OpenAI client."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"

        ai_client = AIClient(openai_client)

        assert ai_client.client == openai_client
        assert ai_client.model == "gpt-4"

    def test_init_with_custom_model(self):
        """Test initialization with custom model override."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"

        ai_client = AIClient(openai_client, model="gpt-4o-mini")

        assert ai_client.client == openai_client
        assert ai_client.model == "gpt-4o-mini"

    def test_init_without_client(self):
        """Test initialization without OpenAI client."""
        ai_client = AIClient(None)

        assert ai_client.client is None
        assert ai_client.model == "gpt-4o-mini"  # Default model


class TestPromptBuilding:
    """Test cases for prompt building functionality."""

    def test_build_prompt_basic(self):
        """Test basic prompt building with scene data."""
        ai_client = AIClient(None)

        template = "Analyze scene: {title} at {file_path}"
        scene_data = {"title": "Test Scene", "file_path": "/videos/test.mp4"}

        result = ai_client.build_prompt(template, scene_data)

        assert result == "Analyze scene: Test Scene at /videos/test.mp4"

    def test_build_prompt_with_nested_data(self):
        """Test prompt building with nested scene data."""
        ai_client = AIClient(None)

        template = "Studio: {studio}, Performers: {performers}"
        scene_data = {
            "studio": {"name": "Test Studio"},
            "performers": [{"name": "Actor 1"}, {"name": "Actor 2"}],
        }

        result = ai_client.build_prompt(template, scene_data)

        assert result == "Studio: Test Studio, Performers: Actor 1, Actor 2"

    def test_build_prompt_with_tags(self):
        """Test prompt building with various tag formats."""
        ai_client = AIClient(None)

        template = "Tags: {tags}"

        # Test with string tags
        scene_data = {"tags": "tag1, tag2, tag3"}
        result = ai_client.build_prompt(template, scene_data)
        assert result == "Tags: tag1, tag2, tag3"

        # Test with dict tags
        scene_data = {"tags": [{"name": "tag1"}, {"name": "tag2"}]}
        result = ai_client.build_prompt(template, scene_data)
        assert result == "Tags: tag1, tag2"

        # Test with string list tags
        scene_data = {"tags": ["tag1", "tag2", "tag3"]}
        result = ai_client.build_prompt(template, scene_data)
        assert result == "Tags: tag1, tag2, tag3"

    def test_build_prompt_with_available_entities(self):
        """Test prompt building with available entities lists."""
        ai_client = AIClient(None)

        template = "Available studios:\n{available_studios}\n\nAvailable performers:\n{available_performers}"
        scene_data = {
            "available_studios": ["Studio A", "Studio B"],
            "available_performers": [
                {"name": "John Doe", "aliases": ["JD", "Johnny"]},
                {"name": "Jane Smith", "aliases": []},
            ],
        }

        result = ai_client.build_prompt(template, scene_data)

        expected = (
            "Available studios:\n"
            "- Studio A\n"
            "- Studio B\n\n"
            "Available performers:\n"
            "- John Doe (aliases: JD, Johnny)\n"
            "- Jane Smith"
        )
        assert result == expected

    def test_build_prompt_missing_key(self):
        """Test prompt building with missing data keys."""
        ai_client = AIClient(None)

        template = "Title: {title}, Missing: {missing_field}"
        scene_data = {"title": "Test"}

        # Should return template as-is when key is missing
        result = ai_client.build_prompt(template, scene_data)
        assert result == template


class TestSceneAnalysis:
    """Test cases for scene analysis functionality."""

    @pytest.mark.asyncio
    async def test_analyze_scene_structured(self):
        """Test structured scene analysis with response format."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion = AsyncMock(
            return_value='{"result": "test", "confidence": 0.9}'
        )

        ai_client = AIClient(openai_client)

        result = await ai_client.analyze_scene(
            prompt="Analyze {title}",
            scene_data={"title": "Test Scene"},
            response_format=SampleResponse,
            temperature=0.5,
        )

        assert isinstance(result, SampleResponse)
        assert result.result == "test"
        assert result.confidence == 0.9

        # Verify API call
        openai_client.generate_completion.assert_called_once()
        args = openai_client.generate_completion.call_args
        assert args[1]["temperature"] == 0.5
        assert args[1]["response_format"]["type"] == "json_object"

    @pytest.mark.asyncio
    async def test_analyze_scene_unstructured(self):
        """Test unstructured scene analysis without response format."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion = AsyncMock(
            return_value="This is a test response"
        )

        ai_client = AIClient(openai_client)

        result = await ai_client.analyze_scene(
            prompt="Analyze {title}",
            scene_data={"title": "Test Scene"},
            temperature=0.7,
        )

        assert result == "This is a test response"

    @pytest.mark.asyncio
    async def test_analyze_scene_no_client(self):
        """Test scene analysis without configured client."""
        ai_client = AIClient(None)

        with pytest.raises(ValueError, match="OpenAI client is not configured"):
            await ai_client.analyze_scene(prompt="Test", scene_data={})

    @pytest.mark.asyncio
    async def test_analyze_scene_parse_error(self):
        """Test scene analysis with JSON parsing error."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion = AsyncMock(
            return_value="Invalid JSON response"
        )

        ai_client = AIClient(openai_client)

        with pytest.raises(Exception):
            await ai_client.analyze_scene(
                prompt="Test", scene_data={}, response_format=SampleResponse
            )


class TestSceneAnalysisWithCost:
    """Test cases for scene analysis with cost tracking."""

    @pytest.mark.asyncio
    async def test_analyze_scene_with_cost_success(self):
        """Test successful scene analysis with cost information."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.generate_completion_with_usage = AsyncMock(
            return_value=(
                '{"result": "analyzed", "confidence": 0.85}',
                {"prompt_tokens": 100, "completion_tokens": 50},
            )
        )

        ai_client = AIClient(openai_client, model="gpt-4o-mini")

        result, cost_info = await ai_client.analyze_scene_with_cost(
            prompt="Analyze {title}",
            scene_data={"title": "Test"},
            response_format=SampleResponse,
        )

        # Check result
        assert isinstance(result, SampleResponse)
        assert result.result == "analyzed"
        assert result.confidence == 0.85

        # Check cost info
        assert "cost" in cost_info
        assert cost_info["usage"]["prompt_tokens"] == 100
        assert cost_info["usage"]["completion_tokens"] == 50
        assert cost_info["model"] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_analyze_scene_with_cost_no_format(self):
        """Test scene analysis with cost tracking but no response format."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion_with_usage = AsyncMock(
            return_value=(
                "Plain text response",
                {"prompt_tokens": 50, "completion_tokens": 25},
            )
        )

        ai_client = AIClient(openai_client)

        result, cost_info = await ai_client.analyze_scene_with_cost(
            prompt="Test prompt", scene_data={}
        )

        assert result == "Plain text response"
        assert cost_info["usage"]["prompt_tokens"] == 50


class TestBatchAnalysis:
    """Test cases for batch scene analysis."""

    def test_create_batch_prompt(self):
        """Test batch prompt creation."""
        ai_client = AIClient(None)

        template = "Analyze scene {title}"
        scenes = [{"id": "1", "title": "Scene 1"}, {"id": "2", "title": "Scene 2"}]

        batch_prompt = ai_client._create_batch_prompt(template, scenes)

        assert "Scene 1 (ID: 1):" in batch_prompt
        assert "Analyze scene Scene 1" in batch_prompt
        assert "Scene 2 (ID: 2):" in batch_prompt
        assert "Analyze scene Scene 2" in batch_prompt

    def test_parse_batch_response_valid_json(self):
        """Test parsing valid JSON batch response."""
        ai_client = AIClient(None)

        response = '{"scene1": {"result": "good"}, "scene2": {"result": "bad"}}'
        scenes = [{"id": "scene1"}, {"id": "scene2"}]

        result = ai_client._parse_batch_response(response, scenes)

        assert result["scene1"]["result"] == "good"
        assert result["scene2"]["result"] == "bad"

    def test_parse_batch_response_invalid_json(self):
        """Test parsing invalid batch response."""
        ai_client = AIClient(None)

        response = "Invalid JSON response"
        scenes = [{"id": "1"}, {"id": "2"}]

        result = ai_client._parse_batch_response(response, scenes)

        # Should return empty results for each scene
        assert result["1"] == {}
        assert result["2"] == {}

    @pytest.mark.asyncio
    async def test_batch_analyze_scenes(self):
        """Test batch scene analysis."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion = AsyncMock(
            return_value='{"scene1": {"tags": ["action"]}, "scene2": {"tags": ["drama"]}}'
        )

        ai_client = AIClient(openai_client)

        scenes = [
            {"id": "scene1", "title": "Action Scene"},
            {"id": "scene2", "title": "Drama Scene"},
        ]

        result = await ai_client.batch_analyze_scenes(
            prompt_template="Analyze {title}", scenes_data=scenes
        )

        assert result["scene1"]["tags"] == ["action"]
        assert result["scene2"]["tags"] == ["drama"]


class TestCostEstimation:
    """Test cases for cost estimation functionality."""

    def test_estimate_cost(self):
        """Test cost estimation for different models."""
        ai_client = AIClient(None, model="gpt-4o-mini")

        # Test basic cost calculation
        cost_info = ai_client.estimate_cost(prompt_tokens=1000, completion_tokens=500)

        assert "total_cost" in cost_info
        assert cost_info["total_cost"] > 0

    def test_estimate_cost_with_cache(self):
        """Test cost estimation with cached tokens."""
        ai_client = AIClient(None, model="gpt-4o-mini")

        cost_info = ai_client.estimate_cost(
            prompt_tokens=1000, completion_tokens=500, cached_tokens=200
        )

        assert "total_cost" in cost_info

    def test_estimate_tokens(self):
        """Test token estimation from text."""
        ai_client = AIClient(None)

        # Test with known text length
        text = "a" * 400  # 400 characters
        tokens = ai_client.estimate_tokens(text)

        # Should be approximately 100 tokens (4 chars per token)
        assert tokens == 100


class TestErrorHandling:
    """Test cases for error handling."""

    @pytest.mark.asyncio
    async def test_analyze_scene_api_error(self):
        """Test handling of API errors during analysis."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion = AsyncMock(
            side_effect=Exception("API Error")
        )

        ai_client = AIClient(openai_client)

        with pytest.raises(Exception, match="API Error"):
            await ai_client.analyze_scene(prompt="Test", scene_data={})

    @pytest.mark.asyncio
    async def test_batch_analyze_error_handling(self):
        """Test error handling in batch analysis."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion = AsyncMock(
            side_effect=Exception("Batch API Error")
        )

        ai_client = AIClient(openai_client)

        with pytest.raises(Exception, match="Batch API Error"):
            await ai_client.batch_analyze_scenes(
                prompt_template="Test", scenes_data=[{"id": "1"}]
            )


class TestRetryAndTimeoutBehavior:
    """Test cases for retry logic and timeout handling."""

    @pytest.mark.asyncio
    async def test_multiple_api_failures(self):
        """Test handling of multiple consecutive API failures."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"

        # Simulate multiple failures
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"API Error {call_count}")
            return '{"result": "success"}'

        openai_client.generate_completion = AsyncMock(side_effect=side_effect)

        ai_client = AIClient(openai_client)

        # First attempt should fail
        with pytest.raises(Exception, match="API Error 1"):
            await ai_client.analyze_scene(
                prompt="Test", scene_data={}, response_format=SampleResponse
            )

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test handling of timeout scenarios."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.timeout = 5  # 5 second timeout
        openai_client.generate_completion = AsyncMock(
            side_effect=TimeoutError("Request timed out")
        )

        ai_client = AIClient(openai_client)

        with pytest.raises(TimeoutError):
            await ai_client.analyze_scene(prompt="Test", scene_data={})

    @pytest.mark.asyncio
    async def test_partial_response_handling(self):
        """Test handling of partial or incomplete responses."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"

        # Simulate incomplete JSON response
        openai_client.generate_completion = AsyncMock(
            return_value='{"result": "test", "confidence":'  # Incomplete JSON
        )

        ai_client = AIClient(openai_client)

        with pytest.raises(Exception):
            await ai_client.analyze_scene(
                prompt="Test", scene_data={}, response_format=SampleResponse
            )

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Test handling of rate limit errors."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )

        ai_client = AIClient(openai_client)

        with pytest.raises(Exception, match="Rate limit exceeded"):
            await ai_client.analyze_scene(prompt="Test", scene_data={})

    @pytest.mark.asyncio
    async def test_invalid_api_key_error(self):
        """Test handling of invalid API key errors."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion = AsyncMock(
            side_effect=Exception("Invalid API key provided")
        )

        ai_client = AIClient(openai_client)

        with pytest.raises(Exception, match="Invalid API key"):
            await ai_client.analyze_scene(prompt="Test", scene_data={})

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of network connectivity errors."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion = AsyncMock(
            side_effect=ConnectionError("Network is unreachable")
        )

        ai_client = AIClient(openai_client)

        with pytest.raises(ConnectionError):
            await ai_client.analyze_scene(prompt="Test", scene_data={})

    @pytest.mark.asyncio
    async def test_cost_tracking_with_errors(self):
        """Test cost tracking when errors occur."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion_with_usage = AsyncMock(
            side_effect=Exception("API Error during cost tracking")
        )

        ai_client = AIClient(openai_client)

        with pytest.raises(Exception, match="API Error during cost tracking"):
            await ai_client.analyze_scene_with_cost(prompt="Test", scene_data={})

    @pytest.mark.asyncio
    async def test_malformed_response_format(self):
        """Test handling of responses that don't match expected format."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"

        # Response with wrong structure
        openai_client.generate_completion = AsyncMock(
            return_value='{"wrong_field": "value", "another_field": 123}'
        )

        ai_client = AIClient(openai_client)

        with pytest.raises(Exception):  # Pydantic validation error
            await ai_client.analyze_scene(
                prompt="Test", scene_data={}, response_format=SampleResponse
            )


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_build_prompt_empty_data(self):
        """Test prompt building with empty scene data."""
        ai_client = AIClient(None)

        template = "Title: {title}, Path: {file_path}"
        scene_data = {}

        result = ai_client.build_prompt(template, scene_data)

        assert result == "Title: , Path: "

    def test_build_prompt_resolution_formatting(self):
        """Test resolution formatting in prompts."""
        ai_client = AIClient(None)

        template = "Resolution: {resolution}"

        # With width and height
        scene_data = {"width": 1920, "height": 1080}
        result = ai_client.build_prompt(template, scene_data)
        assert result == "Resolution: 1920x1080"

        # Without dimensions
        scene_data = {}
        result = ai_client.build_prompt(template, scene_data)
        assert result == "Resolution: 0x0"

    @pytest.mark.asyncio
    async def test_analyze_scene_dict_response(self):
        """Test handling of dict response from API."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4"
        openai_client.generate_completion = AsyncMock(
            return_value={"result": "test", "confidence": 0.9}
        )

        ai_client = AIClient(openai_client)

        result = await ai_client.analyze_scene(
            prompt="Test", scene_data={}, response_format=SampleResponse
        )

        assert isinstance(result, SampleResponse)
        assert result.result == "test"
