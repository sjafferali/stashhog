# Backend Test Coverage Task List

This document tracks the progress of increasing backend test coverage, focusing on one file at a time. Each task represents a specific test file to create or enhance. After each test creation task, we run all tests to ensure nothing breaks.

## Instructions for Maintaining This Document

1. After completing a task, mark it as `[x]` instead of `[ ]`
2. Add the date completed next to the task
3. Update the coverage percentage after running tests
4. Add any notes about issues encountered or additional tests needed
5. Keep the current coverage metrics updated at the top

## Current Coverage Status

- **Current Coverage**: ~81% overall (improved from 26%)
- **Target Coverage**: 80%+ (ACHIEVED! 🎉)
- **Last Updated**: 2025-07-22
- **Files Completed Today**: tag_repository.py (100%), scene_service.py (96%), settings_loader.py (100%), openai_client.py (100%), debug.py (improved), scene_sync.py (87%), analysis.py (improved), jobs.py (improved), core/exceptions.py (100%), sync/progress.py (92%), setting.py (91%), analysis_plan.py (100%), plan_change.py (97%), job.py (93%), stash_service.py (70%)

## Test Execution Command
```bash
cd backend && python -m pytest -v --cov=app --cov-report=html --cov-report=term --cov-report=xml
```

## Coverage Report Location
- Terminal: Shows inline after test run
- HTML Report: `backend/htmlcov/index.html`
- XML Report: `backend/coverage.xml`

## Task List

### Phase 1: Critical Missing Tests - Zero Coverage Files (0% coverage)

#### Tag Repository Tests (100% coverage - app/repositories/tag_repository.py)
- [x] Task 1: Create test_tag_repository.py - Test tag CRUD operations (2025-07-22)
- [x] Task 2: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 3: Add tests for bulk tag operations and search functionality (2025-07-22)
- [x] Task 4: Run all backend tests and ensure they pass (2025-07-22)

#### Scene Service Tests (96% coverage - app/services/scene_service.py)
- [x] Task 5: Create test_scene_service.py - Test scene management service (2025-07-22)
- [x] Task 6: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 7: Add tests for scene filtering and pagination (2025-07-22) - Note: Not applicable to scene service
- [x] Task 8: Run all backend tests and ensure they pass (2025-07-22)

#### Title Generator Tests (0% coverage - app/services/analysis/title_generator.py)
- [x] Task 9: Create test_title_generator.py - Test AI-based title generation (2025-07-22) - Note: File doesn't exist
- [x] Task 10: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 11: Add tests for title formatting and edge cases (2025-07-22) - Note: File doesn't exist
- [x] Task 12: Run all backend tests and ensure they pass (2025-07-22)

### Phase 2: Very Low Coverage Files (<20% coverage)

#### Settings Loader Tests (100% coverage - app/core/settings_loader.py)
- [x] Task 13: Create test_settings_loader.py - Test settings loading mechanism (2025-07-22)
- [x] Task 14: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 15: Add tests for environment variable parsing and validation (2025-07-22)
- [x] Task 16: Run all backend tests and ensure they pass (2025-07-22)

#### OpenAI Client Tests (100% coverage - app/services/openai_client.py)
- [x] Task 17: Create test_openai_client.py - Test OpenAI API wrapper (2025-07-22)
- [x] Task 18: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 19: Add tests for retry logic and error handling (2025-07-22)
- [x] Task 20: Run all backend tests and ensure they pass (2025-07-22)

#### Debug Routes Tests (improved coverage - app/api/routes/debug.py)
- [x] Task 21: Create test_api_routes_test.py - Test development/debugging endpoints (2025-07-22)
- [x] Task 22: Run all backend tests and ensure they pass (2025-07-22)

### Phase 3: Low Coverage Core Services (<40% coverage)

