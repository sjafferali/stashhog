"""AI client wrapper for OpenAI integration."""
import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class AIClient:
    """Wrapper for OpenAI client with analysis-specific functionality."""
    
    # Cost estimation constants (per million tokens)
    MODEL_COSTS = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50}
    }
    
    # Token estimation constants
    AVG_CHARS_PER_TOKEN = 4
    
    def __init__(self, openai_client: OpenAIClient, model: Optional[str] = None):
        """Initialize AI client.
        
        Args:
            openai_client: OpenAI client instance
            model: Model to use (defaults to client's model)
        """
        self.client = openai_client
        self.model = model or openai_client.model
        
    async def analyze_scene(
        self,
        prompt: str,
        scene_data: Dict[str, Any],
        response_format: Optional[Type[T]] = None,
        temperature: float = 0.3
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
        try:
            if response_format:
                response = await self.client.create_completion(
                    messages=[{"role": "user", "content": final_prompt}],
                    response_format=response_format,
                    temperature=temperature
                )
                return response
            else:
                # For non-structured responses
                response = await self.client.create_completion(
                    messages=[{"role": "user", "content": final_prompt}],
                    temperature=temperature
                )
                return response.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
            
    async def batch_analyze_scenes(
        self,
        prompt_template: str,
        scenes_data: List[Dict[str, Any]],
        response_format: Optional[Type[BaseModel]] = None,
        temperature: float = 0.3
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
        
        try:
            response = await self.client.create_completion(
                messages=[{"role": "user", "content": batch_prompt}],
                temperature=temperature
            )
            
            # Parse the batch response
            return self._parse_batch_response(response.content, scenes_data)
        except Exception as e:
            logger.error(f"Batch analysis error: {e}")
            raise
    
    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None
    ) -> float:
        """Estimate API cost for given token counts.
        
        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            model: Model name (defaults to instance model)
            
        Returns:
            Estimated cost in USD
        """
        model = model or self.model
        
        # Get model costs
        costs = self.MODEL_COSTS.get(model, self.MODEL_COSTS["gpt-4o-mini"])
        
        # Calculate costs
        input_cost = (prompt_tokens / 1_000_000) * costs["input"]
        output_cost = (completion_tokens / 1_000_000) * costs["output"]
        
        return input_cost + output_cost
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Simple estimation based on character count
        return len(text) // self.AVG_CHARS_PER_TOKEN
    
    def build_prompt(
        self,
        template: str,
        scene_data: Dict[str, Any]
    ) -> str:
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
            "studio": scene_data.get("studio", {}).get("name", "") if scene_data.get("studio") else "",
            "performers": ", ".join([p.get("name", "") for p in scene_data.get("performers", [])]),
            "tags": ", ".join([t.get("name", "") for t in scene_data.get("tags", [])]),
            "duration": scene_data.get("duration", 0),
            "resolution": f"{scene_data.get('width', 0)}x{scene_data.get('height', 0)}"
        }
        
        # Fill the template
        try:
            return template.format(**prompt_data)
        except KeyError as e:
            logger.warning(f"Missing key in prompt template: {e}")
            # Return template with safe substitution
            return template
    
    def _create_batch_prompt(
        self,
        template: str,
        scenes_data: List[Dict[str, Any]]
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
        self,
        response: str,
        scenes_data: List[Dict[str, Any]]
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
        return {scene.get("id", f"scene_{idx}"): {} 
                for idx, scene in enumerate(scenes_data)}