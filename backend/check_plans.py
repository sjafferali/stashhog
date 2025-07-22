#!/usr/bin/env python3
"""Check existing plans in the database"""

import asyncio

from sqlalchemy import select

from app.database import get_db_context
from app.models.analysis import AnalysisPlan


async def check_plans():
    async with get_db_context() as db:
        query = select(AnalysisPlan).order_by(AnalysisPlan.id.desc()).limit(10)
        result = await db.execute(query)
        plans = result.scalars().all()

        if not plans:
            print("No plans found in database")
            return

        print("Recent plans:")
        for plan in plans:
            print(f"  ID: {plan.id}, Name: {plan.name}, Status: {plan.status}")
            print(
                f"    Total scenes: {plan.total_scenes}, Total changes: {plan.total_changes}"
            )
            print(f"    Created: {plan.created_at}")
            print()


if __name__ == "__main__":
    asyncio.run(check_plans())