#### Scene Sync Tests (87% coverage - app/services/sync/scene_sync.py)
- [x] Task 23: Enhance test_scene_sync.py - Add comprehensive sync logic tests (2025-07-22)
- [x] Task 24: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 25: Add tests for conflict resolution and merge strategies (2025-07-22) - Note: Already had comprehensive tests
- [x] Task 26: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 27: Add tests for batch sync operations (2025-07-22) - Note: Added as part of Task 23
- [x] Task 28: Run all backend tests and ensure they pass (2025-07-22)

### Phase 4: API Routes with Low Coverage (<60% coverage)

#### Analysis Routes Tests (40% coverage - app/api/routes/analysis.py)
- [x] Task 29: Enhance test_api_routes_analysis.py - Add batch operation tests (2025-07-22)
- [x] Task 30: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 31: Add tests for cost estimation endpoints (2025-07-22)
- [x] Task 32: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 33: Add tests for analysis plan preview functionality (2025-07-22)
- [x] Task 34: Run all backend tests and ensure they pass (2025-07-22)

#### Jobs Routes Tests (51% coverage - app/api/routes/jobs.py)
- [x] Task 35: Enhance test_api_routes_jobs.py - Add job lifecycle tests (2025-07-22)
- [x] Task 36: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 37: Add tests for job cancellation and retry functionality (2025-07-22)
- [x] Task 38: Run all backend tests and ensure they pass (2025-07-22)

### Phase 5: Core Infrastructure (<60% coverage)

#### Core Exceptions Tests (46% coverage - app/core/exceptions.py)
- [x] Task 39: Create test_core_exceptions.py - Test custom exception handling (2025-07-22)
- [x] Task 40: Run all backend tests and ensure they pass (2025-07-22)

#### Sync Progress Tests (91% coverage - app/services/sync/progress.py)
- [x] Task 41: Create test_sync_progress.py - Test progress tracking (2025-07-22)
- [x] Task 42: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 43: Add tests for real-time progress updates (2025-07-22)
- [x] Task 44: Run all backend tests and ensure they pass (2025-07-22)

#### Model Setting Tests (91% coverage - app/models/setting.py)
- [x] Task 45: Create test_model_setting.py - Test setting model operations (2025-07-22)
- [x] Task 46: Run all backend tests and ensure they pass (2025-07-22)

#### Video Tag Detector Tests (94% coverage - app/services/analysis/video_tag_detector.py)
- [x] Task 47: Create test_video_tag_detector.py - Test video analysis (2025-07-22)
- [x] Task 48: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 49: Add tests for tag confidence scoring (2025-07-22)
- [x] Task 50: Run all backend tests and ensure they pass (2025-07-22)

### Phase 6: Model Tests (<60% coverage)

#### Analysis Plan Model Tests (100% coverage - app/models/analysis_plan.py)
- [x] Task 51: Create test_model_analysis_plan.py - Test plan model operations (2025-07-22)
- [x] Task 52: Run all backend tests and ensure they pass (2025-07-22)

#### Plan Change Model Tests (97% coverage - app/models/plan_change.py)
- [x] Task 53: Create test_model_plan_change.py - Test change tracking (2025-07-22)
- [x] Task 54: Run all backend tests and ensure they pass (2025-07-22)

#### Job Model Tests (93% coverage - app/models/job.py)
- [x] Task 55: Create test_model_job.py - Test job model operations (2025-07-22)
- [x] Task 56: Run all backend tests and ensure they pass (2025-07-22)

### Phase 7: Service Components (<60% coverage)

#### Stash Service Tests (85% coverage - app/services/stash_service.py)
- [x] Task 57: Enhance test_stash_service.py - Add GraphQL operation tests (2025-07-22)
- [x] Task 58: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 59: Add tests for error handling and retry logic (2025-07-22)
- [x] Task 60: Run all backend tests and ensure they pass (2025-07-22)

#### Stash Cache Tests (100% coverage - app/services/stash/cache.py)
- [x] Task 61: Create test_stash_cache.py - Test caching mechanism (2025-07-22)
- [x] Task 62: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 63: Add tests for cache invalidation and TTL (2025-07-22)
- [x] Task 64: Run all backend tests and ensure they pass (2025-07-22)

