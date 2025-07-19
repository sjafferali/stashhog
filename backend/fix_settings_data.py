#!/usr/bin/env python3
"""
Script to fix incorrect setting values in the database.
Converts 0 values to None for string fields.
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.setting import Setting  # noqa: E402


async def fix_settings():
    """Fix incorrect setting values."""
    async with AsyncSessionLocal() as db:
        # Define which settings should be strings/null, not numbers
        string_settings = [
            "stash_api_key",
            "openai_base_url",
            "analysis_ai_video_server_url",
        ]

        # Fetch all settings
        query = select(Setting)
        result = await db.execute(query)
        settings = result.scalars().all()

        fixed_count = 0

        for setting in settings:
            if setting.key in string_settings and setting.value == 0:
                print(f"Fixing {setting.key}: {setting.value} -> None")
                setting.value = None
                fixed_count += 1

        if fixed_count > 0:
            await db.commit()
            print(f"\nFixed {fixed_count} settings")
        else:
            print("No settings needed fixing")


if __name__ == "__main__":
    asyncio.run(fix_settings())
