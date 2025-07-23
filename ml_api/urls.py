# ml_api/urls.py - Updated with Complete Image ID Workflow + CAMERA INTEGRATION

from django.urls import path

# Updated simple authentication views with Image ID workflow
# Add this to your existing imports
from .simple_auth_views import (
    simple_login_view,
    simple_logout_view,
    simple_admin_dashboard,
    simple_user_dashboard,
    simple_workflow_page,
    simple_process_image,
    # New Image ID workflow views
    image_id_entry_view,
    validate_image_id,
    qr_scanner_endpoint,
    image_source_selection_view,
    results_display_view,
    # 📷 NEW: Camera integration views
    camera_capture_view,
    camera_capture_and_process,
    # 🆕 NEW: Enhanced Authentication views
    simple_signup_view,
    inspection_list_view,
    update_inspection_status_view,
    # 🆕 NEW: Add these file transfer imports
    file_transfer_dashboard,
    retry_failed_transfers,
    test_file_transfer_system,
    # 🔒 NEW: Override authentication
    override_authentication_view,
)

# Keep your working detection endpoints
from .views import (
    NutDetectionView, 
    detection_page,
    # Camera functionality imports
    connect_camera,
    disconnect_camera,
    camera_status,
    capture_photo,
    video_stream,
    get_current_frame_base64,
    camera_control_page,
    # Trigger mode imports
    enable_trigger_mode,
    disable_trigger_mode,
    get_trigger_status,
    test_trigger_workflow,
    get_recent_trigger_results
)

app_name = 'ml_api'

urlpatterns = [
    # 🏠 AUTHENTICATION SYSTEM
    path('', simple_login_view, name='simple_login'),
    path('login/', simple_login_view, name='simple_login'),
    path('logout/', simple_logout_view, name='simple_logout'),
    # 🆕 NEW: Enhanced Authentication
    path('signup/', simple_signup_view, name='simple_signup'),
    
    # 📊 DASHBOARDS (Role-based)
    path('admin-dashboard/', simple_admin_dashboard, name='simple_admin_dashboard'),
    path('user-dashboard/', simple_user_dashboard, name='simple_user_dashboard'),
    # 🆕 NEW: Inspection Management
    path('inspections/', inspection_list_view, name='inspection_list'),
    path('inspection/<uuid:inspection_id>/update-status/', update_inspection_status_view, name='update_inspection_status'),
    
    # 🆕 NEW: File Transfer Management URLs
    path('file-transfer-dashboard/', file_transfer_dashboard, name='file_transfer_dashboard'),
    path('retry-failed-transfers/', retry_failed_transfers, name='retry_failed_transfers'),
    path('test-file-transfer/', test_file_transfer_system, name='test_file_transfer'),
    path('override-auth/', override_authentication_view, name='override_auth'),

     
    # 🏭 COMPLETE IMAGE WORKFLOW (Your Problem Statement Requirements)
    # Step 1: Image ID Entry (Manual/QR Scanner)
    path('image-id/', image_id_entry_view, name='image_id_entry'),
    path('validate-image-id/', validate_image_id, name='validate_image_id'),
    path('qr-scan/', qr_scanner_endpoint, name='qr_scanner'),
    
    # Step 2: Image Source Selection (Upload/Camera)
    path('image-source/', image_source_selection_view, name='image_source_selection'),
    
    # 📷 Step 2B: CAMERA CAPTURE (NEW - Integrated into workflow)
    path('camera-capture/', camera_capture_view, name='camera_capture'),
    path('camera/capture-and-process/', camera_capture_and_process, name='camera_capture_and_process'),
    
    # Step 3 & 4: Processing and Results
    path('process-image/', simple_process_image, name='simple_process_image'),
    # Step 4: Results Display
    path('results/', results_display_view, name='results_display'),
    
    # 🎯 WORKFLOW ENTRY POINTS
    path('workflow/', simple_workflow_page, name='simple_workflow'),  # Redirects to image-id/
    path('start/', image_id_entry_view, name='start_workflow'),  # Direct entry point
    
    # 🔧 LEGACY/WORKING ENDPOINTS (Keep for compatibility)
    path('health/', NutDetectionView.as_view(), name='health_check'),
    path('detect-nuts/', NutDetectionView.as_view(), name='detect_nuts'),
    path('detection/', detection_page, name='detection_page'),
    
    # 📷 CAMERA CONTROL ENDPOINTS (Added functionality)
    path('camera/connect/', connect_camera, name='connect_camera'),
    path('camera/disconnect/', disconnect_camera, name='disconnect_camera'),
    path('camera/status/', camera_status, name='camera_status'),
    path('camera/capture/', capture_photo, name='capture_photo'),
    path('camera/frame/', get_current_frame_base64, name='get_frame'),
    path('camera/stream/', video_stream, name='video_stream'),
    path('camera/', camera_control_page, name='camera_control'),
    
    # 🎯 TRIGGER MODE ENDPOINTS (NEW)
    path('camera/trigger/enable/', enable_trigger_mode, name='enable_trigger_mode'),
    path('camera/trigger/disable/', disable_trigger_mode, name='disable_trigger_mode'),
    path('camera/trigger/status/', get_trigger_status, name='get_trigger_status'),
    path('camera/trigger/test/', test_trigger_workflow, name='test_trigger_workflow'),
    path('trigger/recent-results/', get_recent_trigger_results, name='get_recent_trigger_results'),

    
]