#### Stash Transformers Tests (100% coverage - app/services/stash/transformers.py)
- [x] Task 65: Create test_stash_transformers.py - Test data transformation (2025-07-22)
- [x] Task 66: Run all backend tests and ensure they pass (2025-07-22)

#### Analysis Service Tests (improved coverage - app/services/analysis/analysis_service.py)
- [x] Task 67: Create test_analysis_service.py - Test main analysis service (2025-07-22)
- [x] Task 68: Run all backend tests and ensure they pass (2025-07-22)
- [x] Task 69: Add tests for scene analysis workflow (2025-07-22)
- [x] Task 70: Run all backend tests and ensure they pass (2025-07-22)
- [ ] Task 71: Add tests for batch analysis operations
- [ ] Task 72: Run all backend tests and ensure they pass

#### Batch Processor Tests (54% coverage - app/services/analysis/batch_processor.py)
- [ ] Task 73: Create test_batch_processor.py - Test batch processing logic
- [ ] Task 74: Run all backend tests and ensure they pass
- [ ] Task 75: Add tests for batch error handling and retries
- [ ] Task 76: Run all backend tests and ensure they pass

#### Core Tasks Tests (54% coverage - app/core/tasks.py)
- [ ] Task 77: Create test_core_tasks.py - Test background task management
- [ ] Task 78: Run all backend tests and ensure they pass

#### Sync Scheduler Tests (55% coverage - app/services/sync/scheduler.py)
- [ ] Task 79: Enhance test_scheduler.py - Add scheduling logic tests
- [ ] Task 80: Run all backend tests and ensure they pass

#### Sync Service Tests (55% coverage - app/services/sync/sync_service.py)
- [ ] Task 81: Create test_sync_service_comprehensive.py - Test full sync workflow
- [ ] Task 82: Run all backend tests and ensure they pass
- [ ] Task 83: Add tests for incremental sync functionality
- [ ] Task 84: Run all backend tests and ensure they pass

### Phase 8: Additional Components (<80% coverage)

#### Main Application Tests (57% coverage - app/main.py)
- [ ] Task 85: Enhance test_main.py - Add application lifecycle tests
- [ ] Task 86: Run all backend tests and ensure they pass

#### Core Dependencies Tests (59% coverage - app/core/dependencies.py)
- [ ] Task 87: Create test_core_dependencies.py - Test dependency injection
- [ ] Task 88: Run all backend tests and ensure they pass

#### Core Logging Tests (59% coverage - app/core/logging.py)
- [ ] Task 89: Create test_core_logging.py - Test logging configuration
- [ ] Task 90: Run all backend tests and ensure they pass

#### Cost Tracker Tests (59% coverage - app/services/analysis/cost_tracker.py)
- [ ] Task 91: Create test_cost_tracker.py - Test cost calculation
- [ ] Task 92: Run all backend tests and ensure they pass

#### Core Database Tests (60% coverage - app/core/database.py)
- [ ] Task 93: Create test_core_database.py - Test database operations
- [ ] Task 94: Run all backend tests and ensure they pass

#### Job Repository Tests (66% coverage - app/repositories/job_repository.py)
- [ ] Task 95: Create test_job_repository.py - Test job data operations
- [ ] Task 96: Run all backend tests and ensure they pass

#### Sync History Model Tests (67% coverage - app/models/sync_history.py)
- [ ] Task 97: Create test_model_sync_history.py - Test sync history tracking
- [ ] Task 98: Run all backend tests and ensure they pass

#### Scene Model Tests (70% coverage - app/models/scene.py)
- [ ] Task 99: Create test_model_scene.py - Test scene model operations
- [ ] Task 100: Run all backend tests and ensure they pass

#### Scene Repository Tests (70% coverage - app/repositories/scene_repository.py)
- [ ] Task 101: Create test_scene_repository.py - Test scene data operations
- [ ] Task 102: Run all backend tests and ensure they pass

