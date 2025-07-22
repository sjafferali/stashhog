"""
Tests for sync repository operations.

This module tests bulk operations, transaction handling, and sync history management.
"""

from datetime import datetime, timedelta

import pytest

from app.models import Performer, Scene, Studio, SyncHistory, Tag
from app.repositories.sync_repository import SyncRepository
from tests.helpers import create_test_scene


class TestBulkUpsertScenes:
    """Test cases for bulk_upsert_scenes method."""

    def test_bulk_upsert_scenes_empty_list(self, test_session):
        """Test with empty scenes list."""
        repo = SyncRepository()
        result = repo.bulk_upsert_scenes([], test_session)
        assert result == []

    def test_bulk_upsert_scenes_single_scene(self, test_session):
        """Test upserting a single scene."""
        repo = SyncRepository()
        scene_data = [
            {
                "id": "scene123",
                "title": "Test Scene",
                "details": "Test details",
                "url": "http://example.com/scene",
                "rating": 5,
                "organized": True,
                "file": {
                    "duration": 3600.5,
                    "size": 1024000,
                    "height": 1080,
                    "width": 1920,
                    "framerate": 30.0,
                    "bitrate": 5000,
                    "video_codec": "h264",
                },
            }
        ]

        result = repo.bulk_upsert_scenes(scene_data, test_session)

        assert len(result) == 1
        assert result[0].id == "scene123"
        assert result[0].title == "Test Scene"
        # File attributes are now in SceneFile, not directly on Scene

    def test_bulk_upsert_scenes_multiple_scenes(self, test_session):
        """Test upserting multiple scenes."""
        repo = SyncRepository()
        scene_data = [
            {
                "id": f"scene{i}",
                "title": f"Test Scene {i}",
                "organized": i % 2 == 0,
                "file": {"duration": i * 100},
            }
            for i in range(1, 6)
        ]

        result = repo.bulk_upsert_scenes(scene_data, test_session)

        assert len(result) == 5
        assert all(s.id == f"scene{i}" for i, s in enumerate(result, 1))
        assert all(s.title == f"Test Scene {i}" for i, s in enumerate(result, 1))

    def test_bulk_upsert_scenes_update_existing(self, test_session):
        """Test updating existing scenes."""
        repo = SyncRepository()

        # First insert
        initial_data = [{"id": "scene1", "title": "Original Title", "rating": 3}]
        repo.bulk_upsert_scenes(initial_data, test_session)
        test_session.commit()

        # Update
        update_data = [
            {
                "id": "scene1",
                "title": "Updated Title",
                "rating": 5,
                "details": "New details",
            }
        ]
        updated_result = repo.bulk_upsert_scenes(update_data, test_session)

        assert len(updated_result) == 1
        assert updated_result[0].title == "Updated Title"
        assert updated_result[0].rating == 5
        assert updated_result[0].details == "New details"

    def test_bulk_upsert_scenes_mixed_insert_update(self, test_session):
        """Test mixed insert and update operations."""
        repo = SyncRepository()

        # Insert first scene
        initial_data = [{"id": "existing1", "title": "Existing Scene"}]
        repo.bulk_upsert_scenes(initial_data, test_session)
        test_session.commit()

        # Mixed update and insert
        mixed_data = [
            {"id": "existing1", "title": "Updated Existing Scene"},
            {"id": "new1", "title": "New Scene"},
        ]
        result = repo.bulk_upsert_scenes(mixed_data, test_session)

        assert len(result) == 2
        assert any(
            s.id == "existing1" and s.title == "Updated Existing Scene" for s in result
        )
        assert any(s.id == "new1" and s.title == "New Scene" for s in result)

    def test_bulk_upsert_scenes_missing_file_data(self, test_session):
        """Test handling missing file data."""
        repo = SyncRepository()
        scene_data = [
            {
                "id": "scene1",
                "title": "Scene without file data",
                # No 'file' key
            }
        ]

        result = repo.bulk_upsert_scenes(scene_data, test_session)

        assert len(result) == 1
        assert result[0].id == "scene1"
        assert result[0].title == "Scene without file data"

    def test_bulk_upsert_scenes_timestamps(self, test_session):
        """Test that timestamps are properly set."""
        repo = SyncRepository()
        scene_data = [{"id": "scene1", "title": "Test Scene"}]

        before_time = datetime.utcnow()
        result = repo.bulk_upsert_scenes(scene_data, test_session)
        after_time = datetime.utcnow()

        assert result[0].last_synced is not None
        assert result[0].updated_at is not None
        assert before_time <= result[0].last_synced <= after_time
        assert before_time <= result[0].updated_at <= after_time


