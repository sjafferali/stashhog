#!/bin/bash

# Test script for bulk update API endpoints

BASE_URL="http://localhost:8000/api"
PLAN_ID=${1:-1}  # Default to plan ID 1 if not provided

echo "Testing bulk update API for plan ID: $PLAN_ID"
echo "========================================="

# Test 1: Get test endpoint data
echo -e "\n1. Testing GET /test/bulk-update-test/$PLAN_ID"
curl -X GET "$BASE_URL/test/bulk-update-test/$PLAN_ID" \
  -H "Content-Type: application/json" | jq '.'

# Test 2: Test bulk update with dry run (accept all)
echo -e "\n\n2. Testing POST /test/bulk-update-test/$PLAN_ID (dry run - accept all)"
curl -X POST "$BASE_URL/test/bulk-update-test/$PLAN_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_all",
    "dry_run": true
  }' | jq '.'

# Test 3: Test bulk update with dry run (accept by field)
echo -e "\n\n3. Testing POST /test/bulk-update-test/$PLAN_ID (dry run - accept by field)"
curl -X POST "$BASE_URL/test/bulk-update-test/$PLAN_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_by_field",
    "field": "tags",
    "dry_run": true
  }' | jq '.'

# Test 4: Test bulk update with dry run (accept by confidence)
echo -e "\n\n4. Testing POST /test/bulk-update-test/$PLAN_ID (dry run - accept by confidence)"
curl -X POST "$BASE_URL/test/bulk-update-test/$PLAN_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_by_confidence",
    "confidence_threshold": 0.8,
    "dry_run": true
  }' | jq '.'

# Test 5: Test actual bulk update endpoint
echo -e "\n\n5. Testing POST /analysis/plans/$PLAN_ID/bulk-update (accept by field - tags)"
curl -X POST "$BASE_URL/analysis/plans/$PLAN_ID/bulk-update" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_by_field",
    "field": "tags"
  }' | jq '.'

echo -e "\n\nDone testing!"