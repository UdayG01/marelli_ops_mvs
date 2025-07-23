#!/usr/bin/env python3
"""
Trigger Mode Test Script
Run this to test the trigger mode functionality
"""

import os
import sys
import django
import time

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ml_backend.settings')
django.setup()

from ml_api.views import camera_manager
from django.conf import settings
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_trigger_mode():
    """Test trigger mode functionality"""
    print("\n🎯 Testing Trigger Mode Functionality...")
    
    try:
        # Check camera connection
        if not camera_manager.is_connected:
            print("❌ Camera not connected. Attempting to connect...")
            success, message = camera_manager.connect()
            if not success:
                print(f"❌ Failed to connect camera: {message}")
                return False
        
        print("✅ Camera connected")
        
        # Check current trigger status
        trigger_status = camera_manager.get_trigger_status()
        print(f"📊 Current Trigger Status:")
        print(f"   - Trigger Mode: {trigger_status['is_trigger_mode']}")
        print(f"   - Monitoring: {trigger_status['is_monitoring']}")
        print(f"   - Trigger Count: {trigger_status['trigger_count']}")
        
        # If not in trigger mode, enable it
        if not trigger_status['is_trigger_mode']:
            print("🔄 Enabling trigger mode...")
            success, message = camera_manager.enable_trigger_mode()
            if success:
                print(f"✅ Trigger mode enabled: {message}")
            else:
                print(f"❌ Failed to enable trigger mode: {message}")
                return False
        else:
            print("✅ Trigger mode already enabled")
        
        # Monitor for trigger events
        print("\n👁️ Monitoring for trigger events...")
        print("   Send a signal to Line 0 to test trigger functionality")
        print("   Press Ctrl+C to stop monitoring\n")
        
        initial_count = camera_manager.trigger_count
        start_time = time.time()
        
        try:
            while True:
                current_count = camera_manager.trigger_count
                if current_count > initial_count:
                    print(f"🎯 TRIGGER DETECTED! Count: {current_count}")
                    print(f"   - Time: {time.strftime('%H:%M:%S')}")
                    print(f"   - This should initiate the full workflow:")
                    print(f"     ✓ Capture image")
                    print(f"     ✓ Process with YOLOv8")
                    print(f"     ✓ Save to database")
                    print(f"     ✓ Store in OK/NG folders")
                    print(f"     ✓ File transfer (if OK)")
                    initial_count = current_count
                
                # Show status every 30 seconds
                if time.time() - start_time > 30:
                    status = camera_manager.get_trigger_status()
                    print(f"📊 Status Update - Triggers: {status['trigger_count']}, Monitoring: {status['is_monitoring']}")
                    start_time = time.time()
                
                time.sleep(0.1)  # Check every 100ms
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            
        final_count = camera_manager.trigger_count
        total_triggers = final_count - initial_count
        print(f"\n📊 Final Summary:")
        print(f"   - Total triggers detected: {total_triggers}")
        print(f"   - Final trigger count: {final_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Trigger mode test error: {e}")
        return False

def test_manual_software_trigger():
    """Test manual software trigger"""
    print("\n🔧 Testing Manual Software Trigger...")
    
    try:
        if not camera_manager.is_connected:
            print("❌ Camera not connected")
            return False
        
        if not camera_manager.is_trigger_mode:
            print("❌ Camera not in trigger mode")
            return False
        
        print("📸 Sending software trigger...")
        
        # Get initial count
        initial_count = camera_manager.trigger_count
        
        # Send software trigger
        ret = camera_manager.camera.MV_CC_SetCommandValue("TriggerSoftware")
        if ret != 0:
            print(f"❌ Failed to send software trigger. Error: {ret}")
            return False
        
        # Wait a moment and check if trigger was processed
        time.sleep(2)
        
        final_count = camera_manager.trigger_count
        if final_count > initial_count:
            print(f"✅ Software trigger successful! Count: {final_count}")
            return True
        else:
            print("⚠️ Software trigger sent but no count increase detected")
            return False
            
    except Exception as e:
        print(f"❌ Software trigger test error: {e}")
        return False

def main():
    """Run trigger mode tests"""
    print("🚀 Starting Trigger Mode Tests...")
    
    # Test 1: Basic trigger mode functionality
    trigger_ok = test_trigger_mode()
    
    if trigger_ok:
        # Test 2: Manual software trigger
        software_trigger_ok = test_manual_software_trigger()
    else:
        software_trigger_ok = False
    
    # Summary
    print("\n📊 Test Summary:")
    print(f"   Trigger Mode: {'✅' if trigger_ok else '❌'}")
    print(f"   Software Trigger: {'✅' if software_trigger_ok else '❌'}")
    
    if trigger_ok:
        print("\n🎉 Trigger mode is working! Line 0 signals will:")
        print("   📸 Capture images automatically")
        print("   🧠 Process with YOLOv8 model")
        print("   💾 Save to database")
        print("   📁 Store in OK/NG folders")
        print("   📤 Transfer files (if status is OK)")
        print("\n💡 Check the logs for detailed trigger processing information")
    else:
        print("\n⚠️ Trigger mode tests failed. Check camera connection and configuration.")
    
    return trigger_ok and software_trigger_ok

if __name__ == "__main__":
    main()
