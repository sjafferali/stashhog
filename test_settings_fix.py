#!/usr/bin/env python3
"""Test script to verify settings are saved with correct types."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.models.setting import Setting
from app.models.base import Base

# Create in-memory database for testing
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def test_settings_storage():
    """Test that settings maintain their proper types."""
    session = Session()
    
    # Test different types of settings
    test_settings = [
        ("video_ai_server_url", "http://localhost:8084"),  # string
        ("video_ai_frame_interval", 5),  # integer
        ("video_ai_threshold", 0.4),  # float
        ("video_ai_create_markers", True),  # boolean
    ]
    
    print("Testing settings storage...")
    
    # Save settings
    for key, value in test_settings:
        setting = Setting(key=key, value=value)
        session.add(setting)
    
    session.commit()
    
    # Retrieve settings
    for key, expected_value in test_settings:
        setting = session.query(Setting).filter_by(key=key).first()
        if setting:
            print(f"\nKey: {key}")
            print(f"  Expected: {expected_value} (type: {type(expected_value).__name__})")
            print(f"  Stored: {setting.value} (type: {type(setting.value).__name__})")
            print(f"  Match: {setting.value == expected_value}")
            
            # Verify type is preserved
            assert type(setting.value) == type(expected_value), f"Type mismatch for {key}"
            assert setting.value == expected_value, f"Value mismatch for {key}"
        else:
            print(f"ERROR: Setting {key} not found!")
    
    print("\n✅ All settings maintained their correct types!")
    session.close()

if __name__ == "__main__":
    test_settings_storage()