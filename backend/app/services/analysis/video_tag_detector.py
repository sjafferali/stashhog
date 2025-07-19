"""Video tag detection module for scene analysis using external AI server."""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from app.core.config import Settings

from .models import ProposedChange

logger = logging.getLogger(__name__)


class VideoTagDetector:
    """Detect tags and markers from video content using external AI server."""

    def __init__(self, settings: Settings):
        """Initialize video tag detector.

        Args:
            settings: Application settings
        """
        self.settings = settings
        # Configuration from settings
        self.api_base_url = settings.analysis.ai_video_server_url
        self.frame_interval = settings.analysis.frame_interval
        self.video_threshold = settings.analysis.ai_video_threshold
        self.server_timeout = settings.analysis.server_timeout
        self.create_markers = settings.analysis.create_markers

    async def process_video_async(
        self,
        video_path: str,
        vr_video: bool = False,
        existing_json: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """Process video file through external AI server.

        Args:
            video_path: Path to the video file
            vr_video: Whether this is a VR video
            existing_json: Existing analysis data if any

        Returns:
            Analysis results from AI server or None if failed
        """
        payload = {
            "path": video_path,
            "frame_interval": self.frame_interval,
            "threshold": self.video_threshold,
            "return_confidence": True,
            "vr_video": vr_video,
            "existing_json_data": existing_json,
        }

        url = f"{self.api_base_url}/process_video/"

        try:
            timeout = aiohttp.ClientTimeout(total=self.server_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        json_result: Dict[str, Any] = result.get("result", {}).get(
                            "json_result", {}
                        )
                        return json_result
                    else:
                        logger.error(
                            f"Failed to process video, status: {response.status}"
                        )
                        return None

        except aiohttp.ClientConnectionError as e:
            logger.error(f"Failed to connect to AI server at {self.api_base_url}: {e}")
            raise
        except asyncio.TimeoutError:
            logger.error(f"Timeout processing video after {self.server_timeout}s")
            raise
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            raise

    def _get_video_path(self, scene_data: Dict[str, Any]) -> Optional[str]:
        """Extract and validate video path from scene data."""
        video_path = scene_data.get("file_path") or scene_data.get("path")
        if not video_path:
            logger.error(f"No video path found for scene {scene_data.get('id')}")
            return None

        return str(video_path)

    def _load_existing_analysis(self, ai_json_path: str) -> Optional[Dict]:
        """Load existing AI analysis from file if available."""
        if not os.path.exists(ai_json_path):
            return None

        try:
            with open(ai_json_path, "r") as f:
                data: Dict[Any, Any] = json.load(f)
                return data
        except Exception as e:
            logger.warning(f"Failed to read existing AI analysis: {e}")
            return None

    def _save_analysis_result(self, ai_json_path: str, result: Dict) -> None:
        """Save AI analysis result to file."""
        try:
            with open(ai_json_path, "w") as f:
                json.dump(result, f, indent=2)
            # Set appropriate permissions if needed
            if hasattr(os, "chown"):
                try:
                    os.chown(ai_json_path, 1050, 1050)
                except Exception:
                    pass  # Ignore permission errors
        except Exception as e:
            logger.warning(f"Failed to save AI analysis to file: {e}")

    def _extract_tags_from_result(
        self,
        result: Dict[str, Any],
        existing_tags: List[str],
    ) -> List[ProposedChange]:
        """Extract tag changes from AI analysis result."""
        changes: List[ProposedChange] = []
        ai_tags = result.get("tags", [])
        existing_tag_names = [t.lower() for t in existing_tags]

        for tag_info in ai_tags:
            if isinstance(tag_info, dict):
                tag_name = tag_info.get("name", "").strip()
                confidence = tag_info.get("confidence", 0.5)
            elif isinstance(tag_info, str):
                tag_name = tag_info.strip()
                confidence = 0.7
            else:
                continue

            if tag_name and tag_name.lower() not in existing_tag_names:
                changes.append(
                    ProposedChange(
                        field="tags",
                        action="add",
                        current_value=existing_tags,
                        proposed_value=tag_name,
                        confidence=confidence,
                        reason="Detected from video content analysis",
                    )
                )

        return changes

    def _extract_markers_from_result(
        self,
        result: Dict[str, Any],
        existing_markers: List[Dict[str, Any]],
    ) -> List[ProposedChange]:
        """Extract marker changes from AI analysis result."""
        changes: List[ProposedChange] = []

        if not self.create_markers:
            return changes

        ai_markers = result.get("markers", [])

        for marker_info in ai_markers:
            if isinstance(marker_info, dict):
                marker_time = marker_info.get("time", 0)
                marker_title = marker_info.get("title", "")
                marker_tags = marker_info.get("tags", [])
                confidence = marker_info.get("confidence", 0.7)

                if marker_time > 0 and (marker_title or marker_tags):
                    # Check if marker already exists at this time
                    existing_at_time = any(
                        abs(m.get("seconds", -1) - marker_time) < 2
                        for m in existing_markers
                    )

                    if not existing_at_time:
                        changes.append(
                            ProposedChange(
                                field="markers",
                                action="add",
                                current_value=existing_markers,
                                proposed_value={
                                    "seconds": marker_time,
                                    "title": marker_title,
                                    "tags": marker_tags,
                                },
                                confidence=confidence,
                                reason="Detected from video content",
                            )
                        )

        return changes

    async def detect(
        self,
        scene_data: Dict[str, Any],
        existing_tags: List[str],
        existing_markers: List[Dict[str, Any]],
    ) -> Tuple[List[ProposedChange], Optional[Dict[str, Any]]]:
        """Detect tags and markers from video content.

        Args:
            scene_data: Scene information including file path
            existing_tags: Currently assigned tags
            existing_markers: Currently assigned markers

        Returns:
            Tuple of (proposed changes, cost info)
        """
        changes: List[ProposedChange] = []

        # Get and validate video path
        video_path = self._get_video_path(scene_data)
        if not video_path:
            return changes, None

        try:
            # Check if we have existing AI analysis
            ai_json_path = f"{video_path}.AI.json"
            existing_analysis = self._load_existing_analysis(ai_json_path)

            # Process video through AI server
            logger.info(
                f"Processing video for scene {scene_data.get('id')}: {video_path}"
            )
            result = await self.process_video_async(
                video_path=video_path,
                vr_video=scene_data.get("is_vr", False),
                existing_json=existing_analysis,
            )

            if not result:
                logger.error(
                    f"No result from AI server for scene {scene_data.get('id')}"
                )
                return changes, None

            # Save result to file
            self._save_analysis_result(ai_json_path, result)

            # Extract tags from result
            tag_changes = self._extract_tags_from_result(result, existing_tags)
            changes.extend(tag_changes)

            # Extract markers from result
            marker_changes = self._extract_markers_from_result(result, existing_markers)
            changes.extend(marker_changes)

            # Calculate approximate cost (simplified)
            cost_info = {
                "model": "video-analysis",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost": 0.0,  # Cost would depend on external AI server
                "duration": len(result.get("tags", []))
                + len(result.get("markers", [])),
            }

            return changes, cost_info

        except Exception as e:
            logger.error(
                f"Error detecting video tags for scene {scene_data.get('id')}: {e}"
            )
            return changes, None