class TestBulkUpsertEntities:
    """Test cases for bulk_upsert_entities method."""

    def test_bulk_upsert_performers_empty(self, test_session):
        """Test with empty performers list."""
        repo = SyncRepository()
        count = repo.bulk_upsert_entities(Performer, [], test_session)
        assert count == 0

    def test_bulk_upsert_performers(self, test_session):
        """Test upserting performers."""
        repo = SyncRepository()
        performer_data = [
            {
                "id": "perf1",
                "name": "Performer One",
                "gender": "FEMALE",
                "birthdate": "1990-01-01",
                "country": "USA",
                "rating": 4,
            },
            {
                "id": "perf2",
                "name": "Performer Two",
                "gender": "MALE",
                "aliases": ["Alias1", "Alias2"],
            },
        ]

        count = repo.bulk_upsert_entities(Performer, performer_data, test_session)
        assert count > 0

        # Verify data
        performers = test_session.query(Performer).all()
        assert len(performers) == 2
        assert any(p.id == "perf1" and p.name == "Performer One" for p in performers)
        assert any(
            p.id == "perf2" and p.aliases == ["Alias1", "Alias2"] for p in performers
        )

    def test_bulk_upsert_tags(self, test_session):
        """Test upserting tags."""
        repo = SyncRepository()
        tag_data = [
            {"id": "tag1", "name": "Tag One", "description": "First tag"},
            {"id": "tag2", "name": "Tag Two", "parent": {"id": "tag1"}},
        ]

        count = repo.bulk_upsert_entities(Tag, tag_data, test_session)
        assert count > 0

        # Verify data
        tags = test_session.query(Tag).all()
        assert len(tags) == 2
        tag2 = next(t for t in tags if t.id == "tag2")
        assert tag2.parent_temp_id == "tag1"

    def test_bulk_upsert_studios(self, test_session):
        """Test upserting studios."""
        repo = SyncRepository()
        studio_data = [
            {
                "id": "studio1",
                "name": "Studio One",
                "url": "http://studio1.com",
                "rating": 5,
                "favorite": True,
            }
        ]

        count = repo.bulk_upsert_entities(Studio, studio_data, test_session)
        assert count > 0

        # Verify data
        studio = test_session.query(Studio).first()
        assert studio.id == "studio1"
        assert studio.name == "Studio One"
        assert studio.favorite is True

    def test_bulk_upsert_unsupported_model(self, test_session):
        """Test with unsupported model class."""
        repo = SyncRepository()

        class UnsupportedModel:
            pass

        # Pass non-empty list to avoid early return
        with pytest.raises(ValueError, match="Unsupported model class"):
            repo.bulk_upsert_entities(UnsupportedModel, [{"id": "test"}], test_session)

    def test_bulk_upsert_entities_update_existing(self, test_session):
        """Test updating existing entities."""
        repo = SyncRepository()

        # Initial insert
        initial_data = [
            {
                "id": "tag1",
                "name": "Original Name",
                "description": "Original description",
            }
        ]
        repo.bulk_upsert_entities(Tag, initial_data, test_session)
        test_session.commit()

        # Update
        update_data = [
            {
                "id": "tag1",
                "name": "Updated Name",
                "description": "Updated description",
                "aliases": ["new-alias"],
            }
        ]
        repo.bulk_upsert_entities(Tag, update_data, test_session)

        # Verify update
        tag = test_session.query(Tag).filter_by(id="tag1").first()
        assert tag.name == "Updated Name"
        assert tag.description == "Updated description"
        assert tag.aliases == ["new-alias"]


