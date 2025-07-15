"""Details/description generation module for scene analysis."""

import logging
import re
from html.parser import HTMLParser
from typing import Dict, List

from .ai_client import AIClient
from .models import DetectionResult
from .prompts import DESCRIPTION_GENERATION_PROMPT

logger = logging.getLogger(__name__)


class HTMLStripper(HTMLParser):
    """Helper class to strip HTML tags from text."""

    def __init__(self) -> None:
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text: List[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def get_data(self) -> str:
        return "".join(self.text)


class DetailsGenerator:
    """Generate and enhance scene descriptions."""

    # Maximum description length
    MAX_DESCRIPTION_LENGTH = 500

    # Minimum description length to consider it substantial
    MIN_SUBSTANTIAL_LENGTH = 50

    def __init__(self) -> None:
        """Initialize details generator."""
        self._description_cache: Dict[str, DetectionResult] = {}

    async def generate_description(
        self, scene_data: Dict, ai_client: AIClient
    ) -> DetectionResult:
        """Generate a new scene description using AI.

        Args:
            scene_data: Scene information
            ai_client: AI client for generation

        Returns:
            Detection result with generated description
        """
        try:
            response: Dict = await ai_client.analyze_scene(
                prompt=DESCRIPTION_GENERATION_PROMPT,
                scene_data=scene_data,
                temperature=0.5,  # Slightly higher for more creative descriptions
            )

            if isinstance(response, dict):
                description = response.get("description", "").strip()
                confidence = float(response.get("confidence", 0.8))

                if description:
                    # Clean and validate the description
                    cleaned = self._clean_description(description)

                    return DetectionResult(
                        value=cleaned,
                        confidence=confidence,
                        source="ai",
                        metadata={
                            "model": ai_client.model,
                            "original_length": len(description),
                            "cleaned_length": len(cleaned),
                        },
                    )

            # Fallback if generation fails
            return DetectionResult(
                value="",
                confidence=0.0,
                source="ai",
                metadata={"error": "Failed to generate description"},
            )

        except Exception as e:
            logger.error(f"Description generation error: {e}")
            return DetectionResult(
                value="", confidence=0.0, source="ai", metadata={"error": str(e)}
            )

    def clean_html(self, text: str) -> str:
        """Remove HTML tags from text.

        Args:
            text: Text potentially containing HTML

        Returns:
            Clean text without HTML tags
        """
        if not text:
            return ""

        # Use HTMLParser to strip tags
        stripper = HTMLStripper()
        stripper.feed(text)
        cleaned = stripper.get_data()

        # Also clean up common HTML entities
        cleaned = cleaned.replace("&amp;", "&")
        cleaned = cleaned.replace("&lt;", "<")
        cleaned = cleaned.replace("&gt;", ">")
        cleaned = cleaned.replace("&quot;", '"')
        cleaned = cleaned.replace("&#39;", "'")
        cleaned = cleaned.replace("&nbsp;", " ")

        # Clean up whitespace
        cleaned = " ".join(cleaned.split())

        return cleaned

    async def enhance_description(
        self, current: str, scene_data: Dict, ai_client: AIClient
    ) -> DetectionResult:
        """Enhance an existing description.

        Args:
            current: Current description
            scene_data: Scene information
            ai_client: AI client for enhancement

        Returns:
            Detection result with enhanced description
        """
        # Clean current description
        current_clean = self.clean_html(current).strip()

        # Check if current description is substantial
        if len(current_clean) < self.MIN_SUBSTANTIAL_LENGTH:
            # Generate new description instead
            return await self.generate_description(scene_data, ai_client)

        # Add current description to scene data for context
        scene_data["details"] = current_clean

        # Generate enhanced version
        result = await self.generate_description(scene_data, ai_client)

        # If the new description is very similar, keep the original
        if (
            result.value
            and self._calculate_similarity(current_clean, result.value) > 0.8
        ):
            result.value = current_clean
            result.metadata["kept_original"] = True

        return result

    def _clean_description(self, description: str) -> str:
        """Clean and validate a description.

        Args:
            description: Raw description text

        Returns:
            Cleaned description
        """
        # Remove any HTML
        cleaned = self.clean_html(description)

        # Remove excessive whitespace
        cleaned = " ".join(cleaned.split())

        # Remove any URLs (privacy/security)
        cleaned = re.sub(r"https?://\S+", "", cleaned)

        # Remove email addresses
        cleaned = re.sub(r"\S+@\S+", "", cleaned)

        # Ensure proper sentence endings
        if cleaned and not cleaned[-1] in ".!?":
            cleaned += "."

        # Truncate if too long
        if len(cleaned) > self.MAX_DESCRIPTION_LENGTH:
            # Try to cut at sentence boundary
            sentences = cleaned.split(". ")
            truncated = []
            current_length = 0

            for sentence in sentences:
                sentence_length = len(sentence) + 2  # +2 for ". "
                if current_length + sentence_length <= self.MAX_DESCRIPTION_LENGTH:
                    truncated.append(sentence)
                    current_length += sentence_length
                else:
                    break

            cleaned = ". ".join(truncated)
            if cleaned and not cleaned.endswith("."):
                cleaned += "."

        return cleaned

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0.0

        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def create_basic_description(self, scene_data: Dict) -> DetectionResult:
        """Create a basic description from scene metadata.

        Args:
            scene_data: Scene information

        Returns:
            Detection result with basic description
        """
        parts: List[str] = []

        # Add studio if available
        self._add_studio_to_parts(scene_data, parts)

        # Add performers if available
        self._add_performers_to_parts(scene_data, parts)

        # Add duration if substantial
        self._add_duration_to_parts(scene_data, parts)

        # Combine parts
        if parts:
            description = " ".join(parts) + "."
            return DetectionResult(
                value=description,
                confidence=0.5,
                source="metadata",
                metadata={"type": "basic"},
            )

        return DetectionResult(
            value="", confidence=0.0, source="metadata", metadata={"type": "empty"}
        )

    def _add_studio_to_parts(self, scene_data: Dict, parts: List[str]) -> None:
        """Add studio information to description parts."""
        studio = scene_data.get("studio", {})
        if isinstance(studio, dict) and studio.get("name"):
            parts.append(f"A {studio['name']} production")

    def _add_performers_to_parts(self, scene_data: Dict, parts: List[str]) -> None:
        """Add performer information to description parts."""
        performers = scene_data.get("performers", [])
        if not performers:
            return

        names = self._extract_performer_names(performers)
        if names:
            performer_text = self._format_performer_list(names)
            parts.append(performer_text)

    def _extract_performer_names(self, performers: List) -> List[str]:
        """Extract performer names from various formats."""
        names: List[str] = []
        for p in performers:
            if isinstance(p, dict) and p.get("name"):
                names.append(p["name"])
            elif isinstance(p, str):
                names.append(p)
        return names

    def _format_performer_list(self, names: List[str]) -> str:
        """Format a list of performer names."""
        if len(names) == 1:
            return f"featuring {names[0]}"
        elif len(names) == 2:
            return f"featuring {names[0]} and {names[1]}"
        else:
            return f"featuring {', '.join(names[:-1])}, and {names[-1]}"

    def _add_duration_to_parts(self, scene_data: Dict, parts: List[str]) -> None:
        """Add duration information to description parts."""
        duration = scene_data.get("duration", 0)
        if duration > 0:
            minutes = duration // 60
            if minutes > 0:
                parts.append(f"({minutes} minutes)")
