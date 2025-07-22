"""Video tag detection module for scene analysis using external AI server."""

import asyncio
import logging
from typing import Any, Optional

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

    def _parse_nested_json_result(self, json_result: Any) -> dict[str, Any]:
        """Parse nested JSON result if it's a string.

        Args:
            json_result: The json_result value which may be a string or dict

        Returns:
            Parsed dictionary or empty dict if parsing fails
        """
        import json

        if isinstance(json_result, str):
            logger.debug("json_result is a string, parsing as JSON...")
            try:
                parsed_json_result = json.loads(json_result)
                logger.debug(
                    f"Successfully parsed nested JSON, type: {type(parsed_json_result)}"
                )
                if isinstance(parsed_json_result, dict):
                    logger.debug(f"Nested JSON keys: {list(parsed_json_result.keys())}")
                    return parsed_json_result
                else:
                    logger.error(
                        f"Parsed nested JSON is not a dict: {type(parsed_json_result).__name__}"
                    )
                    return {}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse nested json_result: {e}")
                logger.error(f"json_result string preview: {json_result[:500]}...")
                return {}
        elif isinstance(json_result, dict):
            logger.debug(f"json_result keys: {list(json_result.keys())}")
            return json_result
        else:
            logger.error(
                f"json_result is neither string nor dict: {type(json_result).__name__}"
            )
            return {}

    def _parse_response_json(self, response_text: str) -> Optional[dict[str, Any]]:
        """Parse the response text as JSON and extract the result.

        Args:
            response_text: Raw response text from the server

        Returns:
            Parsed result dictionary or None if parsing fails
        """
        import json

        try:
            result = json.loads(response_text)
            logger.debug(f"Successfully parsed JSON, type: {type(result)}")
            logger.debug(
                f"JSON keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
            )

            if not isinstance(result, dict):
                logger.error(
                    f"Parsed result is not a dict, it's: {type(result).__name__}"
                )
                logger.error(f"Result value: {result}")
                return {}

            result_data = result.get("result", {})
            logger.debug(f"result.get('result') type: {type(result_data)}")

            if not isinstance(result_data, dict):
                logger.error(
                    f"result['result'] is not a dict, it's: {type(result_data).__name__}"
                )
                logger.error(f"result['result'] value: {result_data}")
                return {}

            json_result = result_data.get("json_result", {})
            logger.debug(
                f"result['result'].get('json_result') type: {type(json_result)}"
            )

            return self._parse_nested_json_result(json_result)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response as JSON: {e}")
            logger.error(f"Response text that failed to parse: {response_text}")
            return None

    async def process_video_async(
        self,
        video_path: str,
        vr_video: bool = False,
    ) -> Optional[dict[str, Any]]:
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

                        return self._parse_response_json(response_text)

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

    def _get_video_path(self, scene_data: dict[str, Any]) -> Optional[str]:
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
        result: dict[str, Any],
        existing_tags: list[str],
    ) -> list[ProposedChange]:
        """Extract tag changes from AI analysis result."""
        logger.debug("_extract_tags_from_result called")
        logger.debug(f"result type: {type(result)}")
        logger.debug(
            f"result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
        )

        changes: list[ProposedChange] = []

        # Check for timespans format (new AI server response format)
        if "timespans" in result:
            logger.debug("Found timespans format, extracting tags from timespans")
            timespans = result.get("timespans", {})
            logger.debug(
                f"timespans keys: {list(timespans.keys()) if isinstance(timespans, dict) else 'Not a dict'}"
            )

            # Convert timespans to tags
            tags_from_timespans = self._convert_timespans_to_tags(timespans)
            ai_tags = tags_from_timespans
            logger.debug(f"Converted timespans to {len(ai_tags)} tags")
        else:
            # Original format with direct tags
            ai_tags = result.get("tags", [])
            logger.debug(f"Using direct tags format: {len(ai_tags)} tags")

        logger.debug(
            f"ai_tags type: {type(ai_tags)}, count: {len(ai_tags) if isinstance(ai_tags, list) else 'Not a list'}"
        )

        existing_tag_names = [t.lower() for t in existing_tags]
        logger.debug(f"existing_tag_names: {existing_tag_names}")

        logger.debug(f"Processing {len(ai_tags)} tags")
        for idx, tag_info in enumerate(ai_tags):
            logger.debug(f"Processing tag {idx}: {tag_info}")
            if isinstance(tag_info, dict):
                tag_name = tag_info.get("name", "").strip()
                confidence = tag_info.get("confidence", 0.5)
            elif isinstance(tag_info, str):
                tag_name = tag_info.strip()
                confidence = 0.7
            else:
                logger.debug(f"Skipping tag {idx}: not dict or string")
                continue

            logger.debug(f"Tag {idx}: name='{tag_name}', confidence={confidence}")

            if tag_name:
                # Add _AI suffix only if not already present
                if not tag_name.endswith("_AI"):
                    ai_tag_name = f"{tag_name}_AI"
                else:
                    ai_tag_name = tag_name

                # Check if this tag (with _AI suffix) already exists
                if ai_tag_name.lower() not in existing_tag_names:
                    logger.debug(
                        f"Adding tag change for '{ai_tag_name}' (original: '{tag_name}')"
                    )
                    changes.append(
                        ProposedChange(
                            field="tags",
                            action="add",
                            current_value=existing_tags,
                            proposed_value=ai_tag_name,
                            confidence=confidence,
                            reason="Detected from video content analysis",
                        )
                    )
            else:
                logger.debug(f"Skipping tag '{tag_name}': empty or already exists")

        return changes

    def _convert_timespans_to_tags(
        self, timespans: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Convert timespans format to tags list."""
        tags = []
        tag_map: dict[str, dict[str, Any]] = (
            {}
        )  # Use map to aggregate same tags from different categories

        for category, actions in timespans.items():
            if not isinstance(actions, dict):
                continue

            logger.debug(
                f"Processing category '{category}' with actions: {list(actions.keys())}"
            )

            for action_name, occurrences in actions.items():
                if isinstance(occurrences, list) and occurrences:
                    # Merge consecutive occurrences first
                    merged_occurrences = self._merge_consecutive_occurrences(
                        occurrences
                    )

                    # Calculate average confidence from merged occurrences
                    confidences = [
                        occ.get("confidence", 0.5)
                        for occ in merged_occurrences
                        if isinstance(occ, dict)
                    ]
                    avg_confidence = (
                        sum(confidences) / len(confidences) if confidences else 0.5
                    )

                    # Create tag entry with _AI suffix only if not already present
                    tag_name = (
                        action_name
                        if action_name.endswith("_AI")
                        else f"{action_name}_AI"
                    )

                    # Aggregate tags with same name (keep highest confidence)
                    if tag_name in tag_map:
                        if avg_confidence > tag_map[tag_name]["confidence"]:
                            tag_map[tag_name]["confidence"] = avg_confidence
                            tag_map[tag_name]["category"] = category
                    else:
                        tag_map[tag_name] = {
                            "name": tag_name,
                            "confidence": avg_confidence,
                            "category": category,
                        }

                    logger.debug(
                        f"Processed tag: {tag_name} with confidence {avg_confidence:.2f}"
                    )

        # Convert map back to list
        tags = list(tag_map.values())
        logger.debug(f"Converted timespans to {len(tags)} unique tags")
        return tags

    def _merge_consecutive_occurrences(
        self, occurrences: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Merge consecutive occurrences with same confidence level.

        This follows the AITagger plugin logic to reduce the number of markers
        by combining frame-by-frame detections into continuous time spans.

        Args:
            occurrences: List of occurrence dictionaries with start, end, confidence

        Returns:
            Merged list of occurrences
        """
        if not occurrences:
            return []

        # Sort by start time
        sorted_occurrences = sorted(occurrences, key=lambda x: x.get("start", 0))
        merged: list[dict[str, Any]] = []

        for occurrence in sorted_occurrences:
            if not isinstance(occurrence, dict):
                continue

            start = occurrence.get("start", 0)
            end = occurrence.get("end", start)
            confidence = occurrence.get("confidence", 0.5)

            # Check if we can merge with the last occurrence
            if merged:
                last = merged[-1]
                last_end = last.get("end", last.get("start", 0))

                # Merge if:
                # 1. Same confidence level
                # 2. Start time is within frame_interval of last end time
                # (AITagger uses exactly frame_interval, we allow small tolerance)
                time_gap = start - last_end
                if (
                    abs(last.get("confidence", 0) - confidence) < 0.01
                    and 0 <= time_gap <= self.frame_interval * 1.1
                ):
                    # Extend the last occurrence
                    last["end"] = end
                    logger.debug(
                        f"Merged occurrence at {start}s-{end}s into "
                        f"{last['start']}s-{last['end']}s"
                    )
                    continue

            # Add as new occurrence
            merged.append({"start": start, "end": end, "confidence": confidence})

        logger.debug(
            f"Merged {len(occurrences)} occurrences into {len(merged)} continuous spans"
        )
        return merged

    def _convert_timespans_to_markers(
        self, timespans: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Convert timespans format to markers list."""
        markers = []

        for _, actions in timespans.items():
            if not isinstance(actions, dict):
                continue

            for action_name, occurrences in actions.items():
                if isinstance(occurrences, list):
                    # Merge consecutive occurrences first
                    merged_occurrences = self._merge_consecutive_occurrences(
                        occurrences
                    )

                    # Create markers for significant occurrences
                    for occurrence in merged_occurrences:
                        if isinstance(occurrence, dict):
                            start_time = occurrence.get("start", 0)
                            end_time = occurrence.get("end", None)
                            confidence = occurrence.get("confidence", 0.5)

                            # Only create markers for high confidence occurrences
                            if confidence >= 0.7:
                                # Add _AI suffix only if not already present
                                marker_name = (
                                    action_name
                                    if action_name.endswith("_AI")
                                    else f"{action_name}_AI"
                                )
                                marker = {
                                    "time": start_time,
                                    "title": marker_name,
                                    "tags": [marker_name],
                                    "confidence": confidence,
                                }
                                # Add end_time if provided
                                if end_time is not None:
                                    marker["end_time"] = end_time
                                markers.append(marker)
                                logger.debug(
                                    f"Added marker for {marker_name} at {start_time}s"
                                    f"{f' to {end_time}s' if end_time is not None else ''}"
                                    f" with confidence {confidence:.2f}"
                                )

        return markers

    def _deduplicate_markers(
        self, markers: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Deduplicate markers that overlap in time or have same title at similar times.

        Args:
            markers: List of marker dictionaries

        Returns:
            Deduplicated list of markers
        """
        if not markers:
            return []

        # Sort by start time
        sorted_markers = sorted(markers, key=lambda x: x.get("time", 0))
        deduplicated: list[dict[str, Any]] = []

        for marker in sorted_markers:
            time = marker.get("time", 0)
            end_time = marker.get("end_time")
            title = marker.get("title", "")

            # Check for duplicates
            is_duplicate = False
            for existing in deduplicated:
                existing_time = existing.get("time", 0)
                existing_end = existing.get("end_time")
                existing_title = existing.get("title", "")

                # Check if markers overlap in time
                if end_time is not None and existing_end is not None:
                    # Both have end times - check for overlap
                    if (
                        not (end_time < existing_time or time > existing_end)
                        and title == existing_title
                    ):
                        is_duplicate = True
                        # Keep the one with higher confidence
                        if marker.get("confidence", 0) > existing.get("confidence", 0):
                            deduplicated.remove(existing)
                            is_duplicate = False
                        break
                else:
                    # Point markers - check if too close (within 2 seconds)
                    if abs(time - existing_time) < 2.0 and title == existing_title:
                        is_duplicate = True
                        # Keep the one with higher confidence
                        if marker.get("confidence", 0) > existing.get("confidence", 0):
                            deduplicated.remove(existing)
                            is_duplicate = False
                        break

            if not is_duplicate:
                deduplicated.append(marker)

        logger.debug(
            f"Deduplicated {len(markers)} markers to {len(deduplicated)} unique markers"
        )
        return deduplicated

    def _extract_markers_from_result(
        self,
        result: dict[str, Any],
        existing_markers: list[dict[str, Any]],
    ) -> list[ProposedChange]:
        """Extract marker changes from AI analysis result."""
        changes: list[ProposedChange] = []

        if not self.create_markers:
            return changes

        # Check for timespans format
        if "timespans" in result:
            logger.debug("Found timespans format, extracting markers from timespans")
            timespans = result.get("timespans", {})
            ai_markers = self._convert_timespans_to_markers(timespans)
            logger.debug(f"Converted timespans to {len(ai_markers)} markers")
        else:
            # Original format with direct markers
            ai_markers = result.get("markers", [])
            logger.debug(f"Using direct markers format: {len(ai_markers)} markers")

        # Deduplicate markers before processing
        ai_markers = self._deduplicate_markers(ai_markers)

        logger.debug(f"Processing {len(ai_markers)} markers after deduplication")
        for idx, marker_info in enumerate(ai_markers):
            logger.debug(f"Processing marker {idx}: {marker_info}")
            if isinstance(marker_info, dict):
                marker_time = marker_info.get("time", 0)
                marker_end_time = marker_info.get("end_time", None)
                marker_title = marker_info.get("title", "")
                marker_tags = marker_info.get("tags", [])
                confidence = marker_info.get("confidence", 0.7)

                logger.debug(
                    f"Marker {idx}: time={marker_time}, title='{marker_title}', tags={marker_tags}, confidence={confidence}"
                )

                if marker_time > 0 and (marker_title or marker_tags):
                    # Check if marker already exists at this time
                    existing_at_time = any(
                        abs(m.get("seconds", -1) - marker_time) < 2
                        for m in existing_markers
                    )

                    if not existing_at_time:
                        # Add _AI suffix to marker title and tags only if not already present
                        ai_marker_title = (
                            marker_title
                            if marker_title.endswith("_AI")
                            else f"{marker_title}_AI" if marker_title else ""
                        )
                        ai_marker_tags = [
                            tag if tag.endswith("_AI") else f"{tag}_AI"
                            for tag in marker_tags
                        ]

                        logger.debug(
                            f"Adding marker change for '{ai_marker_title}' at {marker_time}s"
                            f"{f' to {marker_end_time}s' if marker_end_time is not None else ''}"
                        )
                        marker_value = {
                            "seconds": marker_time,
                            "title": ai_marker_title,
                            "tags": ai_marker_tags,
                        }
                        # Add end_seconds if provided
                        if marker_end_time is not None:
                            marker_value["end_seconds"] = marker_end_time

                        changes.append(
                            ProposedChange(
                                field="markers",
                                action="add",
                                current_value=existing_markers,
                                proposed_value=marker_value,
                                confidence=confidence,
                                reason="Detected from video content",
                            )
                        )
                    else:
                        logger.debug(
                            f"Marker already exists at time {marker_time}s, skipping"
                        )

        return changes

    async def detect(
        self,
        scene_data: dict[str, Any],
        existing_tags: list[str],
        existing_markers: list[dict[str, Any]],
    ) -> tuple[list[ProposedChange], Optional[dict[str, Any]]]:
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

        changes: list[ProposedChange] = []

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
                error_msg = f"No result from AI server for scene {scene_data.get('id')}"
                logger.error(error_msg)
                # Raise exception instead of returning empty changes
                # This will ensure the error is properly propagated
                raise RuntimeError(error_msg)

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
