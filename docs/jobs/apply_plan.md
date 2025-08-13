# Apply Plan Job Documentation

## Overview

The Apply Plan job (`JobType.APPLY_PLAN`) is responsible for applying approved changes from an analysis plan to the Stash database. This job takes changes that have been reviewed and approved (either manually or automatically) and executes them against the Stash API.

## Job Handler

**Function**: `apply_analysis_plan_job` in `app/jobs/analysis_jobs.py`

## Required Arguments

### Primary Parameters

- **`plan_id`** (str, required): The ID of the analysis plan to apply
- **`auto_approve`** (bool, default=False): Whether to automatically apply all approved changes
  - When `True`: Applies all changes with `status=APPROVED` or `accepted=True` 
  - When `False`: Only applies changes explicitly marked as `accepted=True`
- **`change_ids`** (list[int], optional): Specific change IDs to apply
  - If provided, only these specific changes will be applied
  - Overrides the `auto_approve` behavior

### Job Metadata Structure

```python
{
    "plan_id": "123",           # Required: Plan ID to apply
    "auto_approve": True,       # Optional: Auto-apply approved changes
    "created_by": "USER",       # Optional: Who initiated the job
    "change_ids": [1, 2, 3]     # Optional: Specific changes to apply
}
```

## Important Behaviors

### Change Selection Logic

The job uses the following logic to determine which changes to apply:

1. **If `change_ids` is provided**: Only those specific changes are applied
2. **If `auto_approve=True` and no `change_ids`**: 
   - Queries for all changes where:
     - `status == ChangeStatus.APPROVED` OR `accepted == True`
     - AND `applied == False`
   - Applies all matching changes
3. **If `auto_approve=False` and no `change_ids`**:
   - Only applies changes where `accepted == True`

### Plan Status Requirements

- Plans must be in `DRAFT` or `REVIEWING` status to be applied
- Plans in `APPLIED` status will be rejected with an error
- After successful application, the plan status is updated to `APPLIED`

## Return Value

The job returns a dictionary with the following structure:

```python
{
    "plan_id": "123",
    "applied_changes": 45,      # Number of successfully applied changes
    "failed_changes": 2,        # Number of changes that failed
    "skipped_changes": 3,       # Number of changes skipped (already applied)
    "total_changes": 50,        # Total changes attempted
    "success_rate": 90.0,       # Percentage of successful changes
    "errors": [                 # List of errors if any
        {
            "change_id": 456,
            "scene_id": "abc",
            "error": "Failed to update scene",
            "type": "application_error"
        }
    ]
}
```

## Developer Guidelines

### ⚠️ Critical Guidelines to Prevent Issues

1. **Always Check Job Type Before Re-triggering**
   ```python
   # WRONG - Can cause infinite loops
   if job.status == JobStatus.COMPLETED:
       # Don't blindly create another apply job based on result
       if job.result.get("plan_id"):
           create_apply_job(job.result["plan_id"])  # DON'T DO THIS
   
   # CORRECT - Check job type first
   if job.status == JobStatus.COMPLETED:
       if job.job_type == JobType.ANALYSIS:  # Only for analysis jobs
           if job.result.get("plan_id"):
               create_apply_job(job.result["plan_id"])
   ```

2. **Check Plan Status Before Creating Job**
   ```python
   # Always verify the plan can be applied
   plan = await db.get(AnalysisPlan, plan_id)
   if plan.status in [PlanStatus.APPLIED, PlanStatus.REVIEWING]:
       # Plan already applied or being applied - skip
       return
   ```

3. **Verify Unapplied Changes Exist**
   ```python
   # Check for unapplied approved changes before creating job
   count_query = select(func.count(PlanChange.id)).where(
       PlanChange.plan_id == plan_id,
       or_(
           PlanChange.status == ChangeStatus.APPROVED,
           PlanChange.accepted.is_(True),
       ),
       PlanChange.applied.is_(False),
   )
   unapplied_count = await db.execute(count_query).scalar_one()
   
   if unapplied_count == 0:
       # No changes to apply - mark plan as applied
       plan.status = PlanStatus.APPLIED
       await db.commit()
       return
   ```

