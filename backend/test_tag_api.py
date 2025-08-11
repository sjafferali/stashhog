#!/usr/bin/env python3
"""Quick test for tag API endpoints."""

import json

import requests

BASE_URL = "http://localhost:8080/api"


def test_add_tags():
    """Test adding tags to scenes."""
    response = requests.post(
        f"{BASE_URL}/scenes/add-tags", json={"scene_ids": [1, 2, 3], "tag_ids": [1, 2]}
    )
    print(f"Add tags status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Error: {response.text}")
    return response.status_code == 200


def test_remove_tags():
    """Test removing tags from scenes."""
    response = requests.post(
        f"{BASE_URL}/scenes/remove-tags", json={"scene_ids": [1, 2, 3], "tag_ids": [1]}
    )
    print(f"\nRemove tags status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Error: {response.text}")
    return response.status_code == 200


if __name__ == "__main__":
    print("Testing tag API endpoints...")
    print("=" * 50)

    # Note: These will fail if no scenes/tags exist with those IDs
    # This is just to verify the endpoints are accessible

    try:
        test_add_tags()
        test_remove_tags()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is the server running?")
    except Exception as e:
        print(f"Error: {e}")
