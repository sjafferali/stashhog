"""Performer detection module for scene analysis."""

import logging
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .ai_client import AIClient
from .models import DetectionResult
from .prompts import PERFORMER_DETECTION_PROMPT

logger = logging.getLogger(__name__)


class PerformerDetector:
    """Detect performers from file paths and scene metadata."""

    # Common separators in filenames
    SEPARATORS = [
        " and ",
        " & ",
        ", ",
        " - ",
        "_",
        " with ",
        " feat ",
        " ft ",
        " featuring ",
    ]

    # Words to ignore when extracting names
    IGNORE_WORDS = {
        "scene",
        "part",
        "episode",
        "ep",
        "video",
        "clip",
        "raw",
        "bareback",
        "bb",
        "hd",
        "1080p",
        "720p",
        "4k",
        "uhd",
        "mp4",
        "avi",
        "mkv",
        "wmv",
        "mov",
        "fuck",
        "fucks",
        "fucking",
        "sex",
        "anal",
        "oral",
        "blowjob",
        "bj",
        "handjob",
        "hj",
        "cumshot",
        "creampie",
        "compilation",
    }

    def __init__(self) -> None:
        """Initialize performer detector."""
        self._performer_cache: Dict[str, List[DetectionResult]] = {}

    async def detect_from_path(
        self, file_path: str, known_performers: List[Dict[str, str]]
    ) -> List[DetectionResult]:
        """Extract performer names from file path.

        Args:
            file_path: Path to the video file
            known_performers: List of known performer dictionaries with name and aliases

        Returns:
            List of detection results
        """
        path = Path(file_path)
        filename = path.stem
        results = []

        # Extract potential names from filename
        potential_names = self._extract_names_from_string(filename)

        # Also check parent directory name
        if path.parent.name:
            parent_names = self._extract_names_from_string(path.parent.name)
            potential_names.extend(parent_names)

        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for name in potential_names:
            name_lower = name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                unique_names.append(name)

        # Match against known performers
        for name in unique_names:
            match_result = self.find_full_name(name, known_performers)
            if match_result:
                full_name, confidence = match_result
                results.append(
                    DetectionResult(
                        value=full_name,
                        confidence=confidence,
                        source="path",
                        metadata={"extracted_as": name},
                    )
                )
            else:
                # Still include unmatched names with lower confidence
                if self._is_valid_name(name):
                    results.append(
                        DetectionResult(
                            value=name,
                            confidence=0.5,
                            source="path",
                            metadata={"unmatched": True},
                        )
                    )

        return results

    async def detect_with_ai(
        self, scene_data: Dict, ai_client: AIClient
    ) -> List[DetectionResult]:
        """Use AI to detect performers from scene data.

        Args:
            scene_data: Scene information
            ai_client: AI client for analysis

        Returns:
            List of detection results
        """
        try:
            response: Dict = await ai_client.analyze_scene(
                prompt=PERFORMER_DETECTION_PROMPT,
                scene_data=scene_data,
                temperature=0.3,
            )

            results = []
            if isinstance(response, dict) and "performers" in response:
                for performer in response["performers"]:
                    if isinstance(performer, dict):
                        name = performer.get("name", "").strip()
                        confidence = float(performer.get("confidence", 0.7))

                        if name:
                            results.append(
                                DetectionResult(
                                    value=name,
                                    confidence=confidence,
                                    source="ai",
                                    metadata={"model": ai_client.model},
                                )
                            )

            return results

        except Exception as e:
            logger.error(f"AI performer detection error: {e}")
            return []

    def normalize_name(self, name: str, split_names: bool = False) -> str:
        """Normalize performer name for matching.

        Args:
            name: Raw name to normalize
            split_names: Whether to split compound names

        Returns:
            Normalized name
        """
        # Basic normalization
        normalized = name.strip()

        # Remove common suffixes/prefixes
        suffixes = ["xxx", "official", "real", "model", "actor"]
        for suffix in suffixes:
            if normalized.lower().endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()

        # Handle case
        if normalized.isupper() or normalized.islower():
            # Convert to title case
            normalized = normalized.title()

        # Split compound names if requested
        if split_names and " " not in normalized:
            # Try to split CamelCase
            split = re.sub(r"([a-z])([A-Z])", r"\1 \2", normalized)
            if split != normalized:
                normalized = split

        return normalized

    def find_full_name(
        self, partial: str, known_performers: List[Dict[str, str]]
    ) -> Optional[Tuple[str, float]]:
        """Match partial name to full performer name.

        Args:
            partial: Partial or complete name to match
            known_performers: List of known performers with aliases

        Returns:
            Tuple of (full_name, confidence) or None
        """
        partial_lower = partial.lower().strip()

        # Check for exact matches first
        exact_match = self._find_exact_match(partial_lower, known_performers)
        if exact_match:
            return exact_match

        # Check for partial matches
        return self._find_partial_match(partial, partial_lower, known_performers)

    def _find_exact_match(
        self, partial_lower: str, known_performers: List[Dict[str, str]]
    ) -> Optional[Tuple[str, float]]:
        """Find exact name or alias match."""
        for performer in known_performers:
            name = performer.get("name", "")
            name_lower = name.lower()

            # Exact match
            if partial_lower == name_lower:
                return (name, 1.0)

            # Check aliases
            aliases: Union[str, List[str]] = performer.get("aliases", [])
            if isinstance(aliases, str):
                aliases = [a.strip() for a in aliases.split(",") if a.strip()]

            for alias in aliases:
                if partial_lower == alias.lower():
                    return (name, 0.95)

        return None

    def _find_partial_match(
        self, partial: str, partial_lower: str, known_performers: List[Dict[str, str]]
    ) -> Optional[Tuple[str, float]]:
        """Find partial name match with scoring."""
        best_match = None
        best_score = 0.0

        for performer in known_performers:
            name = performer.get("name", "")
            score = self._score_name_match(partial, partial_lower, name)

            if score > best_score and score >= 0.6:
                best_score = score
                best_match = name

        if best_match:
            return (best_match, best_score)

        return None

    def _score_name_match(self, partial: str, partial_lower: str, name: str) -> float:
        """Calculate match score between partial and full name."""
        # Calculate similarity score
        score = self._calculate_similarity(partial, name)

        # Check if partial is a subset
        if partial_lower in name.lower() or name.lower() in partial_lower:
            score = max(score, 0.8)

        # Check first/last name matches
        name_parts = name.split()
        partial_parts = partial.split()

        if name_parts and partial_parts:
            # First name match
            if name_parts[0].lower() == partial_parts[0].lower():
                score = max(score, 0.7)
            # Last name match
            if len(name_parts) > 1 and len(partial_parts) > 1:
                if name_parts[-1].lower() == partial_parts[-1].lower():
                    score = max(score, 0.75)

        return score

    def _extract_names_from_string(self, text: str) -> List[str]:
        """Extract potential performer names from a string.

        Args:
            text: String to extract names from

        Returns:
            List of potential names
        """
        # Clean the text
        text = self._clean_text_for_extraction(text)

        # Try extracting with separators first
        names = self._extract_with_separators(text)

        # If no separators found, try capitalized word extraction
        if not names:
            names = self._extract_capitalized_names(text)

        return names

    def _clean_text_for_extraction(self, text: str) -> str:
        """Clean text before name extraction."""
        text = re.sub(r"\[.*?\]", "", text)  # Remove brackets
        text = re.sub(r"\(.*?\)", "", text)  # Remove parentheses
        text = re.sub(r"\d{3,}", "", text)  # Remove long numbers
        text = re.sub(r"[-_]+", " ", text)  # Replace dashes/underscores with spaces
        return text

    def _extract_with_separators(self, text: str) -> List[str]:
        """Extract names using known separators."""
        names = []
        for separator in self.SEPARATORS:
            if separator in text.lower():
                parts = text.split(separator)
                for part in parts:
                    cleaned = self._clean_name(part)
                    if cleaned:
                        names.append(cleaned)
        return names

    def _extract_capitalized_names(self, text: str) -> List[str]:
        """Extract names based on capitalization patterns."""
        names = []
        words = text.split()
        current_name = []

        for word in words:
            if word and word[0].isupper() and word.lower() not in self.IGNORE_WORDS:
                current_name.append(word)
            elif current_name:
                # End of potential name
                name = " ".join(current_name)
                if self._is_valid_name(name):
                    names.append(name)
                current_name = []

        # Don't forget the last name
        if current_name:
            name = " ".join(current_name)
            if self._is_valid_name(name):
                names.append(name)

        return names

    def _clean_name(self, name: str) -> Optional[str]:
        """Clean and validate a potential name.

        Args:
            name: Raw name string

        Returns:
            Cleaned name or None if invalid
        """
        # Remove extra spaces
        cleaned = " ".join(name.split())

        # Remove common non-name words
        words = cleaned.split()
        filtered_words = [w for w in words if w.lower() not in self.IGNORE_WORDS]

        if not filtered_words:
            return None

        cleaned = " ".join(filtered_words)

        # Basic validation
        if self._is_valid_name(cleaned):
            return cleaned

        return None

    def _is_valid_name(self, name: str) -> bool:
        """Check if a string is likely to be a valid performer name.

        Args:
            name: String to validate

        Returns:
            True if likely a valid name
        """
        if not name or len(name) < 2:
            return False

        # Must contain at least one letter
        if not any(c.isalpha() for c in name):
            return False

        # Shouldn't be all numbers
        if name.isdigit():
            return False

        # Shouldn't be too long
        if len(name) > 50:
            return False

        # Shouldn't contain too many numbers
        digit_count = sum(1 for c in name if c.isdigit())
        if digit_count > len(name) / 2:
            return False

        return True

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity score between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score between 0 and 1
        """
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