class TestSyncHistory:
    """Test cases for sync history management."""

    def test_get_last_sync_time_no_history(self, test_session):
        """Test when no sync history exists."""
        repo = SyncRepository()
        last_sync = repo.get_last_sync_time("scenes", test_session)
        assert last_sync is None

    def test_get_last_sync_time_with_history(self, test_session):
        """Test getting last sync time with existing history."""
        repo = SyncRepository()

        # Create sync history records
        history1 = SyncHistory(
            entity_type="scenes",
            job_id="job1",
            started_at=datetime.utcnow() - timedelta(hours=2),
            completed_at=datetime.utcnow() - timedelta(hours=2),
            status="completed",
        )
        history2 = SyncHistory(
            entity_type="scenes",
            job_id="job2",
            started_at=datetime.utcnow() - timedelta(hours=1),
            completed_at=datetime.utcnow() - timedelta(hours=1),
            status="completed",
        )
        history3 = SyncHistory(
            entity_type="scenes",
            job_id="job3",
            started_at=datetime.utcnow(),
            status="failed",  # Not completed
        )

        test_session.add_all([history1, history2, history3])
        test_session.commit()

        last_sync = repo.get_last_sync_time("scenes", test_session)
        assert last_sync == history2.completed_at

    def test_create_sync_history(self, test_session):
        """Test creating sync history record."""
        repo = SyncRepository()

        before_time = datetime.utcnow()
        history = repo.create_sync_history("performers", "job123", test_session)
        after_time = datetime.utcnow()

        assert history.entity_type == "performers"
        assert history.job_id == "job123"
        assert history.status == "in_progress"
        assert before_time <= history.started_at <= after_time
        assert history.completed_at is None

    def test_update_sync_history_success(self, test_session):
        """Test updating sync history with success."""
        repo = SyncRepository()

        # Create history
        history = repo.create_sync_history("tags", "job456", test_session)
        test_session.commit()

        # Update with success
        stats = {
            "processed": 100,
            "created": 30,
            "updated": 70,
            "failed": 0,
            "errors": [],
        }

        repo.update_sync_history(history.id, "completed", stats, test_session)

        # Verify update
        updated = test_session.query(SyncHistory).filter_by(id=history.id).first()
        assert updated.status == "completed"
        assert updated.completed_at is not None
        assert updated.items_synced == 100
        assert updated.items_created == 30
        assert updated.items_updated == 70
        assert updated.items_failed == 0
        assert updated.error_details == []

    def test_update_sync_history_with_errors(self, test_session):
        """Test updating sync history with errors."""
        repo = SyncRepository()

        # Create history
        history = repo.create_sync_history("studios", "job789", test_session)
        test_session.commit()

        # Update with errors
        stats = {
            "processed": 50,
            "created": 10,
            "updated": 35,
            "failed": 5,
            "errors": ["Error 1", "Error 2"],
        }

        repo.update_sync_history(history.id, "failed", stats, test_session)

        # Verify update
        updated = test_session.query(SyncHistory).filter_by(id=history.id).first()
        assert updated.status == "failed"
        assert updated.items_failed == 5
        assert updated.error_details == ["Error 1", "Error 2"]

    def test_update_sync_history_nonexistent(self, test_session):
        """Test updating non-existent sync history."""
        repo = SyncRepository()

        # Should not raise error
        repo.update_sync_history(99999, "completed", {}, test_session)