#### Core Middleware Tests (70% coverage - app/core/middleware.py)
- [ ] Task 103: Create test_core_middleware.py - Test middleware components
- [ ] Task 104: Run all backend tests and ensure they pass

#### Error Handlers Tests (71% coverage - app/api/error_handlers.py)
- [ ] Task 105: Enhance test_error_handlers.py - Add edge case tests
- [ ] Task 106: Run all backend tests and ensure they pass

#### Scenes Routes Tests (73% coverage - app/api/routes/scenes.py)
- [ ] Task 107: Enhance test_api_routes_scenes.py - Add filtering tests
- [ ] Task 108: Run all backend tests and ensure they pass

#### Tag Model Tests (77% coverage - app/models/tag.py)
- [ ] Task 109: Create test_model_tag.py - Test tag model operations
- [ ] Task 110: Run all backend tests and ensure they pass

#### Studio Model Tests (79% coverage - app/models/studio.py)
- [ ] Task 111: Create test_model_studio.py - Test studio model operations
- [ ] Task 112: Run all backend tests and ensure they pass

#### Scheduled Task Model Tests (79% coverage - app/models/scheduled_task.py)
- [ ] Task 113: Create test_model_scheduled_task.py - Test task scheduling
- [ ] Task 114: Run all backend tests and ensure they pass

#### Job Service Tests (79% coverage - app/services/job_service.py)
- [ ] Task 115: Enhance test_job_service.py - Add edge case tests
- [ ] Task 116: Run all backend tests and ensure they pass

## Completion Checklist

- [x] 70 of 116 tasks completed (60%)
- [x] Coverage target of 80% achieved (currently at 81%)
- [x] All tests passing consistently (1300+ passed, 3 skipped)
- [ ] CI/CD pipeline updated with new tests
- [ ] Test documentation updated

## Priority Order

1. **Critical Priority** (Tasks 1-22): Files with 0% or <20% coverage
2. **High Priority** (Tasks 23-38): Core services and API routes with <60% coverage
3. **Medium Priority** (Tasks 39-84): Infrastructure and service components
4. **Lower Priority** (Tasks 85-116): Files approaching 80% coverage

## Notes Section

### Files Already Well-Tested (≥80% coverage)
- app/core/config.py (98%)
- app/core/db_utils.py (100%)
- app/core/error_handlers.py (100%)
- app/core/pagination.py (100%)
- app/core/security.py (97%)
- app/services/websocket_manager.py (83%)
- app/services/analysis/models.py (89%)
- app/services/sync/models.py (96%)
- app/api/routes/settings.py (100%)
- app/api/routes/sync.py (100%)
- app/services/analysis/details_generator.py (100%)
- app/services/analysis/performer_detector.py (97%)
- app/services/analysis/studio_detector.py (94%)
- app/services/analysis/tag_detector.py (96%)
- app/services/analysis/ai_client.py (93%)
- app/services/sync/strategies.py (93%)
- app/services/sync/conflicts.py (99%)
- app/jobs/sync_jobs.py (100%)
- app/jobs/analysis_jobs.py (95%)

### Common Issues and Solutions
- Mock external API calls (Stash GraphQL, OpenAI)
- Use pytest fixtures for database setup/teardown
- Test both success and error paths
- Include edge cases and boundary conditions
- Mock WebSocket connections for real-time features
- Use transaction rollback to maintain test isolation

### Testing Best Practices
- Create comprehensive test fixtures for models
- Test API endpoints with various authentication states
- Verify database constraints and validations
- Test concurrent operations and race conditions
- Include performance tests for batch operations
- Mock all external service calls

### Application Context Update
The StashHog application has evolved to include:
- Enhanced scene file management with multiple files per scene
- Comprehensive analysis planning with bulk operations
- Advanced sync functionality with conflict resolution
- Real-time progress tracking via WebSockets
- Cost tracking for AI operations
- Scheduled task management with cron support
- Improved error handling and retry mechanisms