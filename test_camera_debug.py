#!/usr/bin/env python3
"""
Camera Debug Test Script
Run this to test camera functionality and YOLOv8 processing separately
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ml_backend.settings')
django.setup()

from ml_api.views import camera_manager
from ml_api.services import enhanced_nut_detection_service
from django.conf import settings
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_camera_connection():
    """Test camera connection"""
    print("\n🔍 Testing Camera Connection...")
    
    try:
        # Check if camera is already connected
        if camera_manager.is_connected:
            print("✅ Camera already connected")
            return True
        
        # Try to connect
        success, message = camera_manager.connect()
        if success:
            print(f"✅ Camera connected: {message}")
            return True
        else:
            print(f"❌ Camera connection failed: {message}")
            return False
            
    except Exception as e:
        print(f"❌ Camera connection error: {e}")
        return False

def test_camera_capture():
    """Test camera capture"""
    print("\n📸 Testing Camera Capture...")
    
    try:
        if not camera_manager.is_connected:
            print("❌ Camera not connected")
            return False
        
        # Test manual override capture
        save_path = os.path.join(settings.MEDIA_ROOT, 'debug_captures')
        os.makedirs(save_path, exist_ok=True)
        
        success, result = camera_manager.capture_manual_override(save_path)
        
        if success:
            print(f"✅ Camera capture successful: {result['filename']}")
            print(f"   File size: {result['size']} bytes")
            print(f"   Path: {result['filepath']}")
            return True, result['filepath']
        else:
            print(f"❌ Camera capture failed: {result}")
            return False, None
            
    except Exception as e:
        print(f"❌ Camera capture error: {e}")
        return False, None

def test_yolo_processing(image_path):
    """Test YOLOv8 processing"""
    print("\n🧠 Testing YOLOv8 Processing...")
    
    try:
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            return False
        
        # Test processing
        result = enhanced_nut_detection_service.process_image_with_id(
            image_path=image_path,
            image_id="DEBUG_TEST",
            user_id=None
        )
        
        if result['success']:
            print("✅ YOLOv8 processing successful")
            decision = result['decision']
            print(f"   Present: {decision['present_count']}")
            print(f"   Missing: {decision['missing_count']}")
            print(f"   Status: {decision['status']}")
            print(f"   Processing time: {result['processing_time']:.2f}s")
            return True
        else:
            print(f"❌ YOLOv8 processing failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ YOLOv8 processing error: {e}")
        return False

def test_camera_states():
    """Test camera trigger mode states"""
    print("\n🎯 Testing Camera States...")
    
    try:
        print(f"   Connected: {camera_manager.is_connected}")
        print(f"   Streaming: {camera_manager.is_streaming}")
        print(f"   Trigger mode: {camera_manager.is_trigger_mode}")
        print(f"   Monitoring triggers: {camera_manager.is_monitoring_trigger}")
        print(f"   Trigger count: {camera_manager.trigger_count}")
        
        if camera_manager.is_connected:
            trigger_status = camera_manager.get_trigger_status()
            print(f"   Trigger status: {trigger_status}")
            
        return True
        
    except Exception as e:
        print(f"❌ Camera state error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Camera Debug Tests...")
    
    # Test 1: Camera connection
    camera_ok = test_camera_connection()
    
    # Test 2: Camera states
    test_camera_states()
    
    # Test 3: Camera capture
    capture_ok = False
    image_path = None
    if camera_ok:
        capture_ok, image_path = test_camera_capture()
    
    # Test 4: YOLOv8 processing
    yolo_ok = False
    if capture_ok and image_path:
        yolo_ok = test_yolo_processing(image_path)
    
    # Summary
    print("\n📊 Test Summary:")
    print(f"   Camera Connection: {'✅' if camera_ok else '❌'}")
    print(f"   Camera Capture: {'✅' if capture_ok else '❌'}")
    print(f"   YOLOv8 Processing: {'✅' if yolo_ok else '❌'}")
    
    if camera_ok and capture_ok and yolo_ok:
        print("\n🎉 All tests passed! The system should work correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")
    
    return camera_ok and capture_ok and yolo_ok

if __name__ == "__main__":
    main()
