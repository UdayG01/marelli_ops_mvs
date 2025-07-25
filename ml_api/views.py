# ml_api/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, JSONParser
from PIL import Image
from datetime import datetime
import io
import base64
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Import the nut detection service
try:
    from .services import enhanced_nut_detection_service
    SERVICE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import nut detection service: {e}")
    SERVICE_AVAILABLE = False


class NutDetectionView(APIView):
    """
    Industrial Nut Detection API View
    
    Endpoints:
    - POST: Process uploaded image for nut detection
    - GET: Health check
    """
    parser_classes = [MultiPartParser, JSONParser]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize detection service once
        if SERVICE_AVAILABLE:
            try:
                self.detection_service = enhanced_nut_detection_service  # Fixed: removed ()
                logger.info("Nut detection service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize nut detection service: {e}")
                self.detection_service = None
        else:
            self.detection_service = None
    
    def post(self, request):
        """
        Process uploaded image for nut detection
        
        Expected form data:
        - image: Image file (required)
        - text: Additional text input (optional)
        
        Returns:
        JSON response with nut detection results
        """
        try:
            # Check if service is available
            if self.detection_service is None:
                return Response(
                    {'error': 'Nut detection service not available. Check model file and dependencies.'}, 
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Get image and text from request
            image_file = request.FILES.get('image')
            text_input = request.data.get('text', '')
            
            if not image_file:
                return Response(
                    {'error': 'No image provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process the image using PIL then convert for nut detection
            try:
                pil_image = Image.open(image_file)
                filename = image_file.name
                
                # Convert PIL image to file path temporarily for processing
                import tempfile
                import os
                
                # Save PIL image to temporary file
                temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                pil_image.save(temp_file.name, 'JPEG')
                temp_file.close()
                
                try:
                    # Process with the enhanced service
                    result = self.detection_service.process_image_with_id(
                        image_path=temp_file.name,
                        image_id=f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        user_id=getattr(request.user, 'id', None) if hasattr(request, 'user') else None
                    )
                    
                    # Add text analysis if provided
                    if text_input:
                        result['text_analysis'] = {
                            'text_input': text_input,
                            'text_length': len(text_input),
                            'text_preview': text_input[:100] + '...' if len(text_input) > 100 else text_input
                        }
                    
                    # Add image metadata
                    result['image_metadata'] = {
                        'filename': filename,
                        'format': pil_image.format,
                        'size': pil_image.size,
                        'mode': pil_image.mode
                    }
                    
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
                
                # Return appropriate HTTP status
                response_status = status.HTTP_200_OK if result.get('success', False) else status.HTTP_400_BAD_REQUEST
                
                return Response(result, status=response_status)
                
            except Exception as e:
                logger.error(f"Image processing error: {e}")
                return Response(
                    {
                        'success': False,
                        'error': f'Image processing failed: {str(e)}',
                        'timestamp': datetime.now().isoformat()
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        except Exception as e:
            logger.error(f"API error: {e}")
            return Response(
                {
                    'success': False,
                    'error': 'Internal server error',
                    'timestamp': datetime.now().isoformat()
                }, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get(self, request):
        """
        Health check endpoint
        
        Returns:
        JSON response with service status
        """
        try:
            # Check if service is available
            service_available = self.detection_service is not None
            model_loaded = False
            
            if service_available:
                # Check if model is actually loaded
                model_loaded = (
                    hasattr(self.detection_service, 'model') and 
                    self.detection_service.model is not None
                )
            
            health_status = {
                'success': True,
                'service': 'Industrial Nut Detection API',
                'status': 'healthy' if model_loaded else 'unhealthy',
                'service_available': service_available,
                'model_loaded': model_loaded,
                'timestamp': datetime.now().isoformat()
            }
            
            if service_available and hasattr(self.detection_service, 'model_path'):
                health_status['model_path'] = self.detection_service.model_path
                
            if service_available and hasattr(self.detection_service, 'config'):
                health_status['config'] = self.detection_service.config
                
            if service_available and hasattr(self.detection_service, 'get_statistics'):
                try:
                    health_status['statistics'] = self.detection_service.get_statistics()
                except Exception as e:
                    logger.warning(f"Could not get statistics: {e}")
            
            if not model_loaded:
                if not service_available:
                    health_status['error'] = 'Service not available - check imports and dependencies'
                else:
                    health_status['error'] = 'Model not loaded - check model file path and format'
            
            return Response(health_status, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return Response({
                'success': False,
                'service': 'Industrial Nut Detection API',
                'status': 'unhealthy',
                'service_available': False,
                'model_loaded': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def options(self, request, *args, **kwargs):
        """
        Handle OPTIONS requests for CORS
        """
        return Response(
            {
                'name': 'Nut Detection',
                'description': 'Industrial Nut Detection API View\\n\\nEndpoints:\\n- POST: Process uploaded image for nut detection\\n- GET: Health check',
                'renders': ['application/json', 'text/html'],
                'parses': ['multipart/form-data', 'application/json']
            },
            status=status.HTTP_200_OK
        )


# Alternative Base64 View for backward compatibility
class NutDetectionBase64View(APIView):
    """Base64 image endpoint for nut detection"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if SERVICE_AVAILABLE:
            try:
                self.detection_service = enhanced_nut_detection_service()
            except Exception as e:
                logger.error(f"Failed to initialize nut detection service: {e}")
                self.detection_service = None
        else:
            self.detection_service = None
    
    def post(self, request):
        try:
            if self.detection_service is None:
                return Response(
                    {'error': 'Nut detection service not available'}, 
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Get base64 image and text
            image_base64 = request.data.get('image_base64')
            text_input = request.data.get('text', '')
            
            if not image_base64:
                return Response(
                    {'error': 'No image_base64 provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # Decode base64 image
                image_data = base64.b64decode(image_base64)
                image = Image.open(io.BytesIO(image_data))
                
                # Process with nut detection
                result = self.detection_service.process_image_from_pil(image, "base64_image")
                
                # Add text analysis if provided
                if text_input:
                    result['text_analysis'] = {
                        'text_input': text_input,
                        'text_length': len(text_input)
                    }
                
                response_status = status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST
                return Response(result, status=response_status)
                
            except Exception as e:
                logger.error(f"Base64 processing error: {e}")
                return Response(
                    {'error': f'Base64 processing failed: {str(e)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        except Exception as e:
            logger.error(f"Base64 API error: {e}")
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Keep the old views for backward compatibility (renamed)
class MLPredictionView(APIView):
    """Legacy ML prediction view (redirects to nut detection)"""
    parser_classes = [MultiPartParser, JSONParser]
    
    def post(self, request):
        # Redirect to new nut detection view
        nut_view = NutDetectionView()
        nut_view.setup(request)
        return nut_view.post(request)


class MLPredictionBase64View(APIView):
    """Legacy base64 prediction view (redirects to nut detection)"""
    
    def post(self, request):
        # Redirect to new nut detection base64 view
        nut_view = NutDetectionBase64View()
        nut_view.setup(request)
        return nut_view.post(request)


# HTML page view
from django.shortcuts import render

def detection_page(request):
    """
    Render the HTML page for nut detection
    """
    return render(request, 'ml_api/detection.html')


# ========== CAMERA FUNCTIONALITY ADDED BELOW ==========
# Camera control imports
import sys
import os
import cv2
import numpy as np
import threading
import time
import json
import ctypes
import tempfile
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

# In your ml_api/views.py file, replace the camera import section with this SIMPLE version:

# Add camera drivers to path
camera_driver_path = os.path.join(settings.BASE_DIR, 'MvImport')

print(f"🔍 Camera driver path: {camera_driver_path}")
print(f"🔍 Path exists: {os.path.exists(camera_driver_path)}")

# Add to Python path
if camera_driver_path not in sys.path:
    sys.path.insert(0, camera_driver_path)
    print(f"✅ Added to sys.path: {camera_driver_path}")

# Simple import exactly like your working code
try:
    from MvImport import *
    from MvImport.MvCameraControl_class import *
    HIKROBOT_AVAILABLE = True
    print("✅ Hikrobot SDK imported successfully")
    
except ImportError as e:
    HIKROBOT_AVAILABLE = False
    print(f"❌ Failed to import Hikrobot SDK: {e}")
    logger.warning(f"Hikrobot SDK not available: {e}")

class HikrobotCameraManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.camera = None
            self.device_list = None
            self.is_streaming = False
            self.is_connected = False
            self.current_frame = None
            self.frame_lock = threading.Lock()
            # Trigger mode functionality - NEW
            self.is_trigger_mode = False
            self.is_monitoring_trigger = False
            self.trigger_count = 0
            self.last_trigger_time = None
            self.monitoring_thread = None
            self.stop_monitoring = threading.Event()
            self.initialized = True
    
    def connect(self):
        """Connect to the first available Hikrobot camera"""
        try:
            logger.info("🔍 Starting camera connection process...")
            
            if not HIKROBOT_AVAILABLE:
                logger.error("❌ Hikrobot SDK not available")
                return False, "Hikrobot SDK not available"
            
            if self.is_connected:
                logger.info("✅ Camera already connected")
                return True, "Already connected"
            
            logger.info("🎥 Creating camera object...")
            # Create camera object
            self.camera = MvCamera()
            
            # Get device list
            self.device_list = MV_CC_DEVICE_INFO_LIST()
            tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE
            
            logger.info("🔍 Enumerating devices...")
            # Enumerate devices
            ret = self.camera.MV_CC_EnumDevices(tlayerType, self.device_list)
            if ret != 0:
                logger.error(f"❌ Failed to enumerate devices. Error: {ret}")
                return False, f"Failed to enumerate devices. Error: {ret}"
            
            logger.info(f"📱 Found {self.device_list.nDeviceNum} device(s)")
            if self.device_list.nDeviceNum == 0:
                logger.error("❌ No Hikrobot cameras found")
                return False, "No Hikrobot cameras found"
            
            # Connect to first camera
            stDeviceList = cast(self.device_list.pDeviceInfo[0], POINTER(MV_CC_DEVICE_INFO)).contents
            
            logger.info("🔗 Creating camera handle...")
            # Create handle
            ret = self.camera.MV_CC_CreateHandle(stDeviceList)
            if ret != 0:
                logger.error(f"❌ Failed to create handle. Error: {ret}")
                return False, f"Failed to create handle. Error: {ret}"
            
            logger.info("🚪 Opening device...")
            # Open device
            ret = self.camera.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
            if ret != 0:
                logger.error(f"❌ Failed to open device. Error: {ret}")
                return False, f"Failed to open device. Error: {ret}"
            
            logger.info("▶️ Starting grabbing...")
            # Start grabbing
            ret = self.camera.MV_CC_StartGrabbing()
            if ret != 0:
                logger.error(f"❌ Failed to start grabbing. Error: {ret}")
                return False, f"Failed to start grabbing. Error: {ret}"
            
            self.is_streaming = True
            self.is_connected = True
            logger.info("✅ Camera connected successfully")
            
            # 🎯 AUTO-ENABLE TRIGGER MODE BY DEFAULT
            logger.info("🎯 Auto-enabling trigger mode by default...")
            try:
                # Stop current grabbing to switch to trigger mode
                ret = self.camera.MV_CC_StopGrabbing()
                if ret != 0:
                    logger.warning(f"Failed to stop grabbing before enabling trigger mode. Error: {ret}")
                
                # Set trigger mode ON
                ret = self.camera.MV_CC_SetEnumValue("TriggerMode", 1)
                if ret != 0:
                    logger.warning(f"Failed to set trigger mode ON. Error: {ret}")
                else:
                    # Set trigger source to Line 0 (external trigger)
                    ret = self.camera.MV_CC_SetEnumValue("TriggerSource", 0)
                    if ret != 0:
                        logger.warning(f"Failed to set trigger source to Line 0. Error: {ret}")
                    
                    # Set trigger activation to Level High
                    ret = self.camera.MV_CC_SetEnumValue("TriggerActivation", 1)
                    if ret != 0:
                        logger.warning(f"Failed to set trigger activation. Error: {ret}")
                    
                    # Start grabbing in trigger mode
                    ret = self.camera.MV_CC_StartGrabbing()
                    if ret != 0:
                        logger.warning(f"Failed to start grabbing in trigger mode. Error: {ret}")
                    else:
                        self.is_trigger_mode = True
                        
                        # Start trigger monitoring thread
                        self.stop_monitoring.clear()
                        self.monitoring_thread = threading.Thread(target=self._monitor_trigger_signal, daemon=True)
                        self.monitoring_thread.start()
                        self.is_monitoring_trigger = True
                        
                        logger.info("🎯 ✅ Trigger mode enabled by default successfully")
                        return True, "Camera connected successfully with trigger mode enabled by default"
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to auto-enable trigger mode: {e}")
                # Fall back to free-running mode if trigger mode fails
                try:
                    ret = self.camera.MV_CC_StartGrabbing()
                    if ret == 0:
                        logger.info("✅ Fallback to free-running mode successful")
                except Exception as fallback_e:
                    logger.error(f"❌ Fallback to free-running mode also failed: {fallback_e}")
            
            return True, "Camera connected successfully"
            
        except Exception as e:
            logger.error(f"❌ Connection exception: {str(e)}")
            return False, f"Connection error: {str(e)}"
    
    def disconnect(self):
        """Disconnect from camera"""
        try:
            # Stop trigger monitoring if active
            if self.is_monitoring_trigger:
                self.disable_trigger_mode()
            
            if self.camera and self.is_streaming:
                self.camera.MV_CC_StopGrabbing()
                self.camera.MV_CC_CloseDevice()
                self.camera.MV_CC_DestroyHandle()
            
            self.is_streaming = False
            self.is_connected = False
            self.is_trigger_mode = False
            return True, "Camera disconnected"
            
        except Exception as e:
            return False, f"Disconnect error: {str(e)}"
    
    def enable_trigger_mode(self):
        """Enable trigger mode for Line 0 detection - based on input_trigger.py"""
        if not self.is_connected:
            return False, "Camera not connected"
        
        try:
            logger.info("🎯 Enabling trigger mode...")
            
            # Stop current grabbing
            if self.is_streaming:
                ret = self.camera.MV_CC_StopGrabbing()
                if ret != 0:
                    logger.warning(f"Failed to stop grabbing before trigger mode. Error: {ret}")
            
            # Set trigger mode ON
            ret = self.camera.MV_CC_SetEnumValue("TriggerMode", 1)
            if ret != 0:
                return False, f"Failed to set trigger mode ON. Error: {ret}"
            
            # Set trigger source to Line 0 (external trigger)
            ret = self.camera.MV_CC_SetEnumValue("TriggerSource", 0)
            if ret != 0:
                logger.warning(f"Failed to set trigger source to Line 0. Error: {ret}")
            
            # Set trigger activation to Level High
            ret = self.camera.MV_CC_SetEnumValue("TriggerActivation", 1)
            if ret != 0:
                logger.warning(f"Failed to set trigger activation. Error: {ret}")
            
            # Start grabbing in trigger mode
            ret = self.camera.MV_CC_StartGrabbing()
            if ret != 0:
                return False, f"Failed to start grabbing in trigger mode. Error: {ret}"
            
            self.is_trigger_mode = True
            self.is_streaming = True
            
            # Start trigger monitoring thread
            self.stop_monitoring.clear()
            self.monitoring_thread = threading.Thread(target=self._monitor_trigger_signal, daemon=True)
            self.monitoring_thread.start()
            self.is_monitoring_trigger = True
            
            logger.info("✅ Trigger mode enabled successfully")
            return True, "Trigger mode enabled successfully. Camera will capture on Line 0 signal."
            
        except Exception as e:
            logger.error(f"❌ Failed to enable trigger mode: {str(e)}")
            return False, f"Failed to enable trigger mode: {str(e)}"
    
    def disable_trigger_mode(self):
        """Disable trigger mode and return to free-running mode"""
        if not self.is_connected:
            return False, "Camera not connected"
        
        try:
            logger.info("🎯 Disabling trigger mode...")
            
            # Stop trigger monitoring
            if self.is_monitoring_trigger:
                self.stop_monitoring.set()
                if self.monitoring_thread and self.monitoring_thread.is_alive():
                    self.monitoring_thread.join(timeout=2.0)
                self.is_monitoring_trigger = False
            
            # Stop grabbing
            if self.is_streaming:
                ret = self.camera.MV_CC_StopGrabbing()
                if ret != 0:
                    logger.warning(f"Failed to stop grabbing. Error: {ret}")
            
            # Set trigger mode OFF (free-running)
            ret = self.camera.MV_CC_SetEnumValue("TriggerMode", 0)
            if ret != 0:
                return False, f"Failed to set trigger mode OFF. Error: {ret}"
            
            # Start grabbing in free-running mode
            ret = self.camera.MV_CC_StartGrabbing()
            if ret != 0:
                return False, f"Failed to start grabbing in free-running mode. Error: {ret}"
            
            self.is_trigger_mode = False
            self.is_streaming = True
            
            logger.info("✅ Trigger mode disabled successfully")
            return True, "Trigger mode disabled. Camera in free-running mode."
            
        except Exception as e:
            logger.error(f"❌ Failed to disable trigger mode: {str(e)}")
            return False, f"Failed to disable trigger mode: {str(e)}"
    
    def _monitor_trigger_signal(self):
        """Monitor trigger signal on Line 0 with enhanced error handling and logging"""
        logger.info("🎯 Started monitoring trigger signal on Line 0")
        logger.info("🎯 IMPORTANT: Line 0 triggers will now execute the FULL 'Capture & Process' workflow")
        
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while not self.stop_monitoring.is_set() and self.is_monitoring_trigger:
            try:
                if not self.is_connected or not self.is_trigger_mode:
                    logger.warning("🎯 Camera disconnected or not in trigger mode, stopping monitoring")
                    break
                
                # Check for trigger signal by attempting to capture
                # In trigger mode, this will only succeed if trigger signal is received
                captured_frame = self._capture_triggered_frame()
                
                if captured_frame is not None:
                    self.trigger_count += 1
                    self.last_trigger_time = datetime.now()
                    
                    logger.info(f"🎯 ⚡ TRIGGER #{self.trigger_count} DETECTED at {self.last_trigger_time.strftime('%H:%M:%S')}")
                    logger.info(f"🎯 ⚡ Initiating FULL workflow (same as 'Capture & Process' button)")
                    
                    # Save triggered image and initiate processing
                    self._save_and_process_triggered_image(captured_frame)
                    
                    # Reset error counter on successful trigger
                    consecutive_errors = 0
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.01)  # 10ms
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Trigger monitoring error #{consecutive_errors}: {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping trigger monitoring")
                    break
                
                time.sleep(0.1)  # Longer delay on error
        
        logger.info("🎯 Stopped monitoring trigger signal")
        self.is_monitoring_trigger = False
    
    def _capture_triggered_frame(self):
        """Capture frame when trigger signal is received"""
        try:
            if not self.is_trigger_mode or not self.is_streaming:
                return None
            
            # Get payload size
            stParam = MVCC_INTVALUE()
            ret = self.camera.MV_CC_GetIntValue("PayloadSize", stParam)
            if ret != 0:
                return None
            
            nPayloadSize = stParam.nCurValue
            
            # Create buffer
            pData = (ctypes.c_ubyte * nPayloadSize)()
            stFrameInfo = MV_FRAME_OUT_INFO_EX()
            
            # Get frame with shorter timeout for trigger mode
            ret = self.camera.MV_CC_GetOneFrameTimeout(pData, nPayloadSize, stFrameInfo, 100)
            if ret != 0:
                return None  # No trigger received
            
            # Convert to numpy array
            frame_width = stFrameInfo.nWidth
            frame_height = stFrameInfo.nHeight
            np_array = np.frombuffer(pData, dtype=np.uint8)
            
            bytes_per_pixel = len(np_array) // (frame_width * frame_height)
            
            if bytes_per_pixel == 1:
                # Grayscale
                image = np_array[:frame_width * frame_height].reshape((frame_height, frame_width))
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif bytes_per_pixel == 3:
                # RGB
                image = np_array[:frame_width * frame_height * 3].reshape((frame_height, frame_width, 3))
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            else:
                # Unknown format, try grayscale
                size = frame_width * frame_height
                if len(np_array) >= size:
                    image = np_array[:size].reshape((frame_height, frame_width))
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                else:
                    return None
            
            return image
            
        except Exception as e:
            logger.error(f"Trigger capture error: {e}")
            return None
    
    def _save_and_process_triggered_image(self, frame):
        """Save triggered image and initiate the SAME processing workflow as 'Capture & Process' button"""
        try:
            # Save the triggered image to the same location as manual captures
            original_dir = os.path.join(settings.MEDIA_ROOT, 'inspections', 'original')
            os.makedirs(original_dir, exist_ok=True)
            
            # Generate filename with trigger count
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            trigger_image_id = f"TRIGGER_{self.trigger_count:04d}_{timestamp}"
            filename = f"{trigger_image_id}_camera.jpg"
            filepath = os.path.join(original_dir, filename)
            
            # Save image
            success = cv2.imwrite(filepath, frame)
            
            if success:
                logger.info(f"💾 Triggered image saved: {filename}")
                
                # Process using the EXACT SAME workflow as the manual "Capture & Process" button
                processing_thread = threading.Thread(
                    target=self._execute_full_capture_and_process_workflow,
                    args=(filepath, filename, trigger_image_id),
                    daemon=True
                )
                processing_thread.start()
                
                return filepath
            else:
                logger.error(f"❌ Failed to save triggered image: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving triggered image: {e}")
            return None
    
    def _execute_full_capture_and_process_workflow(self, image_path, filename, image_id):
        """Execute the EXACT SAME workflow as the manual 'Capture & Process' button"""
        try:
            logger.info(f"🔄 Starting FULL triggered workflow for: {image_id}")
            
            # Import the same processing function used by manual captures
            from .simple_auth_views import _process_with_yolov8_model
            
            # Process with YOLOv8 model (SAME AS MANUAL CAPTURE)
            processing_result = _process_with_yolov8_model(image_path, image_id)
            
            if not processing_result['success']:
                logger.error(f"❌ YOLOv8 processing failed: {processing_result.get('error', 'Unknown error')}")
                return
            
            # Extract results using the same business logic
            detection_data = processing_result['data']
            nut_results = detection_data['nut_results']
            decision = detection_data['decision']
            
            # Use ML decision for counts (SAME AS MANUAL CAPTURE)
            present_count = decision['present_count']
            missing_count = decision['missing_count']
            
            logger.info(f"✅ Triggered ML Results - Present: {present_count}, Missing: {missing_count}")
            
            # Determine individual nut statuses based on ML results (SAME AS MANUAL CAPTURE)
            nut_statuses = ['MISSING', 'MISSING', 'MISSING', 'MISSING']
            
            # Assign PRESENT status based on ML detection
            for nut_key in ['nut1', 'nut2', 'nut3', 'nut4']:
                if nut_key in nut_results and nut_results[nut_key]['status'] == 'PRESENT':
                    nut_index = int(nut_key.replace('nut', '')) - 1
                    nut_statuses[nut_index] = 'PRESENT'
            
            # Overall result based on ML decision
            overall_result = 'PASS' if missing_count == 0 else 'FAIL'
            
            # Get a system user for triggered captures
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Try to get a system user, fallback to first user, or create one
            try:
                system_user = User.objects.filter(username__in=['system', 'trigger', 'auto']).first()
                if not system_user:
                    system_user = User.objects.first()
                if not system_user:
                    # Create a system user if none exists
                    system_user = User.objects.create_user(
                        username='system',
                        email='system@marelli.com',
                        password='system123',
                        role='user'
                    )
            except Exception as user_error:
                logger.error(f"❌ Could not get/create system user: {user_error}")
                return
            
            # Save to database (SAME AS MANUAL CAPTURE)
            from .models import SimpleInspection
            
            inspection = SimpleInspection.objects.create(
                user=system_user,
                image_id=image_id,
                filename=filename,
                overall_result=overall_result,
                nut1_status=nut_statuses[0],
                nut2_status=nut_statuses[1],
                nut3_status=nut_statuses[2],
                nut4_status=nut_statuses[3],
                processing_time=detection_data.get('processing_time', 0.0)
            )
            
            logger.info(f"💾 Triggered inspection saved to database: {inspection.id}")
            
            # Get annotated image path (SAME AS MANUAL CAPTURE)
            annotated_image_path = detection_data.get('annotated_image_path', '')
            
            if annotated_image_path and os.path.exists(annotated_image_path):
                annotated_filename = os.path.basename(annotated_image_path)
            else:
                # Check for existing result files
                results_dir = os.path.join(settings.MEDIA_ROOT, 'inspections', 'results')
                import glob
                pattern = f"{image_id}_*_result.jpg"
                matching_files = glob.glob(os.path.join(results_dir, pattern))
                
                if matching_files:
                    latest_file = max(matching_files, key=os.path.getctime)
                    annotated_filename = os.path.basename(latest_file)
                    annotated_image_path = latest_file
                else:
                    timestamp_new = datetime.now().strftime('%Y%m%d_%H%M%S')
                    annotated_filename = f"{image_id}_{timestamp_new}_result.jpg"
                    annotated_image_path = os.path.join(results_dir, annotated_filename)
            
            # ============================================================================
            # 🆕 ENHANCED FUNCTIONALITY - OK/NG STORAGE (SAME AS MANUAL CAPTURE)
            # ============================================================================
            
            try:
                # Import enhanced storage service
                from .storage_service import EnhancedStorageService
                
                # Initialize storage service
                storage_service = EnhancedStorageService()
                
                # Extract confidence scores for enhanced storage
                confidence_scores = []
                for nut_key in ['nut1', 'nut2', 'nut3', 'nut4']:
                    if nut_key in nut_results:
                        confidence_scores.append(nut_results[nut_key].get('confidence', 0.0))
                
                # Save to enhanced database with OK/NG organization
                enhanced_inspection = storage_service.save_inspection_with_images(
                    user=system_user,
                    image_id=image_id,
                    original_image_path=image_path,
                    annotated_image_path=annotated_image_path,
                    nuts_present=present_count,
                    nuts_absent=missing_count,
                    confidence_scores=confidence_scores,
                    processing_time=detection_data.get('processing_time', 0.0)
                )

                if enhanced_inspection and enhanced_inspection.test_status == 'OK':
                    logger.info(f"🎯 Triggered Status is OK - Initiating file transfer...")
                    logger.info(f"   - QR Code: {enhanced_inspection.image_id}")
                    logger.info(f"   - Inspection ID: {enhanced_inspection.id}")
                    
                    try:
                        from .file_transfer_service import FileTransferService
                        transfer_service = FileTransferService()
                        
                        success, message, details = transfer_service.process_ok_status_change(enhanced_inspection)
                        
                        if success:
                            logger.info(f"✅ Triggered file transfer successful: {message}")
                        else:
                            logger.error(f"❌ Triggered file transfer failed: {message}")
                            
                    except Exception as e:
                        logger.error(f"💥 Triggered file transfer error: {str(e)}")
                
                if enhanced_inspection:
                    logger.info(f"🎯 Triggered enhanced storage: {enhanced_inspection.test_status} folder - {enhanced_inspection.id}")
                    enhanced_storage_success = True
                    enhanced_folder = enhanced_inspection.test_status
                else:
                    logger.warning("Triggered enhanced storage failed, continuing with existing workflow")
                    enhanced_storage_success = False
                    enhanced_folder = 'OK' if missing_count == 0 else 'NG'
                    
            except ImportError:
                logger.warning("Enhanced storage service not available for triggered processing")
                enhanced_storage_success = False
                enhanced_folder = 'OK' if missing_count == 0 else 'NG'
            except Exception as e:
                logger.error(f"Triggered enhanced storage error: {e}")
                enhanced_storage_success = False
                enhanced_folder = 'OK' if missing_count == 0 else 'NG'
            
            # ============================================================================
            # LOG COMPLETE RESULTS (SAME FORMAT AS MANUAL CAPTURE)
            # ============================================================================
            
            logger.info(f"🎯 ✅ TRIGGERED WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info(f"🎯 Image ID: {image_id}")
            logger.info(f"🎯 Overall Result: {overall_result}")
            logger.info(f"🎯 Nuts Present: {present_count}, Missing: {missing_count}")
            logger.info(f"🎯 Enhanced Storage: {enhanced_storage_success}")
            logger.info(f"🎯 Storage Folder: {enhanced_folder}")
            logger.info(f"🎯 Database ID: {inspection.id}")
            
            # Save summary result for potential UI integration
            trigger_summary = {
                'trigger_count': self.trigger_count,
                'image_id': image_id,
                'overall_result': overall_result,
                'present_count': present_count,
                'missing_count': missing_count,
                'enhanced_storage': enhanced_storage_success,
                'storage_folder': enhanced_folder,
                'database_id': str(inspection.id),
                'processed_at': datetime.now().isoformat(),
                'file_transfer_attempted': enhanced_inspection and enhanced_inspection.test_status == 'OK' if enhanced_inspection else False
            }
            
            # Save trigger summary
            summary_path = os.path.join(settings.MEDIA_ROOT, 'camera_captures', 'trigger_summaries')
            os.makedirs(summary_path, exist_ok=True)
            
            summary_filename = f"trigger_summary_{self.trigger_count:04d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            summary_filepath = os.path.join(summary_path, summary_filename)
            
            with open(summary_filepath, 'w') as f:
                json.dump(trigger_summary, f, indent=2, default=str)
            
            logger.info(f"📋 Triggered workflow summary saved: {summary_filename}")
                
        except Exception as e:
            logger.error(f"❌ Error in triggered workflow execution: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
    
    def get_trigger_status(self):
        """Get current trigger mode status with recent processing info"""
        status = {
            'is_trigger_mode': self.is_trigger_mode,
            'is_monitoring': self.is_monitoring_trigger,
            'trigger_count': self.trigger_count,
            'last_trigger_time': self.last_trigger_time.isoformat() if self.last_trigger_time else None
        }
        
        # Add recent trigger processing info
        try:
            # Check for recent trigger summaries
            summary_path = os.path.join(settings.MEDIA_ROOT, 'camera_captures', 'trigger_summaries')
            if os.path.exists(summary_path):
                summary_files = [f for f in os.listdir(summary_path) if f.endswith('.json')]
                if summary_files:
                    # Get most recent summary
                    latest_summary_file = max(summary_files, key=lambda x: os.path.getctime(os.path.join(summary_path, x)))
                    latest_summary_path = os.path.join(summary_path, latest_summary_file)
                    
                    with open(latest_summary_path, 'r') as f:
                        import json
                        latest_summary = json.load(f)
                        status['latest_processing'] = latest_summary
        except Exception as e:
            logger.error(f"Error getting trigger processing info: {e}")
        
        return status
    
    def capture_manual_override(self, save_path=None):
        """Force manual capture even in trigger mode by temporarily switching modes"""
        try:
            logger.info("🎯 Manual capture override requested...")
            
            if not self.is_connected:
                return False, "Camera not connected"
            
            # If in trigger mode, temporarily switch to free-running for manual capture
            was_trigger_mode = self.is_trigger_mode
            
            if was_trigger_mode:
                logger.info("🔄 Temporarily switching to manual mode for capture...")
                
                # Stop monitoring
                if self.is_monitoring_trigger:
                    self.stop_monitoring.set()
                    if self.monitoring_thread and self.monitoring_thread.is_alive():
                        self.monitoring_thread.join(timeout=1.0)
                    self.is_monitoring_trigger = False
                
                # Stop grabbing
                ret = self.camera.MV_CC_StopGrabbing()
                if ret != 0:
                    logger.warning(f"Failed to stop grabbing. Error: {ret}")
                
                # Set to free-running mode
                ret = self.camera.MV_CC_SetEnumValue("TriggerMode", 0)
                if ret != 0:
                    logger.error(f"Failed to set free-running mode. Error: {ret}")
                    return False, f"Failed to set free-running mode. Error: {ret}"
                
                # Start grabbing in free-running mode
                ret = self.camera.MV_CC_StartGrabbing()
                if ret != 0:
                    logger.error(f"Failed to start grabbing in free-running mode. Error: {ret}")
                    return False, f"Failed to start grabbing in free-running mode. Error: {ret}"
                
                self.is_trigger_mode = False
                logger.info("✅ Switched to manual mode for capture")
                
                # Wait a moment for the camera to stabilize
                time.sleep(0.5)
            
            # Capture the image
            result = self.capture_image(save_path)
            
            # If we were in trigger mode, switch back
            if was_trigger_mode:
                logger.info("🔄 Switching back to trigger mode...")
                
                # Stop grabbing
                ret = self.camera.MV_CC_StopGrabbing()
                if ret != 0:
                    logger.warning(f"Failed to stop grabbing. Error: {ret}")
                
                # Set trigger mode back ON
                ret = self.camera.MV_CC_SetEnumValue("TriggerMode", 1)
                if ret != 0:
                    logger.error(f"Failed to restore trigger mode. Error: {ret}")
                else:
                    # Set trigger source back to Line 0
                    ret = self.camera.MV_CC_SetEnumValue("TriggerSource", 0)
                    if ret != 0:
                        logger.warning(f"Failed to set trigger source back to Line 0. Error: {ret}")
                    
                    # Set trigger activation back to Level High
                    ret = self.camera.MV_CC_SetEnumValue("TriggerActivation", 1)
                    if ret != 0:
                        logger.warning(f"Failed to set trigger activation. Error: {ret}")
                    
                    # Start grabbing in trigger mode
                    ret = self.camera.MV_CC_StartGrabbing()
                    if ret != 0:
                        logger.error(f"Failed to start grabbing in trigger mode. Error: {ret}")
                    else:
                        self.is_trigger_mode = True
                        
                        # Restart trigger monitoring
                        self.stop_monitoring.clear()
                        self.monitoring_thread = threading.Thread(target=self._monitor_trigger_signal, daemon=True)
                        self.monitoring_thread.start()
                        self.is_monitoring_trigger = True
                        
                        logger.info("✅ Restored trigger mode")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Manual capture override error: {str(e)}")
            return False, f"Manual capture override error: {str(e)}"
    
    def test_trigger_workflow_manually(self):
        """Test the trigger workflow manually (for debugging purposes)"""
        try:
            logger.info("🧪 Testing trigger workflow manually...")
            
            if not self.is_connected:
                return False, "Camera not connected"
            
            # Capture a frame manually
            frame = self.get_frame()
            if frame is None:
                return False, "Failed to capture test frame"
            
            # Simulate a trigger event
            self.trigger_count += 1
            self.last_trigger_time = datetime.now()
            
            logger.info(f"🧪 Simulating trigger #{self.trigger_count} for testing")
            
            # Execute the same workflow as a real trigger
            self._save_and_process_triggered_image(frame)
            
            return True, f"Test trigger workflow initiated successfully (trigger #{self.trigger_count})"
            
        except Exception as e:
            logger.error(f"❌ Test trigger workflow error: {str(e)}")
            return False, f"Test trigger workflow error: {str(e)}"
    
    def get_frame(self):
        """Get current frame from camera"""
        try:
            if not self.is_connected:
                logger.error("❌ Camera not connected")
                return None
                
            if not self.is_streaming:
                logger.error("❌ Camera not streaming")
                return None
            
            # Get payload size
            stParam = MVCC_INTVALUE()
            ret = self.camera.MV_CC_GetIntValue("PayloadSize", stParam)
            if ret != 0:
                logger.error(f"❌ Failed to get payload size. Error: {ret}")
                return None
            
            nPayloadSize = stParam.nCurValue
            logger.debug(f"📏 Payload size: {nPayloadSize}")
            
            # Get image dimensions
            stWidth = MVCC_INTVALUE()
            stHeight = MVCC_INTVALUE()
            ret_width = self.camera.MV_CC_GetIntValue("Width", stWidth)
            ret_height = self.camera.MV_CC_GetIntValue("Height", stHeight)
            
            if ret_width != 0 or ret_height != 0:
                logger.warning(f"⚠️ Failed to get image dimensions. Width ret: {ret_width}, Height ret: {ret_height}")
            
            # Create buffer
            import ctypes
            pData = (ctypes.c_ubyte * nPayloadSize)()
            stFrameInfo = MV_FRAME_OUT_INFO_EX()
            
            # Get frame with appropriate timeout and better error handling
            timeout_ms = 100  # Short timeout for free-running mode
            
            # In trigger mode, don't try to get frames for streaming
            if self.is_trigger_mode:
                logger.debug("🎯 Camera in trigger mode - no frames available for streaming")
                return None
            
            ret = self.camera.MV_CC_GetOneFrameTimeout(pData, nPayloadSize, stFrameInfo, timeout_ms)
            if ret != 0:
                # Common Hikrobot error codes
                if ret == -2147483612:  # MV_E_TIMEOUT
                    logger.debug("⏱️ Frame timeout (normal when no frames available)")
                elif ret == 2147483655:  # MV_E_NOENOUGH_BUF or similar buffer error
                    logger.debug("📦 Buffer error (normal in trigger mode)")
                elif ret == -2147483634:  # Device not ready
                    logger.debug("📷 Device not ready")
                else:
                    logger.debug(f"⚠️ Frame not available. Error: {ret}")
                return None
            
            # Convert to numpy array
            frame_width = stFrameInfo.nWidth
            frame_height = stFrameInfo.nHeight
            logger.debug(f"📐 Frame dimensions: {frame_width}x{frame_height}")
            
            np_array = np.frombuffer(pData, dtype=np.uint8)
            
            if len(np_array) == 0:
                logger.error("❌ Empty frame data")
                return None
            
            bytes_per_pixel = len(np_array) // (frame_width * frame_height)
            logger.debug(f"🎨 Bytes per pixel: {bytes_per_pixel}")
            
            if bytes_per_pixel == 1:
                # Grayscale
                image = np_array[:frame_width * frame_height].reshape((frame_height, frame_width))
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif bytes_per_pixel == 3:
                # RGB
                image = np_array[:frame_width * frame_height * 3].reshape((frame_height, frame_width, 3))
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            else:
                # Unknown format, try grayscale
                size = frame_width * frame_height
                if len(np_array) >= size:
                    logger.warning(f"⚠️ Unknown pixel format ({bytes_per_pixel} bytes/pixel), trying grayscale")
                    image = np_array[:size].reshape((frame_height, frame_width))
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                else:
                    logger.error(f"❌ Insufficient data for frame: {len(np_array)} < {size}")
                    return None
            
            with self.frame_lock:
                self.current_frame = image.copy()
            
            logger.debug(f"✅ Frame captured successfully: {image.shape}")
            return image
            
        except Exception as e:
            logger.error(f"❌ Frame capture error: {e}")
            return None
    
    def capture_image(self, save_path=None):
        """Capture and save a single image"""
        try:
            logger.info("📸 Starting image capture...")
            
            if not self.is_connected:
                logger.error("❌ Camera not connected")
                return False, "Camera not connected"
            
            # If in trigger mode, temporarily switch to manual capture or use software trigger
            if self.is_trigger_mode:
                logger.info("🎯 Camera in trigger mode - using software trigger for manual capture")
                frame = self._capture_with_software_trigger()
            else:
                logger.info("📷 Camera in free-running mode - capturing frame")
                frame = self.get_frame()
            
            if frame is None:
                logger.error("❌ Failed to capture frame")
                return False, "Failed to capture frame"
            
            logger.info(f"✅ Frame captured successfully - Shape: {frame.shape}")
            
            if save_path is None:
                save_path = os.path.join(settings.MEDIA_ROOT, 'captures')
            
            # Create save directory if it doesn't exist
            os.makedirs(save_path, exist_ok=True)
            logger.info(f"📁 Save path: {save_path}")
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
            filename = f"hikrobot_capture_{timestamp}.jpg"
            filepath = os.path.join(save_path, filename)
            
            # Save image
            success = cv2.imwrite(filepath, frame)
            
            if success:
                file_size = os.path.getsize(filepath)
                logger.info(f"💾 Image saved successfully: {filename} ({file_size} bytes)")
                return True, {
                    'filename': filename,
                    'filepath': filepath,
                    'size': file_size,
                    'timestamp': timestamp
                }
            else:
                logger.error("❌ Failed to save image")
                return False, "Failed to save image"
                
        except Exception as e:
            logger.error(f"❌ Capture error: {str(e)}")
            return False, f"Capture error: {str(e)}"
    
    def _capture_with_software_trigger(self):
        """Capture frame using software trigger when in trigger mode"""
        try:
            if not self.is_connected or not self.is_streaming:
                logger.error("❌ Camera not ready for software trigger")
                return None
            
            logger.info("🎯 Sending software trigger...")
            
            # Send software trigger
            ret = self.camera.MV_CC_SetCommandValue("TriggerSoftware")
            if ret != 0:
                logger.error(f"❌ Failed to send software trigger. Error: {ret}")
                return None
            
            # Wait a bit for the trigger to process
            time.sleep(0.1)
            
            # Get the triggered frame
            frame = self.get_frame()
            if frame is not None:
                logger.info("✅ Software trigger capture successful")
            else:
                logger.error("❌ Software trigger capture failed")
            
            return frame
            
        except Exception as e:
            logger.error(f"❌ Software trigger error: {str(e)}")
            return None


# Global camera manager instance
camera_manager = HikrobotCameraManager()


# Camera API Views
@csrf_exempt
@require_http_methods(["POST"])
def connect_camera(request):
    """Connect to Hikrobot camera"""
    success, message = camera_manager.connect()
    return JsonResponse({
        'success': success,
        'message': message,
        'connected': camera_manager.is_connected
    })


@csrf_exempt
@require_http_methods(["POST"])
def disconnect_camera(request):
    """Disconnect from camera"""
    success, message = camera_manager.disconnect()
    return JsonResponse({
        'success': success,
        'message': message,
        'connected': camera_manager.is_connected
    })


@csrf_exempt
@require_http_methods(["GET"])
def camera_status(request):
    """Get camera connection status including trigger mode"""
    status_data = {
        'connected': camera_manager.is_connected,
        'streaming': camera_manager.is_streaming,
        'sdk_available': HIKROBOT_AVAILABLE
    }
    
    # Add trigger mode status if camera is connected
    if camera_manager.is_connected:
        trigger_status = camera_manager.get_trigger_status()
        status_data.update(trigger_status)
    
    return JsonResponse(status_data)


@csrf_exempt
@require_http_methods(["POST"])
def capture_photo(request):
    """Capture a single photo"""
    if not camera_manager.is_connected:
        return JsonResponse({
            'success': False,
            'message': 'Camera not connected'
        })
    
    try:
        # Get save path from request or use default
        data = json.loads(request.body) if request.body else {}
        save_path = data.get('save_path', os.path.join(settings.MEDIA_ROOT, 'captures'))
        
        success, result = camera_manager.capture_image(save_path)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Photo captured successfully',
                'data': result
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


def generate_frames():
    """Generate frames for video streaming with trigger mode awareness"""
    while True:
        if camera_manager.is_connected and camera_manager.is_streaming:
            # In trigger mode, show appropriate message
            if camera_manager.is_trigger_mode:
                # Show trigger mode status
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                
                # Add trigger mode info
                cv2.putText(placeholder, 'TRIGGER MODE ACTIVE', (180, 200), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.putText(placeholder, 'Waiting for Line 0 signal...', (150, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 215, 255), 2)
                
                if camera_manager.trigger_count > 0:
                    cv2.putText(placeholder, f'Triggers: {camera_manager.trigger_count}', (250, 280), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                _, buffer = cv2.imencode('.jpg', placeholder, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_bytes = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # Free-running mode - try to get actual frame
                frame = camera_manager.get_frame()
                if frame is not None:
                    # Encode frame as JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    frame_bytes = buffer.tobytes()
                    
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                else:
                    # Send placeholder frame if no camera frame available
                    placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(placeholder, 'MANUAL MODE', (220, 220), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(placeholder, 'No frame available', (190, 260), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 215, 255), 2)
                    _, buffer = cv2.imencode('.jpg', placeholder)
                    frame_bytes = buffer.tobytes()
                    
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            # Send "disconnected" frame
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder, 'Camera Disconnected', (180, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            _, buffer = cv2.imencode('.jpg', placeholder)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.1)  # 10 FPS to reduce CPU usage


def video_stream(request):
    """Stream video from camera"""
    return StreamingHttpResponse(
        generate_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


@csrf_exempt
@require_http_methods(["GET"])
def get_current_frame_base64(request):
    """Get current frame as base64 encoded image"""
    if not camera_manager.is_connected:
        return JsonResponse({
            'success': False,
            'message': 'Camera not connected'
        })
    
    try:
        frame = camera_manager.get_frame()
        if frame is not None:
            # Encode frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return JsonResponse({
                'success': True,
                'image': f'data:image/jpeg;base64,{img_base64}',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No frame available'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


# NEW: Trigger Mode API Endpoints
@csrf_exempt
@require_http_methods(["POST"])
def enable_trigger_mode(request):
    """Enable trigger mode for Line 0 detection"""
    if not camera_manager.is_connected:
        return JsonResponse({
            'success': False,
            'message': 'Camera not connected'
        })
    
    success, message = camera_manager.enable_trigger_mode()
    status_data = camera_manager.get_trigger_status()
    
    return JsonResponse({
        'success': success,
        'message': message,
        'trigger_status': status_data
    })


@csrf_exempt
@require_http_methods(["POST"])
def disable_trigger_mode(request):
    """Disable trigger mode and return to free-running"""
    if not camera_manager.is_connected:
        return JsonResponse({
            'success': False,
            'message': 'Camera not connected'
        })
    
    success, message = camera_manager.disable_trigger_mode()
    status_data = camera_manager.get_trigger_status()
    
    return JsonResponse({
        'success': success,
        'message': message,
        'trigger_status': status_data
    })


@csrf_exempt
@require_http_methods(["GET"])
def get_trigger_status(request):
    """Get trigger mode status"""
    if not camera_manager.is_connected:
        return JsonResponse({
            'success': False,
            'message': 'Camera not connected'
        })
    
    status_data = camera_manager.get_trigger_status()
    return JsonResponse({
        'success': True,
        'trigger_status': status_data
    })


@csrf_exempt  
@require_http_methods(["GET"])
def get_recent_trigger_results(request):
    """Get recent trigger results for notification system"""
    try:
        from .models import SimpleInspection
        
        # Get recent triggered inspections (last 10, within last hour)
        from datetime import datetime, timedelta
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        recent_inspections = SimpleInspection.objects.filter(
            image_id__startswith='TRIGGER_',
            created_at__gte=one_hour_ago
        ).order_by('-created_at')[:10]
        
        results = []
        for inspection in recent_inspections:
            results.append({
                'id': inspection.id,
                'image_id': inspection.image_id,
                'overall_result': inspection.overall_result,
                'present_count': sum([
                    1 for status in [inspection.nut1_status, inspection.nut2_status, 
                                   inspection.nut3_status, inspection.nut4_status] 
                    if status == 'PRESENT'
                ]),
                'missing_count': sum([
                    1 for status in [inspection.nut1_status, inspection.nut2_status,
                                   inspection.nut3_status, inspection.nut4_status]
                    if status == 'MISSING'  
                ]),
                'timestamp': inspection.created_at.isoformat(),
                'processing_time': inspection.processing_time
            })
        
        return JsonResponse({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error getting trigger results: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'results': []
        })


@csrf_exempt
@require_http_methods(["POST"])
def test_trigger_workflow(request):
    """Test the trigger workflow manually (for debugging)"""
    if not camera_manager.is_connected:
        return JsonResponse({
            'success': False,
            'message': 'Camera not connected'
        })
    
    success, message = camera_manager.test_trigger_workflow_manually()
    return JsonResponse({
        'success': success,
        'message': message,
        'trigger_count': camera_manager.trigger_count
    })


def camera_control_page(request):
    """
    Render the HTML page for camera control
    """
    return render(request, 'ml_api/camera_control.html')