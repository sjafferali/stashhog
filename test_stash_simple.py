#!/usr/bin/env python3
"""Simple test for Stash API service."""

import asyncio
import os
from backend.app.services.stash_service import StashService


async def test_stash():
    """Simple test of Stash service."""
    # Get settings from environment or use defaults
    stash_url = os.getenv("STASH_URL", "http://localhost:9999")
    stash_api_key = os.getenv("STASH_API_KEY", "")
    
    print(f"Testing Stash service connection to {stash_url}...")
    
    service = StashService(
        stash_url=stash_url,
        api_key=stash_api_key,
        timeout=10
    )
    
    try:
        # Test connection
        connected = await service.test_connection()
        print(f"Connection test: {'✅ Success' if connected else '❌ Failed'}")
        
        if connected:
            # Get stats
            stats = await service.get_stats()
            print(f"\nStash Statistics:")
            print(f"  Scenes: {stats.get('scene_count', 0)}")
            print(f"  Performers: {stats.get('performer_count', 0)}")
            print(f"  Tags: {stats.get('tag_count', 0)}")
            print(f"  Studios: {stats.get('studio_count', 0)}")
    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(test_stash())