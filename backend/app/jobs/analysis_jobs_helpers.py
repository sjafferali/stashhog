"""Helper functions for analysis jobs to reduce complexity."""

from typing import Any, Dict


def calculate_plan_summary(plan_changes: Any) -> Dict[str, int]:
    """Calculate summary statistics from plan changes.

    Args:
        plan_changes: QuerySet of plan changes

    Returns:
        Dictionary with counts by change type
    """
    performers_to_add = 0
    tags_to_add = 0
    tags_to_remove = 0
    studios_to_set = 0
    titles_to_update = 0
    details_to_update = 0
    markers_to_add = 0

    # Track unique scenes with detail changes
    scenes_with_detail_changes = set()

    for change in plan_changes:
        # Handle both string enum values and mock objects with .value attribute
        action = (
            change.action.value if hasattr(change.action, "value") else change.action
        )

        if change.field == "performers" and action == "add":
            performers_to_add += 1
        elif change.field == "tags" and action == "add":
            tags_to_add += 1
        elif change.field == "tags" and action == "remove":
            tags_to_remove += 1
        elif change.field == "studio" and action == "set":
            studios_to_set += 1
        elif change.field == "title" and action == "set":
            titles_to_update += 1
        elif change.field == "details" and action in ["set", "update"]:
            details_to_update += 1
            scenes_with_detail_changes.add(change.scene_id)
        elif change.field == "markers" and action == "add":
            markers_to_add += 1

    return {
        "performers_to_add": performers_to_add,
        "tags_to_add": tags_to_add,
        "tags_to_remove": tags_to_remove,
        "studios_to_set": studios_to_set,
        "titles_to_update": titles_to_update,
        "details_to_update": details_to_update,
        "scenes_with_detail_changes": len(scenes_with_detail_changes),
        "markers_to_add": markers_to_add,
    }
