"""Video tag detection module for scene analysis using external AI server."""

import asyncio
import logging
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
    ) -> Optional[Dict[str, Any]]:
        """Process video file through external AI server.

        Args:
            video_path: Path to the video file
            vr_video: Whether this is a VR video

        Returns:
            Analysis results from AI server or None if failed
        """
        logger.debug(
            f"process_video_async called with video_path: {video_path}, vr_video: {vr_video}"
        )

        payload = {
            "path": video_path,
            "frame_interval": self.frame_interval,
            "threshold": self.video_threshold,
            "return_confidence": True,
            "vr_video": vr_video,
        }
        logger.debug(f"Prepared payload: {payload}")

        url = f"{self.api_base_url}/process_video/"
        logger.debug(f"AI server URL: {url}")

        try:
            timeout = aiohttp.ClientTimeout(total=self.server_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logger.debug("Sending POST request to AI server...")
                async with session.post(url, json=payload) as response:
                    logger.debug(f"Received response with status: {response.status}")
                    if response.status == 200:
                        # First read the raw response text
                        response_text = await response.text()
                        logger.debug(f"Raw response text length: {len(response_text)}")
                        logger.debug(
                            f"Raw response preview: {response_text[:500]}..."
                            if len(response_text) > 500
                            else f"Raw response: {response_text}"
                        )

                        try:
                            # Try to parse as JSON
                            import json

                            result = json.loads(response_text)
                            logger.debug(
                                f"Successfully parsed JSON, type: {type(result)}"
                            )
                            logger.debug(
                                f"JSON keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
                            )

                            # Check if result is a dict before trying to access it
                            if isinstance(result, dict):
                                result_data = result.get("result", {})
                                logger.debug(
                                    f"result.get('result') type: {type(result_data)}"
                                )

                                if isinstance(result_data, dict):
                                    json_result: Dict[str, Any] = result_data.get(
                                        "json_result", {}
                                    )
                                    logger.debug(
                                        f"result['result'].get('json_result') type: {type(json_result)}"
                                    )
                                    logger.debug(
                                        f"json_result keys: {list(json_result.keys()) if isinstance(json_result, dict) else 'Not a dict'}"
                                    )
                                    return json_result
                                else:
                                    logger.error(
                                        f"result['result'] is not a dict, it's: {type(result_data).__name__}"
                                    )
                                    logger.error(
                                        f"result['result'] value: {result_data}"
                                    )
                                    return {}
                            else:
                                logger.error(
                                    f"Parsed result is not a dict, it's: {type(result).__name__}"
                                )
                                logger.error(f"Result value: {result}")
                                return {}

                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse response as JSON: {e}")
                            logger.error(
                                f"Response text that failed to parse: {response_text}"
                            )
                            return None

                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to process video, status: {response.status}, error: {error_text}"
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
        logger.debug(f"_get_video_path called with scene_data type: {type(scene_data)}")
        logger.debug(
            f"scene_data keys: {list(scene_data.keys()) if isinstance(scene_data, dict) else 'Not a dict'}"
        )

        video_path = scene_data.get("file_path") or scene_data.get("path")
        logger.debug(f"Extracted video_path: {video_path}")

        if not video_path:
            logger.error(f"No video path found for scene {scene_data.get('id')}")
            logger.error(f"Available keys in scene_data: {list(scene_data.keys())}")
            return None

        return str(video_path)

    def _extract_tags_from_result(
        self,
        result: Dict[str, Any],
        existing_tags: List[str],
    ) -> List[ProposedChange]:
        """Extract tag changes from AI analysis result."""
        logger.debug("_extract_tags_from_result called")
        logger.debug(f"result type: {type(result)}")
        logger.debug(
            f"result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
        )

        changes: List[ProposedChange] = []
        ai_tags = result.get("tags", [])
        logger.debug(
            f"ai_tags type: {type(ai_tags)}, count: {len(ai_tags) if isinstance(ai_tags, list) else 'Not a list'}"
        )

        existing_tag_names = [t.lower() for t in existing_tags]
        logger.debug(f"existing_tag_names: {existing_tag_names}")

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
        logger.debug("VideoTagDetector.detect called")
        logger.debug(f"scene_data type: {type(scene_data)}")
        logger.debug(
            f"existing_tags type: {type(existing_tags)}, count: {len(existing_tags)}"
        )
        logger.debug(
            f"existing_markers type: {type(existing_markers)}, count: {len(existing_markers)}"
        )

        changes: List[ProposedChange] = []

        # Validate scene_data is a dictionary
        if not isinstance(scene_data, dict):
            logger.error(
                f"Invalid scene_data type: expected dict, got {type(scene_data).__name__}"
            )
            logger.error(f"scene_data value: {scene_data}")
            return changes, None

        # Log scene_data structure
        logger.debug(f"scene_data keys: {list(scene_data.keys())}")
        logger.debug(f"scene_data['id']: {scene_data.get('id')}")

        # Get and validate video path
        video_path = self._get_video_path(scene_data)
        if not video_path:
            logger.error("Failed to extract video path from scene_data")
            return changes, None

        try:
            # Process video through AI server
            logger.info(
                f"Processing video for scene {scene_data.get('id')}: {video_path}"
            )
            result = await self.process_video_async(
                video_path=video_path,
                vr_video=scene_data.get("is_vr", False),
            )

            logger.debug(f"process_video_async returned type: {type(result)}")
            if result is not None:
                logger.debug(
                    f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
                )

            if not result:
                logger.error(
                    f"No result from AI server for scene {scene_data.get('id')}"
                )
                return changes, None

            # Extract tags from result
            logger.debug("Extracting tags from result...")
            tag_changes = self._extract_tags_from_result(result, existing_tags)
            logger.debug(f"Found {len(tag_changes)} tag changes")
            changes.extend(tag_changes)

            # Extract markers from result
            logger.debug("Extracting markers from result...")
            marker_changes = self._extract_markers_from_result(result, existing_markers)
            logger.debug(f"Found {len(marker_changes)} marker changes")
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

            logger.debug(f"Returning {len(changes)} total changes")
            return changes, cost_info

        except Exception as e:
            logger.error(
                f"Error detecting video tags for scene {scene_data.get('id')}: {e}",
                exc_info=True,
            )
            # Raise the exception so it can be properly handled upstream
            raise
