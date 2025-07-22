"""Title generation service for scenes."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from app.models import Scene
from app.services.analysis.ai_client import AIClient
from app.services.analysis.models import ProposedChange

logger = logging.getLogger(__name__)


class TitleGenerator:
    """Generates improved titles for scenes based on metadata."""

    def __init__(self, ai_client: Optional[AIClient] = None):
        """Initialize the title generator.

        Args:
            ai_client: Optional AI client for title generation
        """
        self.ai_client = ai_client

    async def generate_title(
        self, scene: Scene, use_ai: bool = True
    ) -> List[ProposedChange]:
        """Generate an improved title for a scene.

        Args:
            scene: Scene to generate title for
            use_ai: Whether to use AI for title generation

        Returns:
            List of proposed changes (empty if no improvements suggested)
        """
        logger.debug(f"Generating title for scene {scene.id}")
        changes = []

        # Clean up existing title first
        title_value = (
            scene.title
            if isinstance(scene.title, str)
            else str(scene.title) if scene.title else None
        )
        cleaned_title = self._clean_title(title_value)

        if cleaned_title != scene.title:
            changes.append(
                ProposedChange(
                    field="title",
                    action="update",
                    current_value=scene.title,
                    proposed_value=cleaned_title,
                    confidence=0.9,
                    reason="Cleaned up title formatting",
                )
            )

        # Generate AI-based title if enabled
        if use_ai and self.ai_client:
            ai_title = await self._generate_ai_title(scene)
            if ai_title and ai_title != cleaned_title:
                changes.append(
                    ProposedChange(
                        field="title",
                        action="update",
                        current_value=scene.title,
                        proposed_value=ai_title,
                        confidence=0.8,
                        reason="AI-generated improved title",
                    )
                )

        return changes

    def _clean_title(self, title: Optional[str]) -> str:
        """Clean up a title by removing common artifacts.

        Args:
            title: Original title

        Returns:
            Cleaned title
        """
        if not title:
            return ""

        # Remove file extensions
        title = re.sub(
            r"\.(mp4|mkv|avi|mov|wmv|flv|webm)$", "", title, flags=re.IGNORECASE
        )

        # Replace underscores and dots with spaces
        title = title.replace("_", " ").replace(".", " ")

        # Remove resolution indicators
        title = re.sub(
            r"\b(720p|1080p|4k|2160p|480p)\b", "", title, flags=re.IGNORECASE
        )

        # Remove common tags in brackets
        title = re.sub(r"\[(.*?)\]", "", title)
        title = re.sub(r"\((.*?)\)", "", title)

        # Clean up extra spaces
        title = " ".join(title.split())

        # Title case
        if title.islower() or title.isupper():
            title = title.title()

        return title.strip()

    async def _generate_ai_title(self, scene: Scene) -> Optional[str]:
        """Generate an improved title using AI.

        Args:
            scene: Scene to generate title for

        Returns:
            Generated title or None if generation fails
        """
        if not self.ai_client:
            return None

        try:
            context = self._build_scene_context(scene)
            prompt = self._create_title_prompt(context)

            # Generate title
            result: Optional[str] = await self.ai_client.analyze_scene(
                prompt=prompt,
                scene_data={"id": scene.id},
                temperature=0.7,
            )

            if result and isinstance(result, str):
                return self._clean_generated_title(result)

        except Exception as e:
            logger.error(f"Error generating AI title for scene {scene.id}: {e}")

        return None

    def _build_scene_context(self, scene: Scene) -> str:
        """Build context string from scene metadata.

        Args:
            scene: Scene to extract context from

        Returns:
            Formatted context string
        """
        context_parts = []

        # Current title
        if scene.title:
            context_parts.append(f"Current title: {scene.title}")

        # File path
        if scene.path:
            filename = Path(scene.path).stem
            context_parts.append(f"Filename: {filename}")

        # Performers
        if scene.performers:
            performer_names = [p.name for p in scene.performers]
            context_parts.append(f"Performers: {', '.join(performer_names)}")

        # Studio
        if scene.studio:
            context_parts.append(f"Studio: {scene.studio.name}")

        # Tags
        if scene.tags:
            tag_names = [t.name for t in scene.tags][:10]  # Limit to 10 most relevant
            context_parts.append(f"Tags: {', '.join(tag_names)}")

        # Duration
        primary_file = (
            scene.get_primary_file() if hasattr(scene, "get_primary_file") else None
        )
        if primary_file and primary_file.duration:
            minutes = int(primary_file.duration / 60)
            context_parts.append(f"Duration: {minutes} minutes")

        return "\n".join(context_parts)

    def _create_title_prompt(self, context: str) -> str:
        """Create prompt for title generation.

        Args:
            context: Scene context string

        Returns:
            Formatted prompt
        """
        prompt_template = """Based on the following scene information, generate an improved, descriptive title.
The title should be concise, professional, and accurately describe the content.

{context}

Generate a single improved title (no quotes, no explanation):"""

        return prompt_template.format(context=context)

    def _clean_generated_title(self, title: str) -> str:
        """Clean up AI-generated title.

        Args:
            title: Raw generated title

        Returns:
            Cleaned title
        """
        # Clean up the generated title
        generated_title = title.strip()
        # Remove quotes if present
        generated_title = generated_title.strip("\"'")
        # Ensure it's not too long
        if len(generated_title) > 200:
            generated_title = generated_title[:197] + "..."

        return generated_title

    async def process_batch(
        self, scenes: List[Scene], use_ai: bool = True
    ) -> Dict[str, List[ProposedChange]]:
        """Process a batch of scenes for title generation.

        Args:
            scenes: List of scenes to process
            use_ai: Whether to use AI for generation

        Returns:
            Dictionary mapping scene IDs to proposed changes
        """
        results = {}

        for scene in scenes:
            try:
                changes = await self.generate_title(scene, use_ai=use_ai)
                if changes:
                    results[str(scene.id)] = changes
            except Exception as e:
                logger.error(f"Error processing scene {scene.id}: {e}")

        return results