4. **Use `auto_approve` Correctly for Automated Systems**
   ```python
   # For daemons and automated systems
   job_metadata = {
       "plan_id": str(plan_id),
       "auto_approve": True,  # Essential for automated application
       "created_by": "AUTO_VIDEO_ANALYSIS_DAEMON"
   }
   ```

5. **Handle Both Legacy and New Status Fields**
   - The system supports both `accepted` (legacy) and `status` fields
   - Always check both when determining if changes should be applied
   - UI typically sets `status=APPROVED`
   - Some older code may set `accepted=True`

### Common Pitfalls to Avoid

1. **Infinite Loop Prevention**
   - Never create an apply job from an apply job's completion handler
   - Always check the job type before processing completion results
   - Implement guards against re-applying already applied plans

2. **Missing `auto_approve` Parameter**
   - Automated systems MUST set `auto_approve=True`
   - Without it, only explicitly accepted changes (legacy field) are applied
   - This can result in jobs that run but apply 0 changes

3. **Not Checking Plan Status**
   - Always verify plan is in an applicable state (`DRAFT` or `REVIEWING`)
   - Don't attempt to apply `APPLIED` plans

4. **Ignoring Change Application State**
   - Always check `applied=False` to avoid re-applying changes
   - The system tracks which changes have been applied

## Example Usage

### Manual Apply (User-Triggered)
```python
from app.core.dependencies import get_job_service

job_service = get_job_service()
job = await job_service.create_job(
    job_type=JobType.APPLY_PLAN,
    db=db,
    metadata={
        "plan_id": "123",
        "auto_approve": False,
        "change_ids": [1, 2, 3, 4, 5],  # User selected specific changes
        "created_by": "user@example.com"
    }
)
```

### Automated Apply (Daemon)
```python
job = await job_service.create_job(
    job_type=JobType.APPLY_PLAN,
    db=db,
    metadata={
        "plan_id": str(plan_id),
        "auto_approve": True,  # Apply all approved changes
        "created_by": "AUTO_VIDEO_ANALYSIS_DAEMON"
    }
)
```

### Bulk Apply Multiple Plans
```python
job = await job_service.create_job(
    job_type=JobType.APPLY_PLAN,
    db=db,
    metadata={
        "bulk_apply": True,
        "plans_to_apply": [123, 124, 125],
        "auto_approve": True,
        "created_by": "BULK_OPERATIONS"
    }
)
```

## Integration Points

### Auto Video Analysis Daemon
- Creates apply jobs after analysis completes
- Sets `auto_approve=True` for automatic application
- Monitors job completion but doesn't re-trigger on apply job completion

### Web UI
- Creates apply jobs when user clicks "Apply" button
- May specify specific `change_ids` based on user selection
- Typically sets `auto_approve=False` for manual review

### API Endpoints
- `/api/analysis/plans/{plan_id}/apply` endpoint creates these jobs
- Handles both auto-approve and manual selection modes

## Monitoring and Debugging

### Key Log Messages
- `"Starting apply_analysis_plan job {job_id} for plan {plan_id}"`
- `"No approved changes found for plan {plan_id}"` - Indicates configuration issue
- `"Plan {plan_id} applied {n} changes to {m} scenes"`

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Apply job runs but applies 0 changes | Missing `auto_approve=True` | Set `auto_approve=True` for automated systems |
| Infinite loop of apply jobs | Apply job completion triggering new apply job | Check job type before handling completion |
| "Plan cannot be applied" error | Plan already in APPLIED status | Check plan status before creating job |
| Changes not found | Changes already applied | Verify `applied=False` before creating job |

## Related Documentation
- [Analysis Jobs](./analysis.md)
- [Job Service Architecture](../architecture/job-service.md)
- [Plan Management](../services/plan-manager.md)