# Tag Deletion API Documentation

## Overview
The tag deletion functionality allows you to delete tags from both Stash and the local StashHog database through a REST API endpoint.

## Endpoint

### DELETE `/api/entities/tags/{tag_id}`

Deletes a tag from both Stash (via GraphQL API) and the local database.

#### Parameters
- `tag_id` (path parameter): The ID of the tag to delete

#### Response

**Success (200 OK):**
```json
{
  "success": true,
  "message": "Tag [tag_name] deleted successfully",
  "deleted_tag_id": "tag_id"
}
```

**Tag Not Found (404):**
```json
{
  "detail": "Tag not found in local database"
}
```

**Stash Deletion Failed (500):**
```json
{
  "detail": "Failed to delete tag from Stash"
}
```

## Implementation Details

### Components

1. **GraphQL Mutation** (`backend/app/services/stash/mutations.py:180-184`):
   - `DELETE_TAG` mutation for communicating with Stash GraphQL API

2. **StashService Method** (`backend/app/services/stash_service.py:627-648`):
   - `delete_tag()` method handles the GraphQL execution
   - Invalidates tag cache after deletion
   - Returns boolean indicating success

3. **API Endpoint** (`backend/app/api/routes/entities.py:377-436`):
   - Validates tag exists in local database
   - Calls StashService to delete from Stash
   - Removes from local database if Stash deletion succeeds
   - Handles errors gracefully

4. **Tests** (`backend/tests/test_tag_deletion.py`):
   - Test successful deletion
   - Test tag not found scenario
   - Test Stash deletion failure handling

## Usage Example

### Using curl:
```bash
curl -X DELETE http://localhost:8000/api/entities/tags/YOUR_TAG_ID
```

### Using Python:
```python
import requests

tag_id = "your-tag-id"
response = requests.delete(f"http://localhost:8000/api/entities/tags/{tag_id}")

if response.status_code == 200:
    print("Tag deleted successfully")
else:
    print(f"Error: {response.json()}")
```

### Using the test script:
```bash
cd backend
python test_tag_delete_endpoint.py
```

## Important Notes

1. **Destructive Operation**: This operation cannot be undone. The tag will be permanently deleted from both Stash and the local database.

2. **Stash as Source of Truth**: If deletion from Stash succeeds but local database deletion fails, the operation is still considered successful (with a logged error).

3. **Cache Invalidation**: The tag cache is automatically invalidated after successful deletion to ensure consistency.

4. **Authentication**: If your Stash instance requires authentication, ensure the `stash_api_key` is configured in your settings.

## Error Handling

The endpoint handles several error scenarios:

1. **Tag not found**: Returns 404 if the tag doesn't exist in the local database
2. **Stash deletion failure**: Returns 500 if the Stash GraphQL mutation fails
3. **Network errors**: Returns 500 with error details if connection to Stash fails
4. **Local database errors**: Logs the error but doesn't fail the request if Stash deletion succeeded

## Testing

To test the endpoint:

1. Ensure your backend is running:
   ```bash
   cd backend
   ./start_backend.sh
   ```

2. Ensure Stash is running and accessible

3. Get a tag ID from your database (you can use the GET `/api/entities/tags` endpoint)

4. Use the test script or make a DELETE request to `/api/entities/tags/{tag_id}`