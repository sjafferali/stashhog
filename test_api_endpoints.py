#!/usr/bin/env python3
"""
Test script for StashHog API endpoints.
"""
import asyncio
import json
import httpx
from datetime import datetime
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000/api"


class APITester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
    
    async def close(self):
        await self.client.aclose()
    
    def log_result(self, endpoint: str, method: str, status: int, success: bool, response: Any):
        self.test_results.append({
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "success": success,
            "response": response
        })
        
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} {method} {endpoint} - Status: {status}")
        if not success:
            print(f"   Response: {json.dumps(response, indent=2)}")
    
    async def test_endpoint(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        expected_status: int = 200
    ) -> Dict[str, Any]:
        """Test a single endpoint."""
        url = f"{BASE_URL}{endpoint}"
        
        try:
            if method == "GET":
                response = await self.client.get(url, params=params)
            elif method == "POST":
                response = await self.client.post(url, json=data, params=params)
            elif method == "PUT":
                response = await self.client.put(url, json=data, params=params)
            elif method == "DELETE":
                response = await self.client.delete(url, params=params)
            elif method == "PATCH":
                response = await self.client.patch(url, json=data, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            success = response.status_code == expected_status
            response_data = response.json() if response.content else {}
            
            self.log_result(endpoint, method, response.status_code, success, response_data)
            
            return response_data
            
        except Exception as e:
            self.log_result(endpoint, method, 0, False, {"error": str(e)})
            return {"error": str(e)}
    
    async def run_tests(self):
        """Run all API endpoint tests."""
        print("🚀 Starting StashHog API Tests\n")
        
        # Health endpoints
        print("📋 Testing Health Endpoints")
        await self.test_endpoint("GET", "/health")
        await self.test_endpoint("GET", "/health/ready")
        await self.test_endpoint("GET", "/health/version")
        print()
        
        # Settings endpoints
        print("⚙️  Testing Settings Endpoints")
        await self.test_endpoint("GET", "/settings")
        await self.test_endpoint("PUT", "/settings", data={
            "openai_model": "gpt-4",
            "sync_batch_size": 50
        })
        await self.test_endpoint("POST", "/settings/test-stash", data={
            "url": "http://localhost:9999"
        })
        await self.test_endpoint("POST", "/settings/test-openai", data={
            "model": "gpt-4"
        })
        print()
        
        # Scene endpoints
        print("🎬 Testing Scene Endpoints")
        await self.test_endpoint("GET", "/scenes", params={
            "page": 1,
            "per_page": 10
        })
        await self.test_endpoint("GET", "/scenes", params={
            "search": "test",
            "organized": True
        })
        await self.test_endpoint("POST", "/scenes/sync", params={
            "background": True,
            "incremental": True
        })
        await self.test_endpoint("GET", "/scenes/stats/summary")
        
        # Test non-existent scene
        await self.test_endpoint("GET", "/scenes/non-existent-id", expected_status=404)
        print()
        
        # Entity endpoints
        print("👥 Testing Entity Endpoints")
        await self.test_endpoint("GET", "/entities/performers")
        await self.test_endpoint("GET", "/entities/performers", params={"search": "test"})
        await self.test_endpoint("GET", "/entities/tags")
        await self.test_endpoint("GET", "/entities/studios")
        print()
        
        # Analysis endpoints
        print("🔍 Testing Analysis Endpoints")
        await self.test_endpoint("POST", "/analysis/generate", data={
            "scene_ids": ["scene1", "scene2"],
            "options": {
                "detect_performers": True,
                "detect_tags": True,
                "confidence_threshold": 0.7
            },
            "plan_name": "Test Analysis Plan"
        })
        
        await self.test_endpoint("GET", "/analysis/plans", params={
            "page": 1,
            "per_page": 10
        })
        
        # Test non-existent plan
        await self.test_endpoint("GET", "/analysis/plans/999", expected_status=404)
        print()
        
        # Job endpoints
        print("💼 Testing Job Endpoints")
        await self.test_endpoint("GET", "/jobs", params={
            "limit": 10
        })
        await self.test_endpoint("GET", "/jobs", params={
            "status": "completed",
            "job_type": "scene_sync"
        })
        
        # Test non-existent job
        await self.test_endpoint("GET", "/jobs/non-existent-id", expected_status=404)
        await self.test_endpoint("DELETE", "/jobs/non-existent-id", expected_status=404)
        print()
        
        # Sync endpoints
        print("🔄 Testing Sync Endpoints")
        await self.test_endpoint("POST", "/sync/all")
        await self.test_endpoint("POST", "/sync/scenes")
        await self.test_endpoint("POST", "/sync/performers")
        await self.test_endpoint("POST", "/sync/tags")
        await self.test_endpoint("POST", "/sync/studios")
        await self.test_endpoint("GET", "/sync/stats")
        print()
        
        # Test error handling
        print("⚠️  Testing Error Handling")
        await self.test_endpoint("POST", "/scenes", data={
            "invalid": "data"
        }, expected_status=422)
        
        await self.test_endpoint("GET", "/non-existent-route", expected_status=404)
        print()
        
        # Summary
        print("\n📊 Test Summary")
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        failed = total - passed
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['method']} {result['endpoint']} (Status: {result['status']})")


async def main():
    """Run the API tests."""
    tester = APITester()
    
    try:
        await tester.run_tests()
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())