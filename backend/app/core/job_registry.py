"""
Centralized job type registry.

This module provides a single source of truth for all job type definitions,
metadata, and configuration. It eliminates the need to update multiple
locations when adding new job types.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class JobMetadata:
    """Metadata for a job type."""

    # Core properties
    value: str  # Enum value (e.g., "sync_scenes")
    label: str  # Display name (e.g., "Sync Scenes")
    description: str  # Detailed description

    # UI properties
    color: str  # Color for UI display (e.g., "blue", "green")
    icon: Optional[str] = None  # Icon name for UI
    category: Optional[str] = None  # Category for grouping

    # Progress display
    unit: Optional[str] = None  # Unit for progress (e.g., "scenes", "files")
    unit_singular: Optional[str] = None  # Singular form of unit

    # Schema mapping
    schema_name: Optional[str] = None  # Override for schema enum if different

    # Execution properties
    allow_concurrent: bool = False  # Whether multiple instances can run
    is_workflow: bool = False  # Whether this is a workflow job

    @property
    def schema_value(self) -> str:
        """Get the schema enum value."""
        return self.schema_name or self.value


# Define all job types and their metadata in one place
JOB_REGISTRY: Dict[str, JobMetadata] = {
    # Synchronization Jobs
    "SYNC": JobMetadata(
        value="sync",
        label="Sync",
        description="Synchronize all data with Stash",
        color="blue",
        category="Synchronization",
        unit="items",
    ),
    "SYNC_SCENES": JobMetadata(
        value="sync_scenes",
        label="Sync Scenes",
        description="Synchronize specific scenes with Stash",
        color="blue",
        category="Synchronization",
        unit="scenes",
        allow_concurrent=True,
    ),
    # Analysis Jobs
    "ANALYSIS": JobMetadata(
        value="analysis",
        label="Scene Analysis",
        description="Analyze scenes with AI",
        color="green",
        category="AI Analysis",
        unit="scenes",
        schema_name="scene_analysis",  # Different schema name
        allow_concurrent=True,
    ),
    "NON_AI_ANALYSIS": JobMetadata(
        value="non_ai_analysis",
        label="Non-AI Analysis",
        description="Analyze scenes without AI (faster detection)",
        color="lime",
        category="Analysis",
        unit="scenes",
        allow_concurrent=True,
    ),
    "APPLY_PLAN": JobMetadata(
        value="apply_plan",
        label="Apply Plan",
        description="Apply analysis plan changes",
        color="purple",
        category="AI Analysis",
        unit="changes",
        allow_concurrent=True,
    ),
    "GENERATE_DETAILS": JobMetadata(
        value="generate_details",
        label="Generate Details",
        description="Generate scene details with AI",
        color="orange",
        category="AI Analysis",
        unit="scenes",
        allow_concurrent=True,
    ),
    # Stash Operations
    "STASH_SCAN": JobMetadata(
        value="stash_scan",
        label="Stash Metadata Scan",
        description="Scan and update metadata in Stash library",
        color="volcano",
        category="Stash Operations",
        unit="files",
    ),
    "STASH_GENERATE": JobMetadata(
        value="stash_generate",
        label="Stash Generate Metadata",
        description="Generate preview images, sprites, and metadata for media files",
        color="geekblue",
        category="Stash Operations",
        unit="items",
    ),
    "CHECK_STASH_GENERATE": JobMetadata(
        value="check_stash_generate",
        label="Check Resource Generation",
        description="Check for resources requiring generation in Stash",
        color="orange",
        category="Stash Operations",
        unit="resources",
    ),
    "LOCAL_GENERATE": JobMetadata(
        value="local_generate",
        label="Local Generate",
        description="Locally generate marker previews and screenshots for a single scene",
        color="cyan",
        category="Stash Operations",
        unit="markers",
        allow_concurrent=True,
    ),
    # Workflow Jobs
    "PROCESS_DOWNLOADS": JobMetadata(
        value="process_downloads",
        label="Process Downloads",
        description="Process downloaded content",
        color="geekblue",
        category="Workflow",
        unit="downloads",
    ),
    "PROCESS_NEW_SCENES": JobMetadata(
        value="process_new_scenes",
        label="Process New Scenes",
        description="Complete workflow to process newly downloaded scenes through scanning, analysis, and metadata generation",
        color="purple",
        category="Workflow",
        unit="steps",
        is_workflow=True,
    ),
    # Maintenance Jobs
    "CLEANUP": JobMetadata(
        value="cleanup",
        label="Cleanup",
        description="Clean up old jobs, stuck plans, and download logs",
        color="magenta",
        category="Maintenance",
    ),
    "REMOVE_ORPHANED_ENTITIES": JobMetadata(
        value="remove_orphaned_entities",
        label="Remove Orphaned Entities",
        description="Remove scenes, tags, performers, and studios that no longer exist in Stash",
        color="red",
        category="Maintenance",
        unit="entities",
        allow_concurrent=False,
    ),
    # Import/Export
    "EXPORT": JobMetadata(
        value="export",
        label="Export",
        description="Export data",
        color="cyan",
        category="Data Management",
    ),
    "IMPORT": JobMetadata(
        value="import",
        label="Import",
        description="Import data",
        color="cyan",
        category="Data Management",
    ),
    # Testing
    "TEST": JobMetadata(
        value="test",
        label="Test Job",
        description="Test job demonstrating daemon job orchestration",
        color="cyan",
        category="Testing",
        unit="test steps",
    ),
    # Legacy/Compatibility entries
    "SCENE_SYNC": JobMetadata(
        value="scene_sync",
        label="Scene Sync",
        description="Synchronize scenes with Stash",
        color="blue",
        category="Synchronization",
        unit="scenes",
        schema_name="scene_sync",
    ),
    "SCENE_ANALYSIS": JobMetadata(
        value="scene_analysis",
        label="Scene Analysis",
        description="Analyze scenes with AI",
        color="green",
        category="AI Analysis",
        unit="scenes",
        schema_name="scene_analysis",
    ),
    "SETTINGS_TEST": JobMetadata(
        value="settings_test",
        label="Settings Test",
        description="Test system settings",
        color="purple",
        category="Testing",
    ),
}


def get_job_metadata(job_type: str) -> Optional[JobMetadata]:
    """
    Get metadata for a job type.

    Args:
        job_type: The job type value (e.g., "sync_scenes")

    Returns:
        JobMetadata if found, None otherwise
    """
    # Try direct lookup first
    if job_type.upper() in JOB_REGISTRY:
        return JOB_REGISTRY[job_type.upper()]

    # Try by value
    for metadata in JOB_REGISTRY.values():
        if metadata.value == job_type:
            return metadata

    return None


def get_all_job_types() -> List[str]:
    """Get all registered job type values."""
    return [meta.value for meta in JOB_REGISTRY.values()]


def get_all_schema_types() -> List[str]:
    """Get all schema enum values."""
    seen = set()
    result = []
    for meta in JOB_REGISTRY.values():
        schema_value = meta.schema_value
        if schema_value not in seen:
            seen.add(schema_value)
            result.append(schema_value)
    return result


def get_job_type_mapping() -> Dict[str, str]:
    """
    Get mapping from model job types to schema job types.

    Returns:
        Dict mapping model values to schema values
    """
    mapping = {}
    for meta in JOB_REGISTRY.values():
        if meta.schema_name and meta.schema_name != meta.value:
            mapping[meta.value] = meta.schema_name
        else:
            mapping[meta.value] = meta.value
    return mapping


def validate_job_type(job_type: str) -> bool:
    """
    Validate if a job type is registered.

    Args:
        job_type: The job type to validate

    Returns:
        True if valid, False otherwise
    """
    return get_job_metadata(job_type) is not None


def get_job_categories() -> Dict[str, List[JobMetadata]]:
    """
    Get all job types grouped by category.

    Returns:
        Dict mapping category names to lists of job metadata
    """
    categories: Dict[str, List[JobMetadata]] = {}
    for meta in JOB_REGISTRY.values():
        category = meta.category or "Other"
        if category not in categories:
            categories[category] = []
        categories[category].append(meta)
    return categories


def to_api_response() -> Dict:
    """
    Convert registry to API response format.

    Returns:
        Dict suitable for JSON API response
    """
    return {
        "job_types": [
            {
                "value": meta.value,
                "label": meta.label,
                "description": meta.description,
                "color": meta.color,
                "icon": meta.icon,
                "category": meta.category,
                "unit": meta.unit,
                "unit_singular": meta.unit_singular,
                "schema_value": meta.schema_value,
                "allow_concurrent": meta.allow_concurrent,
                "is_workflow": meta.is_workflow,
            }
            for meta in JOB_REGISTRY.values()
        ],
        "categories": list(get_job_categories().keys()),
    }


# Create dynamic enums based on registry
def create_model_enum():
    """Create model JobType enum from registry."""
    from enum import Enum as StdEnum

    class JobType(str, StdEnum):
        """Dynamic JobType enum for models."""

        pass

    for key, meta in JOB_REGISTRY.items():
        setattr(JobType, key, meta.value)

    return JobType


def create_schema_enum():
    """Create schema JobType enum from registry."""
    from enum import Enum as StdEnum

    class SchemaJobType(str, StdEnum):
        """Dynamic JobType enum for API schemas."""

        pass

    # Use a set to avoid duplicates
    seen = set()
    for meta in JOB_REGISTRY.values():
        schema_value = meta.schema_value
        if schema_value not in seen:
            seen.add(schema_value)
            # Create a valid enum name from the value
            enum_name = schema_value.upper().replace("-", "_")
            setattr(SchemaJobType, enum_name, schema_value)

    return SchemaJobType
