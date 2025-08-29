# Implementation Plan: Daemon Status Updates

## Overview
This plan outlines the step-by-step implementation of status reporting for all existing daemons based on the system described in `plans/daemons-status-updates.md`.

## Implementation Order & Priority

### Phase 1: High-Impact Daemons (User-Facing)

#### 1. AutoVideoAnalysisDaemon
**Priority: HIGH** - Most visible to users, processes many items
**Estimated Time: 30 minutes**

**Implementation Steps:**
```python
# Key locations to add status updates:

# 1. In _check_and_analyze_scenes():
await self.update_status("Checking for scenes needing video analysis")
# After counting scenes:
await self.update_status(f"Found {total_pending} scenes needing analysis")

# 2. When processing batches:
await self.update_status(f"Processing batch {self._batch_counter} of {total_batches} ({batch_size} scenes)")

# 3. When creating analysis job:
await self.update_status(
    f"Analyzing video tags for {len(scene_ids)} scenes",
    job_id=str(job.id),
    job_type=JobType.ANALYSIS.value
)

# 4. When monitoring job:
await self.update_status("Waiting for video analysis to complete")

# 5. When applying plan:
await self.update_status(
    f"Applying analysis plan {plan_id}",
    job_id=str(apply_job.id),
    job_type=JobType.APPLY_PLAN.value
)

# 6. When sleeping:
await self.update_status(f"No scenes to analyze, sleeping for {config['job_interval_seconds']} seconds")
```

#### 2. AutoStashSyncDaemon
**Priority: HIGH** - Critical for data consistency
**Estimated Time: 20 minutes**

**Implementation Steps:**
```python
# Key locations to add status updates:

# 1. In _check_and_sync_scenes():
await self.update_status("Checking for scenes to sync from Stash")

# 2. After checking pending scenes:
if pending_count > 0:
    await self.update_status(f"Found {pending_count} scenes needing sync")
else:
    await self.update_status(f"No pending scenes, sleeping for {config['job_interval_seconds']} seconds")

# 3. When creating sync job:
await self.update_status(
    f"Syncing {pending_count} scenes from Stash",
    job_id=str(job.id),
    job_type=JobType.SYNC.value
)

# 4. When monitoring sync:
await self.update_status("Waiting for sync to complete")

# 5. After sync completes:
await self.update_status(f"Sync completed for {scenes_synced} scenes")
```

### Phase 2: Processing Daemons

#### 3. AutoPlanApplierDaemon
**Priority: MEDIUM** - Applies analysis results
**Estimated Time: 25 minutes**

**Implementation Steps:**
```python
# Key locations to add status updates:

# 1. In _process_plans():
await self.update_status("Checking for plans to apply")

# 2. After retrieving plans:
await self.update_status(f"Found {len(plans)} plans in DRAFT/REVIEWING status")

# 3. When filtering plans:
await self.update_status(f"Filtering {len(plans)} plans by prefix: {prefix_filter}")

# 4. When processing each plan:
await self.update_status(f"Processing plan: {plan.name}")

# 5. When checking for changes:
await self.update_status(f"Plan {plan.id} has {change_count} changes to apply")

# 6. When applying plan:
await self.update_status(
    f"Applying plan {plan.id}: {plan.name}",
    job_id=str(job.id),
    job_type=JobType.APPLY_PLAN.value
)

# 7. When waiting for completion:
await self.update_status(f"Waiting for plan {plan.id} to complete")

# 8. When no plans found:
await self.update_status(f"No plans to process, sleeping for {config['job_interval_seconds']} seconds")
```

#### 4. DownloadProcessorDaemon
**Priority: MEDIUM** - Handles new content
**Estimated Time: 20 minutes**

**Implementation Steps:**
```python
# Key locations to add status updates:

# 1. In _check_and_process_downloads():
await self.update_status("Checking qBittorrent for new downloads")

# 2. After checking downloads:
if has_downloads:
    await self.update_status(f"Found {download_count} new downloads to process")
else:
    await self.update_status(f"No new downloads, sleeping for {config['job_interval_seconds']} seconds")

# 3. When creating process job:
await self.update_status(
    f"Processing {download_count} downloads",
    job_id=str(job.id),
    job_type=JobType.PROCESS_DOWNLOADS.value
)

# 4. When monitoring process job:
await self.update_status("Waiting for download processing to complete")

# 5. When creating scan job:
await self.update_status(
    "Triggering Stash metadata scan",
    job_id=str(scan_job.id),
    job_type=JobType.STASH_SCAN.value
)

# 6. When monitoring scan:
await self.update_status("Waiting for metadata scan to complete")
```

### Phase 3: Background Daemons

#### 5. AutoStashGenerationDaemon
**Priority: LOW** - Background metadata generation
**Estimated Time: 25 minutes**

**Implementation Steps:**
```python
# Key locations to add status updates:

# 1. In _check_for_running_jobs():
await self.update_status("Checking for running jobs")
if has_jobs:
    await self.update_status(f"Found {len(jobs)} running jobs, sleeping for {config['job_interval_seconds']} seconds")

# 2. In _check_for_ungenerated_scenes():
await self.update_status("Checking for scenes needing generation")
if not has_ungenerated:
    await self.update_status(f"All scenes generated, sleeping for {config['job_interval_seconds']} seconds")

# 3. When starting generation:
await self.update_status(
    f"Starting metadata generation",
    job_id=str(job.id),
    job_type=JobType.STASH_GENERATE.value
)

# 4. When monitoring generation:
await self.update_status("Generating metadata for scenes")

# 5. When scan jobs detected:
await self.update_status(f"Cancelling generation due to {len(scan_jobs)} scan jobs")

# 6. After generation completes:
await self.update_status("Metadata generation completed")
```

