#!/usr/bin/env python3
"""Debug script to test bulk actions directly"""

import asyncio

from sqlalchemy import func, select

from app.database import get_db_context
from app.models.analysis import AnalysisPlan, PlanChange


async def debug_bulk_actions(plan_id: int):
    async with get_db_context() as db:
        # First, check if the plan exists
        plan_query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
        plan_result = await db.execute(plan_query)
        plan = plan_result.scalar_one_or_none()

        if not plan:
            print(f"Plan {plan_id} not found")
            return

        print(f"Plan found: {plan.name} (status: {plan.status})")

        # Count total changes
        total_query = (
            select(func.count())
            .select_from(PlanChange)
            .where(PlanChange.plan_id == plan_id)
        )
        total_result = await db.execute(total_query)
        total_count = total_result.scalar()
        print(f"Total changes: {total_count}")

        # Count by status
        status_query = (
            select(
                PlanChange.accepted,
                PlanChange.rejected,
                PlanChange.applied,
                func.count(),
            )
            .where(PlanChange.plan_id == plan_id)
            .group_by(PlanChange.accepted, PlanChange.rejected, PlanChange.applied)
        )
        status_result = await db.execute(status_query)

        print("\nChange status breakdown:")
        for row in status_result:
            accepted, rejected, applied, count = row
            print(
                f"  Accepted: {accepted}, Rejected: {rejected}, Applied: {applied} => Count: {count}"
            )

        # Count pending changes (the ones that should be affected by bulk actions)
        pending_query = (
            select(func.count())
            .select_from(PlanChange)
            .where(
                PlanChange.plan_id == plan_id,
                PlanChange.applied.is_(False),
                PlanChange.accepted.is_(False),
                PlanChange.rejected.is_(False),
            )
        )
        pending_result = await db.execute(pending_query)
        pending_count = pending_result.scalar()
        print(
            f"\nPending changes (should be affected by bulk actions): {pending_count}"
        )

        # Sample some pending changes to see their details
        sample_query = (
            select(PlanChange)
            .where(
                PlanChange.plan_id == plan_id,
                PlanChange.applied.is_(False),
                PlanChange.accepted.is_(False),
                PlanChange.rejected.is_(False),
            )
            .limit(5)
        )
        sample_result = await db.execute(sample_query)
        samples = sample_result.scalars().all()

        if samples:
            print("\nSample pending changes:")
            for change in samples:
                print(
                    f"  ID: {change.id}, Field: {change.field}, Scene: {change.scene_id}"
                )
                print(f"    Current: {change.current_value}")
                print(f"    Proposed: {change.proposed_value}")
                print(f"    Confidence: {change.confidence}")
        else:
            print("\nNo pending changes found!")


if __name__ == "__main__":
    # You can change this to test different plan IDs
    plan_id = 1  # Change this to your plan ID

    # Get plan ID from command line if provided
    import sys

    if len(sys.argv) > 1:
        plan_id = int(sys.argv[1])

    asyncio.run(debug_bulk_actions(plan_id))
