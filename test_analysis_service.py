#!/usr/bin/env python3
"""Test script for the analysis service."""
import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import get_settings
from backend.app.core.database import Base
from backend.app.services.stash_service import StashService
from backend.app.services.openai_client import OpenAIClient
from backend.app.services.analysis import AnalysisService, AnalysisOptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_analysis_service():
    """Test the analysis service functionality."""
    settings = get_settings()
    
    # Create database engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///./test_analysis.db",
        echo=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db:
        try:
            # Initialize services
            stash_service = StashService()
            
            # Check if OpenAI is configured
            if not settings.openai.api_key:
                logger.warning("OpenAI API key not configured. Skipping AI tests.")
                return
            
            openai_client = OpenAIClient(
                api_key=settings.openai.api_key,
                model=settings.openai.model
            )
            
            analysis_service = AnalysisService(
                openai_client=openai_client,
                stash_service=stash_service,
                settings=settings
            )
            
            # Test 1: Basic detection without AI
            logger.info("Test 1: Testing pattern-based detection")
            options = AnalysisOptions(
                detect_studios=True,
                detect_performers=True,
                detect_tags=True,
                detect_details=False,
                use_ai=False
            )
            
            # Create a mock scene for testing
            mock_scene = type('Scene', (), {
                'id': 'test-123',
                'title': 'Sean Cody - Test Scene',
                'path': '/videos/SeanCody/SC1234_Test_Scene.mp4',
                'details': '',
                'duration': 1200,
                'width': 1920,
                'height': 1080,
                'frame_rate': 30,
                'performers': [],
                'tags': [],
                'studio': None
            })()
            
            changes = await analysis_service.analyze_single_scene(mock_scene, options)
            
            logger.info(f"Found {len(changes)} changes:")
            for change in changes:
                logger.info(f"  - {change.field}: {change.proposed_value} (confidence: {change.confidence})")
            
            # Test 2: AI-based detection
            logger.info("\nTest 2: Testing AI-based detection")
            options.use_ai = True
            options.detect_details = True
            
            changes = await analysis_service.analyze_single_scene(mock_scene, options)
            
            logger.info(f"Found {len(changes)} changes with AI:")
            for change in changes:
                logger.info(f"  - {change.field}: {change.proposed_value[:50]}... (confidence: {change.confidence})")
            
            # Test 3: Batch processing
            logger.info("\nTest 3: Testing batch processing")
            
            # Get some actual scenes from Stash
            scenes_data = await stash_service.find_scenes({"per_page": 5})
            
            if scenes_data:
                logger.info(f"Analyzing {len(scenes_data)} scenes from Stash")
                
                # Convert to scene objects
                scenes = []
                for data in scenes_data:
                    scene = type('Scene', (), {
                        'id': data.get('id'),
                        'title': data.get('title', ''),
                        'path': data.get('path', data.get('file', {}).get('path', '')),
                        'details': data.get('details', ''),
                        'duration': data.get('file', {}).get('duration', 0),
                        'width': data.get('file', {}).get('width', 0),
                        'height': data.get('file', {}).get('height', 0),
                        'frame_rate': data.get('file', {}).get('frame_rate', 0),
                        'performers': data.get('performers', []),
                        'tags': data.get('tags', []),
                        'studio': data.get('studio')
                    })()
                    scenes.append(scene)
                
                # Analyze with plan creation
                plan = await analysis_service.analyze_scenes(
                    scene_ids=[s.id for s in scenes],
                    options=options,
                    db=db
                )
                
                if plan:
                    logger.info(f"Created analysis plan: {plan.name}")
                    logger.info(f"Plan ID: {plan.id}")
                    logger.info(f"Total changes: {plan.get_metadata('total_changes', 0)}")
                    
                    stats = plan.get_metadata('statistics', {})
                    logger.info(f"Statistics: {stats}")
            else:
                logger.warning("No scenes found in Stash")
            
            # Test 4: Cost estimation
            logger.info("\nTest 4: Testing cost estimation")
            
            # Estimate tokens for a sample prompt
            sample_text = "This is a sample scene description " * 100
            tokens = analysis_service.ai_client.estimate_tokens(sample_text)
            cost = analysis_service.ai_client.estimate_cost(
                prompt_tokens=tokens,
                completion_tokens=100
            )
            
            logger.info(f"Estimated tokens: {tokens}")
            logger.info(f"Estimated cost for 100 scenes: ${cost * 100:.4f}")
            
        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
        finally:
            await db.close()
    
    # Cleanup
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_analysis_service())