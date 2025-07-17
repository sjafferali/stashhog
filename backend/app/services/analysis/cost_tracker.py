"""Cost tracking service for OpenAI API usage."""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AnalysisCostTracker:
    """Track costs for analysis operations."""

    def __init__(self) -> None:
        """Initialize cost tracker."""
        self.operation_costs: Dict[str, float] = {
            "studio_detection": 0.0,
            "performer_detection": 0.0,
            "tag_detection": 0.0,
            "details_generation": 0.0,
        }
        self.token_usage: Dict[str, Dict[str, int]] = {
            "studio_detection": {"prompt": 0, "completion": 0, "total": 0},
            "performer_detection": {"prompt": 0, "completion": 0, "total": 0},
            "tag_detection": {"prompt": 0, "completion": 0, "total": 0},
            "details_generation": {"prompt": 0, "completion": 0, "total": 0},
        }
        self.scenes_analyzed: int = 0
        self.model_used: Optional[str] = None

    def track_operation(
        self,
        operation: str,
        cost: float,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
    ) -> None:
        """Track cost for a specific operation.

        Args:
            operation: Type of operation (studio_detection, etc.)
            cost: Cost in USD
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens used
            model: Model used for the operation
        """
        if operation in self.operation_costs:
            self.operation_costs[operation] += cost
            self.token_usage[operation]["prompt"] += prompt_tokens
            self.token_usage[operation]["completion"] += completion_tokens
            self.token_usage[operation]["total"] += prompt_tokens + completion_tokens

            if model and not self.model_used:
                self.model_used = model

            logger.debug(
                f"Tracked {operation}: ${cost:.4f} "
                f"({prompt_tokens} + {completion_tokens} tokens)"
            )
        else:
            logger.warning(f"Unknown operation type: {operation}")

    def increment_scenes(self) -> None:
        """Increment the count of scenes analyzed."""
        self.scenes_analyzed += 1

    def get_total_cost(self) -> float:
        """Get total cost across all operations."""
        return sum(self.operation_costs.values())

    def get_total_tokens(self) -> Dict[str, int]:
        """Get total token usage across all operations."""
        total_prompt = sum(op["prompt"] for op in self.token_usage.values())
        total_completion = sum(op["completion"] for op in self.token_usage.values())

        return {
            "prompt": total_prompt,
            "completion": total_completion,
            "total": total_prompt + total_completion,
        }

    def get_average_cost_per_scene(self) -> float:
        """Get average cost per scene analyzed."""
        if self.scenes_analyzed == 0:
            return 0.0
        return self.get_total_cost() / self.scenes_analyzed

    def get_summary(self) -> Dict[str, Any]:
        """Get complete cost summary."""
        total_tokens = self.get_total_tokens()

        return {
            "total_cost": self.get_total_cost(),
            "total_tokens": total_tokens["total"],
            "prompt_tokens": total_tokens["prompt"],
            "completion_tokens": total_tokens["completion"],
            "cost_breakdown": self.operation_costs.copy(),
            "token_breakdown": self.token_usage.copy(),
            "scenes_analyzed": self.scenes_analyzed,
            "average_cost_per_scene": self.get_average_cost_per_scene(),
            "model": self.model_used,
        }

    def reset(self) -> None:
        """Reset all tracking."""
        for key in self.operation_costs:
            self.operation_costs[key] = 0.0
        for key in self.token_usage:
            self.token_usage[key] = {"prompt": 0, "completion": 0, "total": 0}
        self.scenes_analyzed = 0
        self.model_used = None

    def __repr__(self) -> str:
        """String representation of tracker state."""
        return (
            f"AnalysisCostTracker("
            f"total_cost=${self.get_total_cost():.4f}, "
            f"scenes={self.scenes_analyzed}, "
            f"model={self.model_used})"
        )
