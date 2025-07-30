# Smoother Workflow Step Progress Implementation Plan

## Overview

This document describes how to implement smoother progress reporting within workflow job steps. Currently, workflow jobs like `process_new_scenes` use fixed progress percentages for each step (e.g., Step 1 stays at 5% until Step 2 jumps to 20%). This enhancement would make progress advance smoothly within each step based on sub-job progress.

## Current Implementation

### How It Works Now

The `process_new_scenes` workflow currently uses manual weighted progress:

```python
# Step 1: 5% (stays at 5% during entire download processing)
await progress_callback(5, "Step 1/6: Processing downloads")

# Step 2: 20% (jumps from 5% to 20%)
await progress_callback(20, f"Step 2/6: Scanning metadata ({synced_items} new items)")

# Step 3: 35% (jumps from 20% to 35%)
await progress_callback(35, "Step 3/6: Running incremental sync")

# And so on...
```

### Sub-job Progress Monitoring

When monitoring sub-jobs, the current implementation correctly avoids updating the parent progress percentage:

```python
# In _create_and_run_subjob
await progress_callback(
    None,  # Don't change progress
    f"{step_name}: {job_metadata.get('message', 'In progress...')}",
)
```

## Proposed Enhancement

### Goal

Make progress advance smoothly within each step based on the sub-job's actual progress. For example:
- Step 1 (Process Downloads): Progress from 5% to 20% as the download job progresses
- Step 2 (Stash Scan): Progress from 20% to 35% as the scan progresses
- And so on...

### Implementation Approach

#### 1. Update the step_progress_callback

The foundation is already in place but unused:

```python
async def step_progress_callback(
    progress: Optional[int], message: Optional[str]
) -> None:
    """Calculate weighted progress based on current step."""
    if progress is not None and current_step_info["step"] > 0:
        # Calculate weighted progress within the current step's range
        step_start = current_step_info["step_start"]
        step_end = current_step_info["step_end"]
        step_range = step_end - step_start
        weighted_progress = int(step_start + (progress / 100.0) * step_range)
        await progress_callback(weighted_progress, message)
    else:
        # Just pass through the message
        await progress_callback(progress, message)
```

#### 2. Modify Sub-job Monitoring

Update `_create_and_run_subjob` to use the weighted calculation:

```python
# Instead of:
await progress_callback(
    None,  # Don't change progress
    f"{step_name}: {job_metadata.get('message', 'In progress...')}",
)

# Use:
# Calculate weighted progress based on sub-job progress
sub_progress = int(sub_job.progress or 0)
if step_info and "current_step" in step_info:
    step_num = step_info["current_step"]
    if step_num in STEP_WEIGHTS:
        step_start, step_end = STEP_WEIGHTS[step_num]
        step_range = step_end - step_start
        weighted_progress = int(step_start + (sub_progress / 100.0) * step_range)
        await progress_callback(
            weighted_progress,
            f"{step_name}: {job_metadata.get('message', 'In progress...')}",
        )
else:
    # Fallback to message-only update
    await progress_callback(
        None,
        f"{step_name}: {job_metadata.get('message', 'In progress...')}",
    )
```

#### 3. Update Workflow Steps

Before each step, set the current step number:

```python
# Step 1: Process downloads
set_current_step(1)
await progress_callback(5, "Step 1/6: Processing downloads")  # Initial progress
synced_items = await _process_downloads_step(
    job_service,
    job_id,
    step_progress_callback,  # Use step_progress_callback instead
    cancellation_token,
    workflow_result,
)

# Step 2: Stash metadata scan
set_current_step(2)
await progress_callback(20, f"Step 2/6: Scanning metadata ({synced_items} new items)")
# ... and so on
```

#### 4. Pass step_progress_callback to Sub-job Creation

Modify `_run_workflow_step` to accept and use `step_progress_callback`:

```python
async def _run_workflow_step(
    job_service: JobService,
    job_type: JobType,
    metadata: Dict[str, Any],
    parent_job_id: str,
    step_name: str,
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    workflow_result: Dict[str, Any],
    result_key: str,
    step_info: Optional[Dict[str, Any]] = None,
    use_step_progress: bool = True,  # New parameter
) -> Optional[Dict[str, Any]]:
    """Run a workflow step and update results."""
    # Use step_progress_callback if enabled
    callback = step_progress_callback if use_step_progress else progress_callback
    
    result = await _create_and_run_subjob(
        job_service,
        job_type,
        metadata,
        parent_job_id,
        step_name,
        callback,  # Pass the appropriate callback
        cancellation_token,
        step_info,
    )
    # ... rest of function
```

### Example Progress Flow

With this implementation, the progress would flow like:

1. **Step 1 (Downloads)**: 5% → 8% → 12% → 15% → 18% → 20%
2. **Step 2 (Scan)**: 20% → 23% → 27% → 30% → 33% → 35%
3. **Step 3 (Sync)**: 35% → 38% → 41% → 43% → 45%
4. **Step 4 (Analysis)**: 45% → 55% → 65% → 75% → 80%
5. **Step 5 (Generate)**: 80% → 85% → 90% → 93% → 95%
6. **Completion**: 95% → 100%

### Benefits

1. **Smoother UX**: Users see continuous progress instead of jumps
2. **Better Feedback**: Progress reflects actual work being done
3. **More Accurate**: Progress bar better represents workflow completion
4. **No Resets**: Progress still only moves forward

### Considerations

1. **Batch Processing**: For steps that process multiple batches (like analysis), the progress calculation needs to account for both the batch number and the progress within each batch.

2. **Quick Steps**: Some steps might complete so quickly that smooth progress isn't noticeable.

3. **Error Handling**: If a sub-job fails, the progress should stop at the current percentage, not jump to the end of the step range.

### Testing

1. **Unit Tests**: Test the weighted progress calculation with various inputs
2. **Integration Tests**: Verify progress flows smoothly through all steps
3. **UI Tests**: Ensure the progress bar updates smoothly without jumps
4. **Edge Cases**: Test with failing sub-jobs, cancelled workflows, etc.

### Implementation Priority

This is a **nice-to-have** enhancement. The current implementation already solves the main issue (progress bar resets) by using fixed percentages. This enhancement would improve the user experience but is not critical for functionality.

### Estimated Effort

- **Development**: 2-4 hours
- **Testing**: 1-2 hours
- **Total**: 3-6 hours

### Alternative Approach

If the above approach proves complex, a simpler alternative is to just interpolate progress at fixed intervals:

```python
# In sub-job monitoring, update progress every 20% of sub-job completion
if sub_progress % 20 == 0:  # At 20%, 40%, 60%, 80%, 100%
    interpolated = step_start + (sub_progress / 100.0) * (step_end - step_start)
    await progress_callback(int(interpolated), message)
```

This would give less smooth but still improved progress updates.