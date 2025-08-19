#!/usr/bin/env python3
"""
Simple test script to verify the tag deletion endpoint works.
"""

import asyncio

import aiohttp


async def test_delete_tag():
    """Test the DELETE /api/entities/tags/{tag_id} endpoint."""

    # Configure your API endpoint
    base_url = (
        "http://localhost:8000"  # Adjust if your backend runs on a different port
    )

    # Example tag ID to delete (replace with an actual tag ID from your system)
    tag_id = "test-tag-id"  # Replace with a real tag ID

    endpoint = f"{base_url}/api/entities/tags/{tag_id}"

    print(f"Testing DELETE endpoint: {endpoint}")
    print("=" * 50)

    async with aiohttp.ClientSession() as session:
        try:
            # Send DELETE request
            async with session.delete(endpoint) as response:
                status = response.status
                data = await response.json()

                print(f"Status Code: {status}")
                print(f"Response: {data}")

                if status == 200:
                    print("\n✅ Tag deletion successful!")
                elif status == 404:
                    print("\n⚠️ Tag not found in local database")
                elif status == 500:
                    print("\n❌ Error deleting tag from Stash")
                else:
                    print(f"\n❓ Unexpected status code: {status}")

        except aiohttp.ClientConnectionError:
            print(
                "\n❌ Could not connect to backend. Make sure it's running on", base_url
            )
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    print("Tag Deletion Endpoint Test")
    print("=" * 50)
    print("\nNote: Make sure to:")
    print("1. Start your backend server")
    print("2. Replace 'test-tag-id' with an actual tag ID from your database")
    print("3. Ensure Stash is running and accessible")
    print("\n" + "=" * 50 + "\n")

    asyncio.run(test_delete_tag())
