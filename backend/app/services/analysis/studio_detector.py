"""Studio detection module for scene analysis."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from .ai_client import AIClient
from .models import DetectionResult
from .prompts import STUDIO_DETECTION_PROMPT

logger = logging.getLogger(__name__)


class StudioDetector:
    """Detect studios from file paths and scene metadata."""

    def __init__(self) -> None:
        """Initialize studio detector with patterns."""
        self.patterns: Dict[str, re.Pattern] = self._load_patterns()
        self._studio_cache: Dict[str, Optional[DetectionResult]] = {}

    def _load_patterns(self) -> Dict[str, re.Pattern]:
        """Load regex patterns for studio detection.

        Returns:
            Dictionary of studio name to compiled regex pattern
        """
        # Common studio patterns from legacy script
        patterns = {
            # Major studios with specific patterns
            "Sean Cody": re.compile(r"sean[\s_-]?cody|sc\d{4}", re.IGNORECASE),
            "Men.com": re.compile(r"men\.com|men\s+\-|^\s*men\s+", re.IGNORECASE),
            "Lucas Entertainment": re.compile(
                r"lucas[\s_-]?entertainment|lucas[\s_-]?men", re.IGNORECASE
            ),
            "Corbin Fisher": re.compile(
                r"corbin[\s_-]?fisher|cf[\s_-]?\d+", re.IGNORECASE
            ),
            "Bel Ami": re.compile(r"bel[\s_-]?ami|belami", re.IGNORECASE),
            "Falcon Studios": re.compile(r"falcon[\s_-]?studios?", re.IGNORECASE),
            "Raging Stallion": re.compile(
                r"raging[\s_-]?stallion|rs[\s_-]?\d+", re.IGNORECASE
            ),
            "Hot House": re.compile(r"hot[\s_-]?house", re.IGNORECASE),
            "Naked Sword": re.compile(r"naked[\s_-]?sword|nakedsword", re.IGNORECASE),
            "Treasure Island Media": re.compile(
                r"treasure[\s_-]?island|tim[\s_-]?\d+", re.IGNORECASE
            ),
            "Raw Fuck Club": re.compile(
                r"raw[\s_-]?fuck[\s_-]?club|rfc", re.IGNORECASE
            ),
            "Sketchy Sex": re.compile(r"sketchy[\s_-]?sex", re.IGNORECASE),
            "Breed Me Raw": re.compile(r"breed[\s_-]?me[\s_-]?raw", re.IGNORECASE),
            "Bareback That Hole": re.compile(
                r"bareback[\s_-]?that[\s_-]?hole|bbth", re.IGNORECASE
            ),
            "Tim Fuck": re.compile(r"tim[\s_-]?fuck", re.IGNORECASE),
            "Machofucker": re.compile(r"macho[\s_-]?fucker", re.IGNORECASE),
            "Citebeur": re.compile(r"cite[\s_-]?beur", re.IGNORECASE),
            "Cazzo Film": re.compile(r"cazzo[\s_-]?film", re.IGNORECASE),
            "Dark Alley Media": re.compile(r"dark[\s_-]?alley", re.IGNORECASE),
            "Dick Wadd": re.compile(r"dick[\s_-]?wadd", re.IGNORECASE),
            # OnlyFans and fan sites
            "OnlyFans": re.compile(r"onlyfans|only[\s_-]?fans", re.IGNORECASE),
            "JustForFans": re.compile(
                r"justforfans|just[\s_-]?for[\s_-]?fans|jff", re.IGNORECASE
            ),
            "FanCentro": re.compile(r"fancentro|fan[\s_-]?centro", re.IGNORECASE),
            # Amateur/Independent
            "Amateur": re.compile(r"amateur|homemade|self[\s_-]?made", re.IGNORECASE),
            "Independent": re.compile(r"independent|indie", re.IGNORECASE),
        }

        return patterns

    async def detect_from_path(
        self, file_path: str, known_studios: List[str]
    ) -> Optional[DetectionResult]:
        """Detect studio from file path using patterns.

        Args:
            file_path: Path to the video file
            known_studios: List of studios already in database

        Returns:
            Detection result with studio name and confidence
        """
        path = Path(file_path)
        path_parts = path.parts
        filename = path.stem

        # Check against known patterns
        for studio, pattern in self.patterns.items():
            # Check filename
            if pattern.search(filename):
                confidence = 0.9 if studio in known_studios else 0.8
                return DetectionResult(
                    value=studio,
                    confidence=confidence,
                    source="pattern",
                    metadata={"pattern": pattern.pattern},
                )

            # Check directory names
            for part in path_parts[:-1]:  # Exclude filename
                if pattern.search(part):
                    confidence = 0.85 if studio in known_studios else 0.75
                    return DetectionResult(
                        value=studio,
                        confidence=confidence,
                        source="pattern",
                        metadata={
                            "pattern": pattern.pattern,
                            "matched_in": "directory",
                        },
                    )

        # Check for exact studio name matches in path
        path_lower = file_path.lower()
        for studio in known_studios:
            studio_lower = studio.lower()
            if studio_lower in path_lower:
                # Calculate confidence based on match quality
                if f"/{studio_lower}/" in path_lower:  # Exact directory match
                    confidence = 0.95
                elif studio_lower in filename.lower():  # In filename
                    confidence = 0.85
                else:  # Somewhere in path
                    confidence = 0.75

                return DetectionResult(
                    value=studio,
                    confidence=confidence,
                    source="path",
                    metadata={"match_type": "exact"},
                )

        return None

    async def detect_with_ai(
        self, scene_data: Dict, ai_client: AIClient
    ) -> Optional[DetectionResult]:
        """Use AI to detect studio from scene data.

        Args:
            scene_data: Scene information including path, title, etc.
            ai_client: AI client for analysis

        Returns:
            Detection result with studio name and confidence
        """
        try:
            # Use AI to analyze the scene
            response: Dict = await ai_client.analyze_scene(
                prompt=STUDIO_DETECTION_PROMPT, scene_data=scene_data, temperature=0.3
            )

            # Parse response
            if isinstance(response, dict):
                studio = response.get("studio", "").strip()
                confidence = float(response.get("confidence", 0.5))

                if studio and studio.lower() != "unknown":
                    return DetectionResult(
                        value=studio,
                        confidence=confidence,
                        source="ai",
                        metadata={"model": ai_client.model},
                    )

        except Exception as e:
            logger.error(f"AI studio detection error: {e}")

        return None

    async def detect(
        self,
        scene_data: Dict,
        known_studios: List[str],
        ai_client: Optional[AIClient] = None,
        use_ai: bool = True,
    ) -> Optional[DetectionResult]:
        """Detect studio using all available methods.

        Args:
            scene_data: Scene information
            known_studios: List of known studios
            ai_client: Optional AI client
            use_ai: Whether to use AI detection

        Returns:
            Best detection result
        """
        file_path = scene_data.get("file_path", "")

        # Try pattern detection first
        result = await self.detect_from_path(file_path, known_studios)

        # If pattern detection has high confidence, use it
        if result and result.confidence >= 0.85:
            return result

        # Try AI detection if enabled
        if use_ai and ai_client:
            ai_result = await self.detect_with_ai(scene_data, ai_client)

            # Compare results and use the one with higher confidence
            if ai_result:
                if not result or ai_result.confidence > result.confidence:
                    result = ai_result

        return result

    def add_custom_pattern(self, studio: str, pattern: str) -> None:
        """Add a custom pattern for studio detection.

        Args:
            studio: Studio name
            pattern: Regex pattern string
        """
        try:
            compiled: re.Pattern = re.compile(pattern, re.IGNORECASE)
            self.patterns[studio] = compiled
            logger.info(f"Added custom pattern for studio: {studio}")
        except re.error as e:
            logger.error(f"Invalid regex pattern for {studio}: {e}")
            raise ValueError(f"Invalid regex pattern: {e}")
