"""AI client wrapper for OpenAI integration."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel

from app.config.models import calculate_cost
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AIClient:
    """Wrapper for OpenAI client with analysis-specific functionality."""

    # Token estimation constants
    AVG_CHARS_PER_TOKEN = 4

    def __init__(
        self, openai_client: Optional[OpenAIClient], model: Optional[str] = None
    ):
        """Initialize AI client.

        Args:
            openai_client: OpenAI client instance (can be None)
            model: Model to use (defaults to client's model if available)
        """
        self.client = openai_client
        self.model = model or (openai_client.model if openai_client else "gpt-4o-mini")

    async def analyze_scene(
        self,
        prompt: str,
        scene_data: Dict[str, Any],
        response_format: Optional[Type[T]] = None,
        temperature: float = 0.3,
    ) -> T:
        """Call OpenAI with structured output for scene analysis.

        Args:
            prompt: Prompt template with placeholders
            scene_data: Scene data to fill in prompt
            response_format: Pydantic model for structured output
            temperature: Temperature for generation

        Returns:
            Parsed response in the specified format
        """
        # Build the final prompt
        final_prompt = self.build_prompt(prompt, scene_data)

        # Make the API call
        if not self.client:
            raise ValueError("OpenAI client is not configured")

        try:
            if response_format:
                response = await self.client.generate_completion(
                    messages=[{"role": "user", "content": final_prompt}],
                    response_format={"type": "json_object"},
                    temperature=temperature,
                )
                # Parse the response into the expected type
                if isinstance(response, str):
                    try:
                        return response_format.model_validate_json(response)
                    except Exception:
                        logger.error(
                            f"Failed to parse JSON response: {response[:200]}..."
                        )
                        raise
                return response_format.model_validate(response)
            else:
                # For non-structured responses
                response = await self.client.generate_completion(
                    messages=[{"role": "user", "content": final_prompt}],
                    temperature=temperature,
                )
                return response  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def analyze_scene_with_cost(
        self,
        prompt: str,
        scene_data: Dict[str, Any],
        response_format: Optional[Type[T]] = None,
        temperature: float = 0.3,
    ) -> Tuple[T, Dict[str, Any]]:
        """Call OpenAI with structured output and return cost information.

        Args:
            prompt: Prompt template with placeholders
            scene_data: Scene data to fill in prompt
            response_format: Pydantic model for structured output
            temperature: Temperature for generation

        Returns:
            Tuple of (parsed response, cost information)
        """
        # Build the final prompt
        final_prompt = self.build_prompt(prompt, scene_data)

        # Make the API call with usage tracking
        if not self.client:
            raise ValueError("OpenAI client is not configured")

        try:
            content, usage = await self.client.generate_completion_with_usage(
                messages=[{"role": "user", "content": final_prompt}],
                response_format={"type": "json_object"} if response_format else None,
                temperature=temperature,
            )

            # Calculate cost
            cost_info = self.estimate_cost(
                usage["prompt_tokens"], usage["completion_tokens"], self.model
            )

            # Parse the response into the expected type
            if response_format:
                if isinstance(content, str):
                    try:
                        result = response_format.model_validate_json(content)
                    except Exception:
                        logger.error(
                            f"Failed to parse JSON response: {content[:200]}..."
                        )
                        raise
                else:
                    result = response_format.model_validate(content)
            else:
                result = content  # type: ignore[assignment]

            # Return result with cost info
            return result, {
                "cost": cost_info["total_cost"],
                "usage": usage,
                "model": self.model,
                "cost_breakdown": cost_info,
            }
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def batch_analyze_scenes(
        self,
        prompt_template: str,
        scenes_data: List[Dict[str, Any]],
        response_format: Optional[Type[BaseModel]] = None,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Analyze multiple scenes in a single API call.

        Args:
            prompt_template: Template for batch analysis
            scenes_data: List of scene data dictionaries
            response_format: Expected response format
            temperature: Temperature for generation

        Returns:
            Dictionary mapping scene IDs to analysis results
        """
        # Create a batch prompt
        batch_prompt = self._create_batch_prompt(prompt_template, scenes_data)

        if not self.client:
            raise ValueError("OpenAI client is not configured")

        try:
            response = await self.client.generate_completion(
                messages=[{"role": "user", "content": batch_prompt}],
                temperature=temperature,
            )

            # Parse the batch response
            return self._parse_batch_response(response, scenes_data)
        except Exception as e:
            logger.error(f"Batch analysis error: {e}")
            raise

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
        cached_tokens: int = 0,
    ) -> Dict[str, float]:
        """Estimate API cost for given token counts.

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            model: Model name (defaults to instance model)
            cached_tokens: Number of cached tokens (if applicable)

        Returns:
            Cost breakdown dictionary
        """
        model = model or self.model
        return calculate_cost(model, prompt_tokens, completion_tokens, cached_tokens)

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Simple estimation based on character count
        return len(text) // self.AVG_CHARS_PER_TOKEN

    def build_prompt(self, template: str, scene_data: Dict[str, Any]) -> str:
        """Build prompt from template and scene data.

        Args:
            template: Prompt template with placeholders
            scene_data: Data to fill placeholders

        Returns:
            Filled prompt string
        """
        # Extract relevant fields
        prompt_data = {
            "file_path": scene_data.get("file_path", ""),
            "title": scene_data.get("title", ""),
            "details": scene_data.get("details", ""),
            "studio": (
                scene_data.get("studio", {}).get("name", "")
                if scene_data.get("studio")
                else ""
            ),
            "performers": ", ".join(
                [p.get("name", "") for p in scene_data.get("performers", [])]
            ),
            "tags": (
                scene_data.get("tags", "")
                if isinstance(scene_data.get("tags"), str)
                else ", ".join(
                    [
                        t.get("name", "") if isinstance(t, dict) else str(t)
                        for t in scene_data.get("tags", [])
                    ]
                )
            ),
            "duration": scene_data.get("duration", 0),
            "resolution": f"{scene_data.get('width', 0)}x{scene_data.get('height', 0)}",
        }

        # Add available entities lists if provided
        if "available_studios" in scene_data:
            prompt_data["available_studios"] = "\n".join(
                f"- {studio}" for studio in scene_data["available_studios"]
            )

        if "available_performers" in scene_data:
            # Format performers with their aliases
            performer_lines = []
            for performer in scene_data["available_performers"]:
                if isinstance(performer, dict):
                    name = performer.get("name", "")
                    aliases = performer.get("aliases", [])
                    if aliases:
                        performer_lines.append(
                            f"- {name} (aliases: {', '.join(aliases)})"
                        )
                    else:
                        performer_lines.append(f"- {name}")
                else:
                    performer_lines.append(f"- {performer}")
            prompt_data["available_performers"] = "\n".join(performer_lines)

        if "available_tags" in scene_data:
            prompt_data["available_tags"] = "\n".join(
                f"- {tag}" for tag in scene_data["available_tags"]
            )

        # Fill the template
        try:
            return template.format(**prompt_data)
        except KeyError as e:
            logger.warning(f"Missing key in prompt template: {e}")
            # Return template with safe substitution
            return template

    def _create_batch_prompt(
        self, template: str, scenes_data: List[Dict[str, Any]]
    ) -> str:
        """Create a batch prompt for multiple scenes.

        Args:
            template: Base template for analysis
            scenes_data: List of scene data

        Returns:
            Combined prompt for batch analysis
        """
        batch_parts = []

        # Add instruction for batch processing
        batch_parts.append(
            "Analyze the following scenes and provide results in JSON format. "
            "Return a JSON object with scene IDs as keys."
        )
        batch_parts.append("")

        # Add each scene
        for idx, scene in enumerate(scenes_data):
            batch_parts.append(f"Scene {idx + 1} (ID: {scene.get('id', 'unknown')}):")
            scene_prompt = self.build_prompt(template, scene)
            batch_parts.append(scene_prompt)
            batch_parts.append("")

        return "\n".join(batch_parts)

    def _parse_batch_response(
        self, response: str, scenes_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Parse batch analysis response.

        Args:
            response: Raw response from API
            scenes_data: Original scene data

        Returns:
            Dictionary mapping scene IDs to results
        """
        try:
            # Try to parse as JSON
            results = json.loads(response)
            if isinstance(results, dict):
                return results
        except json.JSONDecodeError:
            logger.warning("Failed to parse batch response as JSON")

        # Fallback: create empty results
        return {
            scene.get("id", f"scene_{idx}"): {} for idx, scene in enumerate(scenes_data)
        }
