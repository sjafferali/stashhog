#!/usr/bin/env python3
"""Test enum value behavior."""

from app.models.job import JobType

# Test the enum value
print(f"JobType.VIDEO_TAG_ANALYSIS = {JobType.VIDEO_TAG_ANALYSIS}")
print(f"JobType.VIDEO_TAG_ANALYSIS.value = {JobType.VIDEO_TAG_ANALYSIS.value}")
print(f"JobType.VIDEO_TAG_ANALYSIS.name = {JobType.VIDEO_TAG_ANALYSIS.name}")

# Check if it has value attribute
print(f"hasattr(JobType.VIDEO_TAG_ANALYSIS, 'value') = {hasattr(JobType.VIDEO_TAG_ANALYSIS, 'value')}")

# Test what gets passed to the repository
job_type = JobType.VIDEO_TAG_ANALYSIS
print(f"\nWhen passed as job_type:")
print(f"job_type = {job_type}")
print(f"job_type.value = {job_type.value}")
print(f"str(job_type) = {str(job_type)}")