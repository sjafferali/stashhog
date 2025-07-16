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
    studios_to_set = 0
    titles_to_update = 0

    for change in plan_changes:
        if change.field == "performers" and change.action.value == "add":
            performers_to_add += 1
        elif change.field == "tags" and change.action.value == "add":
            tags_to_add += 1
        elif change.field == "studio" and change.action.value == "set":
            studios_to_set += 1
        elif change.field == "title" and change.action.value == "set":
            titles_to_update += 1

    return {
        "performers_to_add": performers_to_add,
        "tags_to_add": tags_to_add,
        "studios_to_set": studios_to_set,
        "titles_to_update": titles_to_update,
    }