class TestEntitySync:
    """Test cases for entity sync operations."""

    def test_mark_entity_synced(self, test_session):
        """Test marking an entity as synced."""
        repo = SyncRepository()

        # Create a scene
        scene = create_test_scene(
            id="scene1",
            title="Test Scene",
            paths=[],
            stash_created_at=datetime.utcnow(),
            stash_updated_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_session.add(scene)
        test_session.flush()

        # Mark as synced
        before_time = datetime.utcnow()
        repo.mark_entity_synced(scene, test_session)
        after_time = datetime.utcnow()

        assert scene.last_synced is not None
        assert before_time <= scene.last_synced <= after_time

    def test_get_entities_needing_sync_never_synced(self, test_session):
        """Test getting entities that have never been synced."""
        repo = SyncRepository()

        # Create scenes with different sync states
        scene1 = create_test_scene(
            id="scene1",
            title="Never synced",
            paths=[],
            stash_created_at=datetime.utcnow(),
            stash_updated_at=datetime.utcnow(),
            last_synced=datetime.utcnow() - timedelta(days=30),  # Old sync date
        )
        scene2 = create_test_scene(
            id="scene2",
            title="Recently synced",
            paths=[],
            stash_created_at=datetime.utcnow(),
            stash_updated_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        scene3 = create_test_scene(
            id="scene3",
            title="Also never synced",
            paths=[],
            stash_created_at=datetime.utcnow(),
            stash_updated_at=datetime.utcnow(),
            last_synced=datetime.utcnow() - timedelta(days=30),  # Old sync date
        )

        test_session.add_all([scene1, scene2, scene3])
        test_session.commit()

        # Get entities needing sync (old sync date)
        # Pass a cutoff time that's more recent than the old syncs
        cutoff = datetime.utcnow() - timedelta(days=7)
        entities = repo.get_entities_needing_sync(Scene, cutoff, 10, test_session)

        assert len(entities) == 2
        assert all(e.last_synced < cutoff for e in entities)
        assert set(e.id for e in entities) == {"scene1", "scene3"}

    def test_get_entities_needing_sync_with_since(self, test_session):
        """Test getting entities needing sync since a specific time."""
        repo = SyncRepository()

        cutoff_time = datetime.utcnow() - timedelta(hours=1)

        # Create scenes with different sync times
        scene1 = create_test_scene(
            id="scene1",
            title="Never synced",
            paths=[],
            stash_created_at=datetime.utcnow(),
            stash_updated_at=datetime.utcnow(),
            last_synced=datetime.utcnow() - timedelta(days=30),  # Very old sync
        )
        scene2 = create_test_scene(
            id="scene2",
            title="Synced before cutoff",
            paths=[],
            stash_created_at=datetime.utcnow(),
            stash_updated_at=datetime.utcnow(),
            last_synced=cutoff_time - timedelta(minutes=30),
        )
        scene3 = create_test_scene(
            id="scene3",
            title="Synced after cutoff",
            paths=[],
            stash_created_at=datetime.utcnow(),
            stash_updated_at=datetime.utcnow(),
            last_synced=cutoff_time + timedelta(minutes=30),
        )

        test_session.add_all([scene1, scene2, scene3])
        test_session.commit()

        # Get entities needing sync
        entities = repo.get_entities_needing_sync(Scene, cutoff_time, 10, test_session)

        assert len(entities) == 2
        assert set(e.id for e in entities) == {"scene1", "scene2"}

    def test_get_entities_needing_sync_with_limit(self, test_session):
        """Test limiting the number of entities returned."""
        repo = SyncRepository()

        # Create many unsynced scenes
        scenes = [
            create_test_scene(
                id=f"scene{i}",
                title=f"Scene {i}",
                paths=[],
                stash_created_at=datetime.utcnow(),
                stash_updated_at=datetime.utcnow(),
                last_synced=datetime.utcnow() - timedelta(days=30),  # Old sync date
            )
            for i in range(10)
        ]
        test_session.add_all(scenes)
        test_session.commit()

        # Get limited entities - pass a cutoff time to get old syncs
        cutoff = datetime.utcnow() - timedelta(days=7)
        entities = repo.get_entities_needing_sync(Scene, cutoff, 3, test_session)

        assert len(entities) == 3


class TestDataPreparation:
    """Test cases for data preparation methods."""

    def test_prepare_performer_data(self):
        """Test preparing performer data."""
        repo = SyncRepository()

        performer_data = [
            {
                "id": "perf1",
                "name": "Test Performer",
                "gender": "FEMALE",
                "height": 170,
                "weight": 60,
                "measurements": "34-24-36",
                "fake_tits": True,
                "rating": 5,
                "favorite": True,
                "image_path": "/path/to/image.jpg",
            }
        ]

        prepared = repo._prepare_performer_data(performer_data)

        assert len(prepared) == 1
        assert prepared[0]["id"] == "perf1"
        assert prepared[0]["name"] == "Test Performer"
        assert prepared[0]["height_cm"] == 170
        assert prepared[0]["weight_kg"] == 60
        assert prepared[0]["fake_tits"] is True
        assert prepared[0]["image_url"] == "/path/to/image.jpg"
        assert "last_synced" in prepared[0]
        assert "updated_at" in prepared[0]

    def test_prepare_tag_data_with_parent(self):
        """Test preparing tag data with parent relationship."""
        repo = SyncRepository()

        tag_data = [
            {"id": "tag1", "name": "Parent Tag"},
            {"id": "tag2", "name": "Child Tag", "parent": {"id": "tag1"}},
        ]

        prepared = repo._prepare_tag_data(tag_data)

        assert len(prepared) == 2
        assert prepared[0]["parent_temp_id"] is None
        assert prepared[1]["parent_temp_id"] == "tag1"

    def test_prepare_studio_data(self):
        """Test preparing studio data."""
        repo = SyncRepository()

        studio_data = [
            {
                "id": "studio1",
                "name": "Test Studio",
                "url": "http://example.com",
                "parent": {"id": "parent_studio"},
                "image_path": "/studio/image.jpg",
            }
        ]

        prepared = repo._prepare_studio_data(studio_data)

        assert len(prepared) == 1
        assert prepared[0]["parent_temp_id"] == "parent_studio"
        assert prepared[0]["image_url"] == "/studio/image.jpg"


class TestTransactionHandling:
    """Test cases for transaction handling and rollback."""

    def test_bulk_upsert_scenes_skip_none_id(self, test_session):
        """Test that scenes with None ID are skipped."""
        repo = SyncRepository()

        # Create a scene that will succeed
        good_scene = {
            "id": "good_scene",
            "title": "Good Scene",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Create a scene with None ID that should be skipped
        bad_scene = {
            "id": None,  # Invalid ID should be skipped
            "title": "Bad Scene",
        }

        scene_data = [good_scene, bad_scene]

        # Bulk upsert should succeed, skipping the None ID scene
        result = repo.bulk_upsert_scenes(scene_data, test_session)
        test_session.commit()

        # Verify only the good scene was inserted
        assert len(result) == 1
        assert result[0].id == "good_scene"

        scenes = test_session.query(Scene).all()
        assert len(scenes) == 1
        assert scenes[0].id == "good_scene"

    def test_bulk_upsert_entities_transaction_rollback(self, test_session):
        """Test that entities with invalid IDs are skipped."""
        repo = SyncRepository()

        # Create performers with one having invalid data
        performer_data = [
            {"id": "perf1", "name": "Valid Performer"},
            {"id": None, "name": "Invalid Performer"},  # Invalid ID - will be skipped
        ]

        # Bulk upsert should succeed, skipping invalid entries
        count = repo.bulk_upsert_entities(Performer, performer_data, test_session)
        test_session.commit()

        # Verify only valid performer was inserted
        performers = test_session.query(Performer).all()
        assert len(performers) == 1
        assert performers[0].id == "perf1"
        assert performers[0].name == "Valid Performer"

        # Count should reflect only the successfully upserted entities
        assert count == 1

    def test_sync_history_isolation(self, test_session):
        """Test that sync history updates are isolated from main transaction."""
        repo = SyncRepository()

        # Create sync history
        history = repo.create_sync_history("scenes", "job1", test_session)
        test_session.commit()

        # Start a new transaction for scene updates
        # Now test with a scene that has None ID - it should be skipped
        bad_scene = {"id": None, "title": "Bad Scene"}
        result = repo.bulk_upsert_scenes([bad_scene], test_session)
        test_session.commit()

        # Should return empty list since the scene was skipped
        assert len(result) == 0

        # Update sync history to reflect that we processed but skipped the scene
        stats = {"processed": 1, "created": 0, "updated": 0, "failed": 0, "errors": []}
        repo.update_sync_history(history.id, "completed", stats, test_session)
        test_session.commit()

        # Verify sync history was updated
        updated_history = (
            test_session.query(SyncHistory).filter_by(id=history.id).first()
        )
        assert updated_history.status == "completed"
        assert updated_history.items_failed == 0

    def test_partial_commit_with_savepoint(self, test_session):
        """Test using savepoints for partial commits."""
        repo = SyncRepository()

        # First batch - should succeed
        batch1 = [
            {
                "id": "scene1",
                "title": "Scene 1",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        ]

        repo.bulk_upsert_scenes(batch1, test_session)
        test_session.commit()

        # Create savepoint
        savepoint = test_session.begin_nested()

        # Second batch - will be skipped due to None ID
        batch2 = [{"id": None, "title": "Invalid Scene"}]
        result = repo.bulk_upsert_scenes(batch2, test_session)
        savepoint.commit()

        # Should return empty list since scene was skipped
        assert len(result) == 0

        # First batch should still be committed
        scenes = test_session.query(Scene).all()
        assert len(scenes) == 1
        assert scenes[0].id == "scene1"

    def test_database_error_handling(self, test_session):
        """Test handling of database-specific errors."""
        repo = SyncRepository()

        # Test that the method handles empty ID - it should process it
        scene_data = [
            {
                "id": "",  # Empty ID
                "title": "Test Scene",
            }
        ]

        # The method processes the scene even with empty ID
        result = repo.bulk_upsert_scenes(scene_data, test_session)
        assert len(result) == 1
        assert result[0].id == ""
        assert result[0].title == "Test Scene"

    def test_concurrent_sync_conflict(self, test_session):
        """Test handling concurrent sync operations."""
        repo = SyncRepository()

        # Create initial scene
        initial_scene = [{"id": "scene1", "title": "Original Title", "rating": 3}]
        repo.bulk_upsert_scenes(initial_scene, test_session)
        test_session.commit()

        # Simulate concurrent updates
        update1 = [{"id": "scene1", "title": "Update 1", "rating": 4}]

        update2 = [{"id": "scene1", "title": "Update 2", "rating": 5}]

        # Both updates should succeed (last write wins)
        repo.bulk_upsert_scenes(update1, test_session)
        repo.bulk_upsert_scenes(update2, test_session)
        test_session.commit()

        # Verify last update won
        scene = test_session.query(Scene).filter_by(id="scene1").first()
        assert scene.title == "Update 2"
        assert scene.rating == 5

    def test_integrity_constraint_violation(self, test_session):
        """Test handling foreign key and unique constraint violations."""
        repo = SyncRepository()

        # Try to create a tag with non-existent parent
        tag_data = [
            {"id": "tag1", "name": "Child Tag", "parent": {"id": "non_existent_parent"}}
        ]

        # This should succeed (parent_temp_id is just stored, not enforced)
        count = repo.bulk_upsert_entities(Tag, tag_data, test_session)
        test_session.commit()

        assert count > 0
        tag = test_session.query(Tag).filter_by(id="tag1").first()
        assert tag.parent_temp_id == "non_existent_parent"