## Testing Plan

### Phase 4: Testing & Validation
**Estimated Time: 1 hour**

#### Test Scenarios for Each Daemon:

1. **Startup Test**
   - Start daemon
   - Verify initial status appears within 2 seconds
   - Check status shows "Checking for..." message

2. **Active Processing Test**
   - Trigger work for daemon (add scenes, create plans, etc.)
   - Verify status updates show processing details
   - Confirm job links appear when applicable
   - Check status updates are frequent (at least every 30 seconds)

3. **Idle State Test**
   - Let daemon complete all work
   - Verify status shows "sleeping for X seconds"
   - Confirm status remains visible during idle periods

4. **Job Monitoring Test**
   - When daemon creates a job
   - Verify job_id and job_type appear in status
   - Click "View Job" link to confirm it works
   - Check status updates during job monitoring

5. **Error Handling Test**
   - Cause an error condition
   - Verify status still updates appropriately
   - Confirm daemon recovers and continues updating status

6. **Stop Test**
   - Stop daemon
   - Verify status clears immediately
   - Confirm no stale status remains

### WebSocket Testing:
1. Open Daemons page in multiple browser tabs
2. Start/stop daemons and verify all tabs update
3. Check network tab for WebSocket messages
4. Verify no excessive network traffic

## Implementation Checklist

### Pre-Implementation:
- [ ] Review current daemon code structure
- [ ] Identify all long-running operations
- [ ] Plan status message wording for consistency
- [ ] Ensure test environment is ready

### Per-Daemon Checklist:
For each daemon:
- [ ] Add status updates at identified locations
- [ ] Include job details where applicable
- [ ] Test startup behavior
- [ ] Test processing behavior
- [ ] Test idle behavior
- [ ] Test error scenarios
- [ ] Verify WebSocket updates
- [ ] Check UI display formatting
- [ ] Review status message clarity

### Post-Implementation:
- [ ] Run all daemons simultaneously
- [ ] Verify no performance degradation
- [ ] Check database for proper status storage
- [ ] Test with multiple browser sessions
- [ ] Document any issues or edge cases
- [ ] Update daemon documentation if needed

## Code Templates

### Basic Status Update:
```python
await self.update_status("Clear description of current activity")
```

### Status with Job Information:
```python
await self.update_status(
    "Processing description",
    job_id=str(job.id),
    job_type=JobType.EXAMPLE.value
)
```

### Status Before Sleep:
```python
await self.update_status(f"Idle message, sleeping for {interval} seconds")
await asyncio.sleep(interval)
```

### Status with Progress:
```python
for i, item in enumerate(items, 1):
    await self.update_status(f"Processing item {i} of {len(items)}: {item.name}")
    # Process item...
```

## Common Patterns

### Pattern 1: Check-Process-Sleep Loop
```python
while self.is_running:
    await self.update_status("Checking for work")
    work = await self._get_work()
    
    if not work:
        await self.update_status(f"No work found, sleeping for {interval} seconds")
        await asyncio.sleep(interval)
        continue
    
    await self.update_status(f"Processing {len(work)} items")
    # Process work...
```

### Pattern 2: Job Creation and Monitoring
```python
# Create job
job = await create_job(...)
await self.update_status(
    f"Running job for {description}",
    job_id=str(job.id),
    job_type=job.type
)

# Monitor job
while job.status == "RUNNING":
    await self.update_status(f"Waiting for job to complete ({elapsed}s)")
    await asyncio.sleep(5)

await self.update_status(f"Job completed: {job.result}")
```

### Pattern 3: Batch Processing
```python
total_batches = (total_items + batch_size - 1) // batch_size
for batch_num in range(1, total_batches + 1):
    await self.update_status(
        f"Processing batch {batch_num} of {total_batches} ({batch_size} items)"
    )
    # Process batch...
```

## Success Criteria

1. **Visibility**: Users can see what each daemon is doing at all times
2. **Clarity**: Status messages are clear and informative
3. **Performance**: No noticeable performance impact
4. **Reliability**: Status updates even during errors
5. **Consistency**: Similar operations use similar language
6. **Integration**: Job links work and provide value

## Rollback Plan

If issues arise:
1. Status updates can be disabled by commenting out `update_status` calls
2. The system is backward compatible - daemons work without status updates
3. Database fields can be safely ignored if not used
4. WebSocket broadcasting fails gracefully

## Timeline

- **Phase 1**: 50 minutes (2 high-priority daemons)
- **Phase 2**: 45 minutes (2 medium-priority daemons)
- **Phase 3**: 25 minutes (1 low-priority daemon)
- **Phase 4**: 60 minutes (comprehensive testing)
- **Total**: ~3 hours

## Notes

- Start with AutoVideoAnalysisDaemon as it's most visible to users
- Test each daemon individually before moving to the next
- Keep status messages concise but informative
- Always include job information when available
- Update frequently during long operations (every 30-60 seconds minimum)
- Consider adding configuration options to control status verbosity in future