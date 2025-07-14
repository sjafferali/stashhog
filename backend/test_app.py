#!/usr/bin/env python
"""Test script to verify the FastAPI application structure."""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all imports."""
    print("Testing imports...")
    
    try:
        # Core modules
        print("  ✓ Importing core modules...")
        from app.core.config import get_settings
        from app.core.exceptions import StashHogException
        from app.core.middleware import RequestIDMiddleware
        from app.core.logging import configure_logging
        
        # API modules
        print("  ✓ Importing API modules...")
        from app.api import api_router
        
        # Main app
        print("  ✓ Importing main app...")
        from app.main import app
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_endpoints():
    """Test endpoint registration."""
    print("\nTesting endpoints...")
    
    try:
        from app.main import app
        
        routes = []
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    routes.append(f"{method} {route.path}")
        
        print(f"\nRegistered endpoints ({len(routes)}):")
        for route in sorted(routes):
            print(f"  - {route}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Endpoint test error: {e}")
        return False

def test_settings():
    """Test settings loading."""
    print("\nTesting settings...")
    
    try:
        from app.core.config import get_settings
        
        settings = get_settings()
        print(f"  ✓ App name: {settings.app.name}")
        print(f"  ✓ Version: {settings.app.version}")
        print(f"  ✓ Environment: {settings.app.environment}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Settings test error: {e}")
        return False

if __name__ == "__main__":
    print("StashHog Backend Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_endpoints,
        test_settings
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    if all(results):
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)