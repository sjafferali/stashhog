# Bulk Update API Testing Guide

This guide explains how to test and debug the bulk update API endpoints.

## Test Endpoints

Two test endpoints have been added to help debug bulk update operations:

### 1. GET /api/test/bulk-update-test/{plan_id}

Retrieves detailed information about a plan and its changes:
- Plan details (ID, name, status, created date)
- Summary of changes (total, pending, accepted, rejected, applied)
- Breakdown of changes by field
- Sample changes for inspection

### 2. POST /api/test/bulk-update-test/{plan_id}

Simulates bulk update operations with a dry-run option:
- Shows which changes would be affected by the operation
- Validates parameters before execution
- Can perform actual updates with `dry_run: false`

## Testing Tools

### 1. Python Test Script (Recommended)

The `test_bulk_update_api.py` script provides a comprehensive test suite with formatted output:

```bash
# Test with default plan ID (1)
python test_bulk_update_api.py

# Test with specific plan ID
python test_bulk_update_api.py 5
```

Features:
- Color-coded output with tables
- Dry-run simulations before actual updates
- Interactive confirmation for destructive operations
- Detailed error reporting

### 2. Shell Script

The `test_bulk_update.sh` script provides basic curl commands:

```bash
# Test with default plan ID (1)
./test_bulk_update.sh

# Test with specific plan ID
./test_bulk_update.sh 5
```

### 3. Manual curl Commands

#### Get plan information:
```bash
curl -X GET "http://localhost:8000/api/test/bulk-update-test/1" | jq '.'
```

#### Test accept all (dry run):
```bash
curl -X POST "http://localhost:8000/api/test/bulk-update-test/1" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_all",
    "dry_run": true
  }' | jq '.'
```

#### Test accept by field (dry run):
```bash
curl -X POST "http://localhost:8000/api/test/bulk-update-test/1" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_by_field",
    "field": "tags",
    "dry_run": true
  }' | jq '.'
```

#### Test accept by confidence (dry run):
```bash
curl -X POST "http://localhost:8000/api/test/bulk-update-test/1" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_by_confidence",
    "confidence_threshold": 0.8,
    "dry_run": true
  }' | jq '.'
```

#### Actual bulk update:
```bash
curl -X POST "http://localhost:8000/api/analysis/plans/1/bulk-update" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_by_field",
    "field": "tags"
  }' | jq '.'
```

## Debugging with Logs

Enhanced logging has been added to the bulk update endpoint. To see detailed logs:

1. Check the backend logs:
```bash
tail -f backend/logs/app.log
```

2. Look for log entries with:
   - `=== Bulk update request received ===` - Start of request
   - `Building query` - Query construction details
   - `Found X changes to update` - Number of changes found
   - `Applied action to X changes` - Number of changes modified
   - `Change counts` - Final status counts
   - `=== Bulk update completed ===` - End of request

## Common Issues and Solutions

### Issue: No changes found to update

**Symptoms:**
- `updated_count: 0` in response
- Log shows "Found 0 changes to update"

**Possible causes:**
1. All changes already accepted/rejected/applied
2. No changes match the filter criteria
3. Wrong plan ID

**Solution:**
- Use GET test endpoint to check current state
- Verify pending changes exist
- Check filter parameters

### Issue: 404 Plan not found

**Symptoms:**
- HTTP 404 error
- "Analysis plan X not found"

**Solution:**
- List available plans: `curl http://localhost:8000/api/analysis/plans | jq '.'`
- Use a valid plan ID

### Issue: 400 Bad Request

**Symptoms:**
- HTTP 400 error
- Missing required parameters

**Solution:**
- For field-based actions, include `field` parameter
- For confidence-based actions, include `confidence_threshold` parameter

## Bulk Update Actions

### accept_all
Accepts all pending changes in the plan.

### reject_all
Rejects all pending changes in the plan.

### accept_by_field
Accepts all pending changes for a specific field.
Required parameter: `field` (e.g., "tags", "performers", "studio")

### reject_by_field
Rejects all pending changes for a specific field.
Required parameter: `field`

### accept_by_confidence
Accepts all pending changes with confidence >= threshold.
Required parameter: `confidence_threshold` (0.0 to 1.0)

## Optional Filters

### scene_id
Limit the bulk operation to changes for a specific scene:
```json
{
  "action": "accept_all",
  "scene_id": "abc123"
}
```

## Plan Status Updates

The bulk update operation automatically updates the plan status:
- If any changes are accepted/rejected, status becomes "reviewing"
- If all non-rejected changes are applied, status becomes "applied"
- If all changes are rejected, status becomes "cancelled"