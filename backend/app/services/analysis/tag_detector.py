"""Tag detection module for scene analysis."""

import logging
from typing import Optional, Tuple

from .ai_client import AIClient
from .models import DetectionResult, TagSuggestionsResponse
from .prompts import TAG_SUGGESTION_PROMPT

logger = logging.getLogger(__name__)


class TagDetector:
    """Detect and suggest tags for scenes."""

    # Tag hierarchy for redundancy detection
    TAG_HIERARCHY = {
        "bareback": ["raw", "no condom"],
        "threesome": ["3way", "three way"],
        "foursome": ["4way", "four way"],
        "group": ["orgy", "gangbang"],
        "interracial": ["ir", "mixed race"],
        "amateur": ["homemade", "self made"],
        "daddy": ["dad", "older"],
        "twink": ["young", "teen"],
        "muscle": ["muscular", "jock", "bodybuilder"],
        "bear": ["hairy", "stocky"],
        "latino": ["latin", "hispanic"],
        "black": ["african american", "ebony"],
        "asian": ["oriental"],
        "uncut": ["uncircumcised", "foreskin"],
        "cut": ["circumcised"],
        "big dick": ["hung", "large cock", "big cock"],
        "anal": ["ass fucking", "butt sex"],
        "oral": ["blowjob", "bj", "cocksucking"],
        "rimming": ["rim job", "ass licking"],
        "cumshot": ["cum", "load", "jizz"],
        "creampie": ["breeding", "internal"],
        "outdoor": ["outdoors", "public"],
        "fetish": ["kink", "bdsm"],
    }

    # Technical tags based on video properties
    RESOLUTION_TAGS = {
        (3840, 2160): ["4K", "UHD", "2160p"],
        (2560, 1440): ["2K", "1440p", "QHD"],
        (1920, 1080): ["1080p", "Full HD", "FHD"],
        (1280, 720): ["720p", "HD"],
        (854, 480): ["480p", "SD"],
    }

    DURATION_TAGS = {
        (0, 300): ["short", "quickie"],  # 0-5 minutes
        (300, 900): ["medium length"],  # 5-15 minutes
        (900, 1800): ["standard length"],  # 15-30 minutes
        (1800, 3600): ["long", "full scene"],  # 30-60 minutes
        (3600, float("inf")): ["feature length", "compilation"],  # 60+ minutes
    }

    def __init__(self) -> None:
        """Initialize tag detector."""
        self._tag_cache: dict[str, list[DetectionResult]] = {}
        self._build_reverse_hierarchy()

    def _build_reverse_hierarchy(self) -> None:
        """Build reverse mapping for tag hierarchy."""
        self.parent_tags: dict[str, str] = {}
        for parent, children in self.TAG_HIERARCHY.items():
            for child in children:
                self.parent_tags[child.lower()] = parent

    async def detect_with_ai(
        self,
        scene_data: dict,
        ai_client: AIClient,
        existing_tags: list[str],
        available_tags: list[str],
    ) -> list[DetectionResult]:
        """Use AI to suggest tags for the scene.

        Args:
            scene_data: Scene information
            ai_client: AI client for analysis
            existing_tags: Tags already assigned to the scene
            available_tags: All available tags in the database

        Returns:
            List of suggested tags with confidence scores
        """
        try:
            # Add existing tags and available tags to scene data
            scene_data_with_tags = scene_data.copy()
            scene_data_with_tags["tags"] = (
                ", ".join(existing_tags) if existing_tags else "None"
            )
            scene_data_with_tags["available_tags"] = available_tags

            response = await ai_client.analyze_scene(
                prompt=TAG_SUGGESTION_PROMPT,
                scene_data=scene_data_with_tags,
                response_format=TagSuggestionsResponse,
                temperature=0.3,
            )

            # Ensure response is the expected type
            if not isinstance(response, TagSuggestionsResponse):
                logger.error(f"Unexpected response type: {type(response)}")
                return []

            results = []
            for tag in response.tags:
                name = tag.name.strip()
                confidence = tag.confidence

                if name and name.lower() not in [t.lower() for t in existing_tags]:
                    results.append(
                        DetectionResult(
                            value=name,
                            confidence=confidence,
                            source="ai",
                            metadata={"model": ai_client.model},
                        )
                    )

            # Filter out redundant tags
            filtered_results = self._filter_redundant_results(results, existing_tags)
            return filtered_results

        except Exception as e:
            logger.error(f"AI tag detection error: {e}", exc_info=True)
            # Try to provide more context about the error
            if hasattr(e, "__class__"):
                logger.error(f"Error type: {e.__class__.__name__}")
            return []

    async def detect_with_ai_tracked(
        self,
        scene_data: dict,
        ai_client: AIClient,
        existing_tags: list[str],
        available_tags: list[str],
    ) -> Tuple[list[DetectionResult], Optional[dict]]:
        """Use AI to suggest tags and return cost information.

        Args:
            scene_data: Scene information
            ai_client: AI client for analysis
            existing_tags: Tags already assigned to the scene
            available_tags: All available tags in the database

        Returns:
            Tuple of (list of suggested tags, cost information)
        """
        try:
            # Add existing tags and available tags to scene data
            scene_data_with_tags = scene_data.copy()
            scene_data_with_tags["tags"] = (
                ", ".join(existing_tags) if existing_tags else "None"
            )
            scene_data_with_tags["available_tags"] = available_tags

            response, cost_info = await ai_client.analyze_scene_with_cost(
                prompt=TAG_SUGGESTION_PROMPT,
                scene_data=scene_data_with_tags,
                response_format=TagSuggestionsResponse,
                temperature=0.3,
            )

            # Ensure response is the expected type
            if not isinstance(response, TagSuggestionsResponse):
                logger.error(f"Unexpected response type: {type(response)}")
                return [], cost_info

            results = []
            for tag in response.tags:
                name = tag.name.strip()
                confidence = tag.confidence

                if name and name.lower() not in [t.lower() for t in existing_tags]:
                    results.append(
                        DetectionResult(
                            value=name,
                            confidence=confidence,
                            source="ai",
                            metadata={"model": ai_client.model},
                        )
                    )

            # Filter out redundant tags
            filtered_results = self._filter_redundant_results(results, existing_tags)
            return filtered_results, cost_info

        except Exception as e:
            logger.error(f"AI tag detection error: {e}", exc_info=True)
            return [], None

    def detect_technical_tags(
        self, scene_data: dict, existing_tags: list[str]
    ) -> list[DetectionResult]:
        """Detect technical tags based on video properties.

        Args:
            scene_data: Scene information with technical details
            existing_tags: Already assigned tags

        Returns:
            List of technical tag suggestions
        """
        results = []
        existing_lower = [t.lower() for t in existing_tags]

        # Resolution-based tags
        width = scene_data.get("width") or 0
        height = scene_data.get("height") or 0

        for (res_width, res_height), tags in self.RESOLUTION_TAGS.items():
            if width >= res_width and height >= res_height:
                for tag in tags:
                    if tag.lower() not in existing_lower:
                        results.append(
                            DetectionResult(
                                value=tag,
                                confidence=0.95,
                                source="technical",
                                metadata={
                                    "type": "resolution",
                                    "width": width,
                                    "height": height,
                                },
                            )
                        )
                break  # Use highest matching resolution

        # Duration-based tags
        duration = scene_data.get("duration") or 0

        for (min_dur, max_dur), tags in self.DURATION_TAGS.items():
            if min_dur <= duration < max_dur:
                for tag in tags:
                    if tag.lower() not in existing_lower:
                        results.append(
                            DetectionResult(
                                value=tag,
                                confidence=0.9,
                                source="technical",
                                metadata={"type": "duration", "seconds": duration},
                            )
                        )
                break

        # Frame rate tags
        frame_rate = scene_data.get("frame_rate") or 0
        if frame_rate >= 60 and "60fps" not in existing_lower:
            results.append(
                DetectionResult(
                    value="60fps",
                    confidence=0.95,
                    source="technical",
                    metadata={"type": "framerate", "fps": frame_rate},
                )
            )

        return results

    def filter_redundant_tags(self, tags: list[str], existing: list[str]) -> list[str]:
        """Remove redundant or duplicate tags.

        Args:
            tags: Proposed new tags
            existing: Already assigned tags

        Returns:
            Filtered list of non-redundant tags
        """
        # Convert to lowercase for comparison
        existing_lower = set(t.lower() for t in existing)
        filtered = []

        for tag in tags:
            tag_lower = tag.lower()

            # Skip if already exists
            if tag_lower in existing_lower:
                continue

            # Check if it's a child of an existing tag
            is_redundant = False
            for existing_tag in existing_lower:
                if existing_tag in self.TAG_HIERARCHY:
                    children = [c.lower() for c in self.TAG_HIERARCHY[existing_tag]]
                    if tag_lower in children:
                        is_redundant = True
                        break

            # Check if existing tags are children of this tag
            if not is_redundant and tag_lower in self.TAG_HIERARCHY:
                children = [c.lower() for c in self.TAG_HIERARCHY[tag_lower]]
                # If we have child tags, we might want to keep the parent
                has_children = any(child in existing_lower for child in children)
                if has_children:
                    # Skip adding parent if we already have specific children
                    continue

            if not is_redundant:
                filtered.append(tag)

        return filtered

    def _filter_redundant_results(
        self, results: list[DetectionResult], existing_tags: list[str]
    ) -> list[DetectionResult]:
        """Filter redundant tags from detection results.

        Args:
            results: Detection results to filter
            existing_tags: Already assigned tags

        Returns:
            Filtered detection results
        """
        # Extract just the tag values
        proposed_tags = [r.value for r in results]

        # Filter using the main method
        filtered_tags = self.filter_redundant_tags(proposed_tags, existing_tags)

        # Return only results for filtered tags
        filtered_results = []
        for result in results:
            if result.value in filtered_tags:
                filtered_results.append(result)

        return filtered_results

    def suggest_related_tags(
        self, current_tags: list[str], all_available_tags: list[str]
    ) -> list[DetectionResult]:
        """Suggest related tags based on current tags.

        Args:
            current_tags: Currently assigned tags
            all_available_tags: All tags available in the system

        Returns:
            List of related tag suggestions
        """
        suggestions = []
        current_lower = set(t.lower() for t in current_tags)

        # Build co-occurrence map (simplified version)
        related_map: dict[str, list[str]] = {
            "bareback": ["creampie", "breeding", "raw"],
            "daddy": ["mature", "older younger", "dad son"],
            "twink": ["young", "smooth", "college"],
            "muscle": ["gym", "jock", "athletic"],
            "outdoor": ["public", "nature", "cruising"],
            "fetish": ["leather", "rubber", "gear"],
            "amateur": ["homemade", "real", "authentic"],
            "interracial": ["bbc", "mixed", "contrast"],
        }

        # Find related tags
        for tag in current_tags:
            tag_lower = tag.lower()
            if tag_lower in related_map:
                for related in related_map[tag_lower]:
                    if related not in current_lower and any(
                        related in t.lower() for t in all_available_tags
                    ):
                        suggestions.append(
                            DetectionResult(
                                value=related,
                                confidence=0.6,
                                source="related",
                                metadata={"based_on": tag},
                            )
                        )

        return suggestions
