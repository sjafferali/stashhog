#!/usr/bin/env python3
"""Test script to verify plan application behavior."""

import asyncio
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models import PlanChange, AnalysisPlan
from app.services.stash_service import StashService
from app.services.analysis.plan_manager import PlanManager
from app.core.config import Settings


async def test_plan_application():
    """Test plan application behavior with and without change_ids."""
    
    # Create database session
    async with AsyncSessionLocal() as db:
        # Get a test plan (you'll need to update this with a real plan ID)
        plan_id = 1  # UPDATE THIS
        
        # Get all changes for the plan
        changes_query = select(PlanChange).where(PlanChange.plan_id == plan_id)
        result = await db.execute(changes_query)
        all_changes = list(result.scalars().all())
        
        print(f"\\nTotal changes in plan {plan_id}: {len(all_changes)}")
        
        if len(all_changes) < 3:
            print("Need at least 3 changes to test properly")
            return
        
        # Reset all changes to clean state
        reset_query = (
            update(PlanChange)
            .where(PlanChange.plan_id == plan_id)
            .values(accepted=False, rejected=False, applied=False)
        )
        await db.execute(reset_query)
        await db.commit()
        
        # Mark some changes as accepted
        accepted_ids = [all_changes[0].id, all_changes[1].id]
        for change_id in accepted_ids:
            update_query = (
                update(PlanChange)
                .where(PlanChange.id == change_id)
                .values(accepted=True)
            )
            await db.execute(update_query)
        await db.commit()
        
        print(f"\\nMarked {len(accepted_ids)} changes as accepted")
        print(f"Left {len(all_changes) - len(accepted_ids)} changes neutral")
        
        # Create services
        settings = Settings()
        stash_service = StashService(
            stash_url=settings.stash.url,
            api_key=settings.stash.api_key
        )
        plan_manager = PlanManager()
        
        # Test 1: Apply without change_ids (should only apply accepted changes)
        print("\\n--- Test 1: Apply without change_ids ---")
        result = await plan_manager.apply_plan(
            plan_id=plan_id,
            db=db,
            stash_service=stash_service,
            change_ids=None
        )
        
        print(f"Application result:")
        print(f"- Total changes processed: {result.total_changes}")
        print(f"- Applied changes: {result.applied_changes}")
        print(f"- Failed changes: {result.failed_changes}")
        
        if result.total_changes == len(accepted_ids):
            print("✅ SUCCESS: Only accepted changes were processed!")
        else:
            print(f"❌ FAILED: Expected {len(accepted_ids)} changes, but {result.total_changes} were processed")
        
        # Reset applied status for test 2
        reset_applied = (
            update(PlanChange)
            .where(PlanChange.plan_id == plan_id)
            .values(applied=False)
        )
        await db.execute(reset_applied)
        await db.commit()
        
        # Test 2: Apply with specific change_ids
        print("\\n--- Test 2: Apply with specific change_ids ---")
        specific_ids = [all_changes[2].id]  # A change that wasn't marked as accepted
        result2 = await plan_manager.apply_plan(
            plan_id=plan_id,
            db=db,
            stash_service=stash_service,
            change_ids=specific_ids
        )
        
        print(f"Application result:")
        print(f"- Total changes processed: {result2.total_changes}")
        print(f"- Applied changes: {result2.applied_changes}")
        print(f"- Failed changes: {result2.failed_changes}")
        
        if result2.total_changes == len(specific_ids):
            print("✅ SUCCESS: Only specified change IDs were processed!")
        else:
            print(f"❌ FAILED: Expected {len(specific_ids)} changes, but {result2.total_changes} were processed")


if __name__ == "__main__":
    asyncio.run(test_plan_application())