#!/usr/bin/env python3
"""Test script for Stash API service integration."""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.stash_service import StashService
from app.core.config import get_settings


async def test_stash_service():
    """Test Stash service functionality."""
    settings = get_settings()
    
    # Initialize service
    service = StashService(
        stash_url=settings.stash.url,
        api_key=settings.stash.api_key,
        timeout=settings.stash.timeout,
        max_retries=settings.stash.max_retries
    )
    
    try:
        print(f"Testing connection to Stash at {settings.stash.url}...")
        
        # Test connection
        connected = await service.test_connection()
        if not connected:
            print("❌ Failed to connect to Stash")
            return
        
        print("✅ Successfully connected to Stash")
        
        # Get stats
        print("\nFetching Stash statistics...")
        stats = await service.get_stats()
        print(f"  Scene count: {stats.get('scene_count', 0)}")
        print(f"  Performer count: {stats.get('performer_count', 0)}")
        print(f"  Tag count: {stats.get('tag_count', 0)}")
        print(f"  Studio count: {stats.get('studio_count', 0)}")
        
        # Get scenes
        print("\nFetching first 5 scenes...")
        scenes, total_count = await service.get_scenes(page=1, per_page=5)
        print(f"  Total scenes: {total_count}")
        print(f"  Retrieved: {len(scenes)} scenes")
        
        if scenes:
            # Display first scene details
            scene = scenes[0]
            print(f"\nFirst scene details:")
            print(f"  ID: {scene.get('stash_id')}")
            print(f"  Title: {scene.get('title', 'Untitled')}")
            print(f"  Path: {scene.get('path', 'N/A')}")
            print(f"  Organized: {scene.get('organized', False)}")
            print(f"  Performers: {len(scene.get('performers', []))}")
            print(f"  Tags: {len(scene.get('tags', []))}")
            
            # Test getting single scene
            print(f"\nFetching scene by ID...")
            single_scene = await service.get_scene(scene['stash_id'])
            if single_scene:
                print("✅ Successfully fetched scene by ID")
            else:
                print("❌ Failed to fetch scene by ID")
        
        # Test entity operations
        print("\nTesting entity operations...")
        
        # Get all performers
        performers = await service.get_all_performers()
        print(f"  Found {len(performers)} performers")
        
        # Get all tags
        tags = await service.get_all_tags()
        print(f"  Found {len(tags)} tags")
        
        # Get all studios
        studios = await service.get_all_studios()
        print(f"  Found {len(studios)} studios")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(test_stash_service())