#!/usr/bin/env python3
"""
Test the new trigger-aware workflow
This tests the complete flow: start inspection -> wait for trigger -> process -> results
"""

import os
import sys
import django
import time
import requests
import json

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ml_backend.settings')
django.setup()

from ml_api.views import camera_manager
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = 'http://localhost:8000/api/ml'

def test_trigger_workflow():
    """Test the complete trigger-aware workflow"""
    print("\n🎯 Testing Trigger-Aware Workflow...")
    
    try:
        # Step 1: Start trigger inspection
        print("📋 Step 1: Starting trigger inspection...")
        response = requests.post(f'{BASE_URL}/inspection/start-trigger/')
        data = response.json()
        
        if not data['success']:
            print(f"❌ Failed to start trigger inspection: {data['message']}")
            return False
        
        print(f"✅ Trigger inspection started: {data['message']}")
        print(f"   Step: {data['step']}")
        
        # Step 2: Poll for trigger results (simulate waiting)
        print("\n⏳ Step 2: Polling for trigger results...")
        print("   (In real scenario, this waits for Line 0 hardware trigger)")
        
        max_polls = 5
        poll_count = 0
        
        while poll_count < max_polls:
            poll_count += 1
            print(f"   Poll #{poll_count}: Checking for trigger results...")
            
            response = requests.get(f'{BASE_URL}/inspection/poll-trigger/')
            data = response.json()
            
            if not data['success']:
                print(f"❌ Polling failed: {data['message']}")
                return False
            
            if data['new_result']:
                print(f"✅ New trigger result found!")
                print(f"   Message: {data['message']}")
                print(f"   Trigger Count: {data['trigger_count']}")
                
                # Display results
                result = data['result']
                print(f"\n📊 Inspection Results:")
                print(f"   Image ID: {result['image_id']}")
                print(f"   Overall Result: {result['overall_result']}")
                print(f"   Present: {result['present_count']}, Missing: {result['missing_count']}")
                print(f"   Storage Folder: {result['storage_folder']}")
                print(f"   Database ID: {result['database_id']}")
                print(f"   Processed At: {result['processed_at']}")
                
                return True
            
            elif data['waiting']:
                print(f"   Still waiting: {data['message']}")
                print(f"   Trigger Count: {data['trigger_count']}")
                print(f"   Monitoring: {data.get('is_monitoring', 'Unknown')}")
                
                # If no hardware trigger available, send software trigger for testing
                if poll_count == 3:
                    print("\n🧪 Sending software trigger for testing...")
                    test_response = requests.post(f'{BASE_URL}/camera/trigger/test/')
                    test_data = test_response.json()
                    
                    if test_data['success']:
                        print(f"✅ Software trigger sent: {test_data['message']}")
                    else:
                        print(f"❌ Software trigger failed: {test_data['message']}")
            
            time.sleep(2)  # Wait 2 seconds between polls
        
        print(f"⏰ Polling timeout after {max_polls} attempts")
        return False
        
    except Exception as e:
        print(f"❌ Workflow test error: {e}")
        return False

def test_camera_status():
    """Test camera status and trigger mode"""
    print("\n📷 Testing Camera Status...")
    
    try:
        response = requests.get(f'{BASE_URL}/camera/status/')
        data = response.json()
        
        print(f"   Connected: {data.get('connected', False)}")
        print(f"   Streaming: {data.get('streaming', False)}")
        print(f"   SDK Available: {data.get('sdk_available', False)}")
        print(f"   Trigger Mode: {data.get('is_trigger_mode', False)}")
        print(f"   Monitoring: {data.get('is_monitoring', False)}")
        print(f"   Trigger Count: {data.get('trigger_count', 0)}")
        
        return data.get('connected', False)
        
    except Exception as e:
        print(f"❌ Camera status error: {e}")
        return False

def test_direct_camera_connection():
    """Test direct camera connection using camera_manager"""
    print("\n🔗 Testing Direct Camera Connection...")
    
    try:
        if not camera_manager.is_connected:
            print("   Attempting to connect camera...")
            success, message = camera_manager.connect()
            
            if success:
                print(f"✅ Camera connected: {message}")
            else:
                print(f"❌ Camera connection failed: {message}")
                return False
        else:
            print("✅ Camera already connected")
        
        # Check trigger mode status
        trigger_status = camera_manager.get_trigger_status()
        print(f"   Trigger Mode: {trigger_status['is_trigger_mode']}")
        print(f"   Monitoring: {trigger_status['is_monitoring']}")
        print(f"   Trigger Count: {trigger_status['trigger_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct camera connection error: {e}")
        return False

def main():
    """Run all workflow tests"""
    print("🚀 Starting Trigger-Aware Workflow Tests...")
    
    # Test 1: Direct camera connection
    camera_ok = test_direct_camera_connection()
    
    # Test 2: Camera status via API
    api_camera_ok = test_camera_status()
    
    # Test 3: Complete trigger workflow
    workflow_ok = False
    if camera_ok or api_camera_ok:
        workflow_ok = test_trigger_workflow()
    else:
        print("⚠️ Skipping workflow test - camera not available")
    
    # Summary
    print("\n📊 Test Summary:")
    print(f"   Direct Camera: {'✅' if camera_ok else '❌'}")
    print(f"   API Camera: {'✅' if api_camera_ok else '❌'}")
    print(f"   Trigger Workflow: {'✅' if workflow_ok else '❌'}")
    
    if workflow_ok:
        print("\n🎉 Trigger-aware workflow is working!")
        print("   ✓ Camera connects and enables trigger mode")
        print("   ✓ System waits for Line 0 hardware trigger")
        print("   ✓ Trigger detection processes image automatically")
        print("   ✓ Results are returned for display")
        print("\n💡 To use in production:")
        print(f"   1. Visit: http://localhost:8000/api/ml/inspection/trigger/")
        print(f"   2. Click 'Start New Inspection'")
        print(f"   3. Send signal to Line 0 to trigger capture")
        print(f"   4. View results and wait for next trigger")
    else:
        print("\n⚠️ Trigger workflow tests failed.")
        print("   Check camera connection and trigger mode configuration.")
    
    return workflow_ok

if __name__ == "__main__":
    main()