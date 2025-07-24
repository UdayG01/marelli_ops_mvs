# ml_api/simple_auth_views.py - CAMERA INTEGRATION ADDED

import os
import glob
from django.conf import settings

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import re
from datetime import datetime
import os  # For os.path.basename()
from .models import CustomUser, SimpleInspection

from django.contrib.auth import get_user_model
from django.db import transaction
import json
from django.http import JsonResponse
from .file_transfer_service import FileTransferService
from .models import CustomUser, SimpleInspection, InspectionRecord  # 🆕 Add InspectionRecord

# CSRF Test View for debugging
def csrf_test_view(request):
    """Test page for debugging CSRF token issues"""
    context = {
        'csrf_token': request.META.get('CSRF_COOKIE'),
        'session_key': request.session.session_key,
        'post_data': dict(request.POST) if request.method == 'POST' else None,
    }
    return render(request, 'ml_api/csrf_test.html', context)


# 🎯 PREDEFINED ADMIN ACCOUNTS - YOU CAN EDIT THIS SECTION
PREDEFINED_ADMINS = {
    'admin': 'admin123',           # username: password
    'supervisor': 'super123',      # username: password
    'manager': 'manager123',       # username: password
    # ADD MORE ADMIN ACCOUNTS HERE AS NEEDED
}

def simple_login_view(request):
    """
    Enhanced login view handling both login and signup forms - EMPLOYEE ONLY INTERFACE
    """
    # Add CSRF debugging
    if request.method == 'POST':
        print(f"🔍 POST request received")
        print(f"🔍 CSRF Token in POST: {request.POST.get('csrfmiddlewaretoken', 'NOT FOUND')}")
        print(f"🔍 Session Key: {request.session.session_key}")
        print(f"🔍 Session CSRF Token: {request.session.get('_csrftoken', 'NOT FOUND')}")
        
        form_type = request.POST.get('form_type', 'login')
        
        # Handle signup form submission
        if form_type == 'signup':
            return handle_signup_form(request)
        
        # Handle login form submission - MODIFIED FOR EMPLOYEE INTERFACE
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # 🆕 NEW: Check if this is a predefined admin
        is_admin = False
        if username in PREDEFINED_ADMINS and password == PREDEFINED_ADMINS[username]:
            is_admin = True
            print(f"🔑 Admin login detected: {username}")
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # 🆕 NEW: Auto-promote predefined admins
            if is_admin and user.role != 'admin':
                user.role = 'admin'
                user.save()
                print(f"👑 User {username} promoted to admin")
            
            login(request, user)
            
            # Redirect based on role (existing logic)
            if user.role == 'admin':
                return redirect('ml_api:simple_admin_dashboard')
            else:
                return redirect('ml_api:simple_user_dashboard')
        else:
            # 🆕 NEW: Special handling for predefined admins not in database
            if is_admin:
                try:
                    # Create admin user if doesn't exist
                    user = CustomUser.objects.create_user(
                        username=username,
                        password=password,
                        email=f"{username}@company.com",  # Default email
                        role='admin'
                    )
                    login(request, user)
                    messages.success(request, f'Admin account created and logged in: {username}')
                    return redirect('ml_api:simple_admin_dashboard')
                except Exception as e:
                    messages.error(request, f'Error creating admin account: {str(e)}')
            else:
                messages.error(request, 'Invalid username or password.')
    
    return render(request, 'ml_api/simple_login.html')


def handle_signup_form(request):
    """
    Handle signup form processing
    """
    username = request.POST.get('username')
    email = request.POST.get('email')
    password1 = request.POST.get('password1')
    password2 = request.POST.get('password2')
    role = 'user'  # 🆕 NEW: All signups default to 'user' role
    employee_id = request.POST.get('employee_id', '')
    
    # Validation
    if password1 != password2:
        messages.error(request, 'Passwords do not match.')
        return render(request, 'ml_api/simple_login.html')
    
    if len(password1) < 8:
        messages.error(request, 'Password must be at least 8 characters long.')
        return render(request, 'ml_api/simple_login.html')
    
    # Check if username already exists
    if CustomUser.objects.filter(username=username).exists():
        messages.error(request, 'Username already exists.')
        return render(request, 'ml_api/simple_login.html')

# 🆕 NEW: Prevent signup with admin usernames
    if username in PREDEFINED_ADMINS:
        messages.error(request, 'This username is reserved. Please choose a different username.')
        return render(request, 'ml_api/simple_login.html')
    
    # Check if email already exists
    if CustomUser.objects.filter(email=email).exists():
        messages.error(request, 'Email already registered.')
        return render(request, 'ml_api/simple_login.html')
    
    try:
        # Create user
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password1,
            role=role,
            employee_id=employee_id
        )
        
        messages.success(request, f'Account created successfully! Please sign in.')
        return render(request, 'ml_api/simple_login.html')
        
    except Exception as e:
        messages.error(request, f'Error creating account: {str(e)}')
        return render(request, 'ml_api/simple_login.html')

def simple_signup_view(request):
    """
    Dedicated signup view (redirect to main login page)
    """
    return redirect('ml_api:simple_login')

@login_required
def update_inspection_status_view(request, inspection_id):
    """
    Update inspection status (OK/NG) with role-based permissions
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status')  # 'OK' or 'NG'
            
            if new_status not in ['OK', 'NG']:
                return JsonResponse({'success': False, 'error': 'Invalid status'})
            
            # Get the inspection record
            try:
                inspection = InspectionRecord.objects.get(id=inspection_id)
            except InspectionRecord.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Inspection not found'})
            
            # Permission check
            if request.user.role == 'user':
                # Users can only change status of their own current images
                if inspection.user != request.user:
                    return JsonResponse({
                        'success': False, 
                        'error': 'Permission denied: You can only modify your own inspections'
                    })
                
                # Check if this is the latest inspection (current image)
                latest_inspection = InspectionRecord.objects.filter(
                    user=request.user
                ).order_by('-capture_datetime').first()
                
                if latest_inspection and inspection.id != latest_inspection.id:
                    return JsonResponse({
                        'success': False, 
                        'error': 'Permission denied: You can only modify your current/latest inspection'
                    })
            
            elif request.user.role == 'admin':
                # Admins can change any inspection status
                pass
            else:
                return JsonResponse({'success': False, 'error': 'Insufficient permissions'})
            
            # Update the status
            old_status = inspection.test_status
            inspection.test_status = new_status
            
            # Update nuts count based on status
            if new_status == 'OK':
                inspection.nuts_present = 4
                inspection.nuts_absent = 0
            else:  # NG
                # Keep existing counts or set default
                if inspection.nuts_present + inspection.nuts_absent != 4:
                    inspection.nuts_present = 3  # Example default
                    inspection.nuts_absent = 1
            
            inspection.save()
            
            # 🆕 NEW: FILE TRANSFER INTEGRATION - ADD THIS SECTION
            transfer_result = None
            if new_status == 'OK':
                print(f"\n🎯 Status changed to OK - Initiating file transfer...")
                print(f"   - QR Code: {inspection.image_id}")
                print(f"   - Changed by: {request.user.username} ({request.user.role})")
                
                try:
                    # Initialize file transfer service
                    transfer_service = FileTransferService()
                    
                    # Process the OK status change
                    transfer_success, transfer_message, transfer_details = transfer_service.process_ok_status_change(inspection)
                    
                    if transfer_success:
                        print(f"✅ File transfer successful: {transfer_message}")
                        transfer_result = {
                            'success': True,
                            'message': transfer_message,
                            'details': transfer_details
                        }
                    else:
                        print(f"❌ File transfer failed: {transfer_message}")
                        transfer_result = {
                            'success': False,
                            'message': transfer_message,
                            'details': transfer_details
                        }
                        
                except Exception as e:
                    error_msg = f"File transfer error: {str(e)}"
                    print(f"💥 {error_msg}")
                    transfer_result = {
                        'success': False,
                        'message': error_msg,
                        'details': {'error': str(e)}
                    }
            
            # ENHANCED RESPONSE WITH TRANSFER INFO
            response_data = {
                'success': True, 
                'message': f'Status updated from {old_status} to {new_status}',
                'new_status': new_status,
                'updated_by': request.user.username,
                'user_role': request.user.role
            }
            
            # Add transfer result if applicable
            if transfer_result:
                response_data['file_transfer'] = transfer_result
                
                # Add user-friendly message
                if transfer_result['success']:
                    response_data['message'] += f" and .nip file sent to external server"
                else:
                    response_data['message'] += f" but .nip file transfer failed"
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

@login_required
def inspection_list_view(request):
    """
    View inspection list with status toggle capability
    """
    if request.user.role == 'admin':
        # Admins see all inspections
        inspections = InspectionRecord.objects.all().order_by('-capture_datetime')[:50]
    else:
        # Users see only their inspections
        inspections = InspectionRecord.objects.filter(
            user=request.user
        ).order_by('-capture_datetime')[:20]
    
    context = {
        'inspections': inspections,
        'user_role': request.user.role,
    }
    
    return render(request, 'ml_api/inspection_list.html', context)


@login_required
def simple_admin_dashboard(request):
    """
    Simple Admin Dashboard
    """
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('ml_api:simple_user_dashboard')
    
    # Get basic statistics
    total_users = CustomUser.objects.count()
    total_inspections = SimpleInspection.objects.count()
    recent_inspections = SimpleInspection.objects.order_by('-created_at')[:10]
    failed_inspections = SimpleInspection.objects.filter(overall_result='FAIL').count()
    
    # Recent activity (last 24 hours)
    from django.utils import timezone
    yesterday = timezone.now() - timezone.timedelta(days=1)
    recent_count = SimpleInspection.objects.filter(created_at__gte=yesterday).count()
    
    context = {
        'total_users': total_users,
        'total_inspections': total_inspections,
        'failed_inspections': failed_inspections,
        'recent_inspections': recent_inspections,
        'recent_count': recent_count,
    }
    
    return render(request, 'ml_api/simple_admin_dashboard.html', context)

@login_required
def simple_user_dashboard(request):
    """
    Simple User Dashboard
    """
    # Get user's inspections
    user_inspections = SimpleInspection.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]
    
    # Get user's failed inspections
    failed_inspections = SimpleInspection.objects.filter(
        user=request.user,
        overall_result='FAIL'
    ).order_by('-created_at')[:10]
    
    # 🆕 ADD: Get today's inspections count
    from django.utils import timezone
    today = timezone.now().date()
    today_inspections = SimpleInspection.objects.filter(
        user=request.user,
        created_at__date=today
    ).count()
    
    context = {
        'user_inspections': user_inspections,
        'failed_inspections': failed_inspections,
        'today_inspections': today_inspections,  # 🆕 NEW: Add this line
    }
    
    return render(request, 'ml_api/simple_user_dashboard.html', context)

@login_required
def image_id_entry_view(request):
    """
    Step 1: Image ID Entry - Manual input or QR scan
    """
    return render(request, 'ml_api/image_id_entry.html')

@login_required
def validate_image_id(request):
    """
    AJAX endpoint to validate Image ID format
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_id = data.get('image_id', '').strip()
            
            # Validate Image ID format
            validation_result = _validate_image_id_format(image_id)
            
            return JsonResponse(validation_result)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Method not allowed'
    })

@csrf_exempt
@login_required
def qr_scanner_endpoint(request):
    """
    QR Scanner endpoint for RS-232 integration
    """
    if request.method == 'POST':
        try:
            # Get scanned data from RS-232 (currently simulated)
            scanned_data = request.POST.get('scanned_data', '').strip()
            
            if not scanned_data:
                return JsonResponse({
                    'success': False,
                    'error': 'No QR data received'
                })
            
            # Validate scanned QR data
            validation_result = _validate_image_id_format(scanned_data)
            
            if validation_result['valid']:
                # Log QR scan for audit trail
                # Could add QRScanLog model here if needed
                
                return JsonResponse({
                    'success': True,
                    'image_id': scanned_data,
                    'source': 'QR_Scanner',
                    'timestamp': datetime.now().isoformat(),
                    'message': f'Successfully scanned: {scanned_data}'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid QR code format: {validation_result["message"]}'
                })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Method not allowed'
    })

# Step 1: Update simple_auth_views.py - Modify image_source_selection_view to redirect directly to camera

@login_required
def image_source_selection_view(request):
    """
    Step 2: DIRECT REDIRECT TO CAMERA (Modified)
    Skip source selection - go directly to camera capture
    """
    # Get Image ID from query parameter
    image_id = request.GET.get('image_id', '')
    
    if not image_id:
        messages.error(request, 'No Image ID provided. Please start from Image ID entry.')
        return redirect('ml_api:image_id_entry')
    
    # Validate Image ID format
    validation_result = _validate_image_id_format(image_id)
    if not validation_result['valid']:
        messages.error(request, f'Invalid Image ID: {validation_result["message"]}')
        return redirect('ml_api:image_id_entry')
    
    # DIRECT REDIRECT TO CAMERA CAPTURE (NO SOURCE SELECTION)
    return redirect(f'/api/ml/camera-capture/?image_id={image_id}')

# Step 2: Simplified Camera Capture Template - Remove unnecessary elements

# 📷 NEW: CAMERA CAPTURE VIEW FOR WORKFLOW INTEGRATION
@login_required
def camera_capture_view(request):
    """
    CAMERA CAPTURE PAGE - Integrated into workflow
    Shows live preview and capture button
    After capture -> automatically processes with ML model
    ENHANCED: Support trigger mode without requiring image ID
    """
    # Get Image ID from query parameter
    image_id = request.GET.get('image_id', '')
    trigger_mode = request.GET.get('trigger_mode', '0') == '1'
    
    # Handle trigger mode - no image ID required
    if trigger_mode:
        print("🎯 Camera capture in trigger mode - waiting for Line 0 trigger")
        context = {
            'image_id': '',  # Empty for trigger mode
            'trigger_mode': True,
        }
        return render(request, 'ml_api/camera_capture.html', context)
    
    # Handle manual mode - image ID required
    if not image_id:
        messages.error(request, 'No Image ID provided. Please start from Image ID entry.')
        return redirect('ml_api:image_id_entry')
    
    # Validate Image ID format
    validation_result = _validate_image_id_format(image_id)
    if not validation_result['valid']:
        messages.error(request, f'Invalid Image ID: {validation_result["message"]}')
        return redirect('ml_api:image_id_entry')
    
    # Check for duplicate Image ID
    if SimpleInspection.objects.filter(image_id=image_id).exists():
        messages.error(request, f'Image ID "{image_id}" already exists. Please use a different ID.')
        return redirect('ml_api:image_id_entry')

    context = {
        'image_id': image_id,
        'trigger_mode': False,
    }
    
    return render(request, 'ml_api/camera_capture.html', context)# ml_api/simple_auth_views.py - ENHANCED camera_capture_and_process function
# Replace your existing function with this enhanced version

@csrf_exempt
@login_required
def camera_capture_and_process(request):
    """
    ENHANCED CAMERA CAPTURE + ML PROCESSING - Complete workflow with OK/NG storage
    1. Capture image from camera
    2. Save to original directory
    3. Process with ML model
    4. Save results to database
    5. ENHANCED: Organize images into OK/NG folders
    6. ENHANCED: Save to InspectionRecord database
    7. Return results
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_id = data.get('image_id', '').strip()
            
            # Validate Image ID
            if not image_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Image ID is required'
                })
            
            validation_result = _validate_image_id_format(image_id)
            if not validation_result['valid']:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid Image ID: {validation_result["message"]}'
                })
            
            # Check for duplicate Image ID
            if SimpleInspection.objects.filter(image_id=image_id).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Image ID "{image_id}" already exists. Please use a different ID.'
                })
            
            # Import camera manager
            from .views import camera_manager
            
            # Check if camera is connected
            if not camera_manager.is_connected:
                return JsonResponse({
                    'success': False,
                    'error': 'Camera not connected. Please connect camera first.'
                })
            
            # Log current camera state
            print(f"📷 Camera state - Connected: {camera_manager.is_connected}, Streaming: {camera_manager.is_streaming}, Trigger mode: {camera_manager.is_trigger_mode}")
            
            # Capture image from camera using manual override to handle trigger mode
            original_dir = os.path.join(settings.MEDIA_ROOT, 'inspections', 'original')
            os.makedirs(original_dir, exist_ok=True)
            
            # Use manual override capture to handle trigger mode properly
            success, capture_result = camera_manager.capture_manual_override(original_dir)
            
            if not success:
                return JsonResponse({
                    'success': False,
                    'error': f'Camera capture failed: {capture_result}'
                })
            
            # Get captured image details (EXISTING CODE - UNCHANGED)
            captured_filepath = capture_result['filepath']
            captured_filename = capture_result['filename']
            
            # Rename file to include image_id (EXISTING CODE - UNCHANGED)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_filename = f"{image_id}_{timestamp}_camera.jpg"
            new_filepath = os.path.join(original_dir, new_filename)
            
            # Move/rename the captured file (EXISTING CODE - UNCHANGED)
            import shutil
            shutil.move(captured_filepath, new_filepath)
            
            print(f"Camera captured: {new_filepath}")
            
            # Process with ML model (EXISTING CODE - UNCHANGED)
            processing_result = _process_with_yolov8_model(new_filepath, image_id)
            
            if not processing_result['success']:
                return JsonResponse({
                    'success': False,
                    'error': processing_result['error']
                })
            
            # Extract results from YOLOv8 processing (EXISTING CODE - UNCHANGED)
            detection_data = processing_result['data']
            nut_results = detection_data['nut_results']
            decision = detection_data['decision']
            
            # Use ML decision for counts (EXISTING CODE - UNCHANGED)
            present_count = decision['present_count']
            missing_count = decision['missing_count']
            
            print(f"ML Results - Present: {present_count}, Missing: {missing_count}")
            
            # Determine individual nut statuses based on ML results (EXISTING CODE - UNCHANGED)
            nut_statuses = ['MISSING', 'MISSING', 'MISSING', 'MISSING']
            
            # Assign PRESENT status based on ML detection (EXISTING CODE - UNCHANGED)
            for nut_key in ['nut1', 'nut2', 'nut3', 'nut4']:
                if nut_key in nut_results and nut_results[nut_key]['status'] == 'PRESENT':
                    nut_index = int(nut_key.replace('nut', '')) - 1
                    nut_statuses[nut_index] = 'PRESENT'
            
            # Overall result based on ML decision (EXISTING CODE - UNCHANGED)
            overall_result = 'PASS' if missing_count == 0 else 'FAIL'
            
            # Save to database (EXISTING CODE - UNCHANGED)
            inspection = SimpleInspection.objects.create(
                user=request.user,
                image_id=image_id,
                filename=new_filename,
                overall_result=overall_result,
                nut1_status=nut_statuses[0],
                nut2_status=nut_statuses[1],
                nut3_status=nut_statuses[2],
                nut4_status=nut_statuses[3],
                processing_time=detection_data.get('processing_time', 0.0)
            )
            
            print(f"Saved to database: {inspection.id}")
            
            # Get annotated image path (EXISTING CODE - UNCHANGED)
            annotated_image_path = detection_data.get('annotated_image_path', '')
            
            if annotated_image_path and os.path.exists(annotated_image_path):
                annotated_filename = os.path.basename(annotated_image_path)
            else:
                # Check for existing result files
                results_dir = os.path.join(settings.MEDIA_ROOT, 'inspections', 'results')
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
            # 🆕 ENHANCED FUNCTIONALITY - OK/NG STORAGE (NEW CODE ADDED)
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
                    user=request.user,
                    image_id=image_id,
                    original_image_path=new_filepath,
                    annotated_image_path=annotated_image_path,
                    nuts_present=present_count,
                    nuts_absent=missing_count,
                    confidence_scores=confidence_scores,
                    processing_time=detection_data.get('processing_time', 0.0)
                )

                if enhanced_inspection.test_status == 'OK':
                    print(f"\n🎯 Status is OK - Initiating file transfer...")
                    print(f"   - QR Code: {enhanced_inspection.image_id}")
                    print(f"   - Inspection ID: {enhanced_inspection.id}")
                    
                    try:
                        from .file_transfer_service import FileTransferService
                        transfer_service = FileTransferService()
                        
                        success, message, details = transfer_service.process_ok_status_change(enhanced_inspection)
                        
                        if success:
                            print(f"✅ File transfer successful: {message}")
                        else:
                            print(f"❌ File transfer failed: {message}")
                            
                    except Exception as e:
                        print(f"💥 File transfer error: {str(e)}")
                
                if enhanced_inspection:
                    print(f"🎯 Enhanced storage: {enhanced_inspection.test_status} folder - {enhanced_inspection.id}")
                    enhanced_storage_success = True
                    enhanced_folder = enhanced_inspection.test_status
                else:
                    print("Enhanced storage failed, continuing with existing workflow")
                    enhanced_storage_success = False
                    enhanced_folder = 'OK' if missing_count == 0 else 'NG'
                    
            except ImportError:
                print("Enhanced storage service not available, continuing with existing workflow")
                enhanced_storage_success = False
                enhanced_folder = 'OK' if missing_count == 0 else 'NG'
            except Exception as e:
                print(f"Enhanced storage error: {e}, continuing with existing workflow")
                enhanced_storage_success = False
                enhanced_folder = 'OK' if missing_count == 0 else 'NG'
            
            # ============================================================================
            # EXISTING RETURN RESPONSE (ENHANCED WITH NEW DATA)
            # ============================================================================
            
            # Return complete results (EXISTING CODE + ENHANCED DATA)
            response_data = {
                'success': True,
                'image_id': image_id,
                'overall_result': overall_result,
                'nut_results': {
                    'nut1': {'status': nut_statuses[0], 'confidence': nut_results.get('nut1', {}).get('confidence', 0.0)},
                    'nut2': {'status': nut_statuses[1], 'confidence': nut_results.get('nut2', {}).get('confidence', 0.0)},
                    'nut3': {'status': nut_statuses[2], 'confidence': nut_results.get('nut3', {}).get('confidence', 0.0)},
                    'nut4': {'status': nut_statuses[3], 'confidence': nut_results.get('nut4', {}).get('confidence', 0.0)},
                },
                'summary': {
                    'present_count': present_count,
                    'missing_count': missing_count,
                    'quality_score': (present_count / 4) * 100
                },
                'processing_info': {
                    'processing_time': detection_data.get('processing_time', 0.0),
                    'method': 'camera',
                    'filename': new_filename,
                    'total_detections': detection_data.get('total_detections', 0),
                    'confidence_threshold': detection_data.get('confidence_threshold', 0.5)
                },
                'detection_details': {
                    'detections': detection_data.get('detections', []),
                    'center_validation': detection_data.get('center_validation', {}),
                    'business_decision': decision
                },
                'image_paths': {
                    'original': f"/media/inspections/original/{new_filename}",
                    'annotated': f"/media/inspections/results/{annotated_filename}",
                },
                'inspection_id': str(inspection.id),
                'timestamp': datetime.now().isoformat(),
                
                # 🆕 ENHANCED DATA (NEW FIELDS ADDED)
                'enhanced_storage': {
                    'enabled': enhanced_storage_success,
                    'folder': enhanced_folder,
                    'test_status': 'OK' if missing_count == 0 else 'NG',
                    'nuts_present': present_count,
                    'nuts_absent': missing_count
                }
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': f'Camera processing error: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Method not allowed'
    })


@login_required
def simple_workflow_page(request):
    """
    Simple single image workflow page - redirects to Image ID entry
    """
    return redirect('ml_api:image_id_entry')

@login_required
def simple_process_image(request):
    """
    Step 3 & 4: Image processing and results (UPLOAD METHOD)
    Enhanced with actual YOLOv8 model integration - FIXED VERSION
    """
    if request.method == 'POST':
        try:
            image_id = request.POST.get('image_id', '').strip()
            uploaded_file = request.FILES.get('image')
            image_source = request.POST.get('image_source', 'upload')  # 'upload' or 'camera'
            
            # Validate Image ID
            if not image_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Image ID is required'
                })
            
            validation_result = _validate_image_id_format(image_id)
            if not validation_result['valid']:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid Image ID: {validation_result["message"]}'
                })
            
            # Check for duplicate Image ID
            if SimpleInspection.objects.filter(image_id=image_id).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Image ID "{image_id}" already exists. Please use a different ID.'
                })
            
            # Handle image file and save to processing directory
            if image_source == 'upload':
                if not uploaded_file:
                    return JsonResponse({
                        'success': False,
                        'error': 'Image file is required for upload method'
                    })
                
                # Save uploaded image to processing directory
                image_path, filename = _save_uploaded_image(uploaded_file, image_id)
                
            else:
                # Camera capture - filename would be generated
                filename = f"{image_id}_camera_capture.jpg"
                # For camera, you would get the image path from camera service
                image_path = None  # TODO: Get from camera service
                
                return JsonResponse({
                    'success': False,
                    'error': 'Camera capture not implemented yet. Please use upload method.'
                })
            
            # Process image with actual YOLOv8 model
            processing_result = _process_with_yolov8_model(image_path, image_id)
            
            if not processing_result['success']:
                return JsonResponse({
                    'success': False,
                    'error': processing_result['error']
                })
            
            # Extract results from YOLOv8 processing
            detection_data = processing_result['data']
            nut_results = detection_data['nut_results']
            decision = detection_data['decision']
            
            # FIXED: Use the correct counts from your ML business logic
            present_count = decision['present_count']
            missing_count = decision['missing_count']
            
            print(f"DEBUG: ML detected - Present: {present_count}, Missing: {missing_count}")
            print(f"DEBUG: Nut results from ML: {nut_results}")
            
            # FIXED: Determine individual nut statuses based on ACTUAL ML results
            nut_statuses = ['MISSING', 'MISSING', 'MISSING', 'MISSING']  # Initialize all as missing
            
            # Assign PRESENT status to the correct positions based on ML detection
            present_count_assigned = 0
            for nut_key in ['nut1', 'nut2', 'nut3', 'nut4']:
                if nut_key in nut_results and nut_results[nut_key]['status'] == 'PRESENT':
                    nut_index = int(nut_key.replace('nut', '')) - 1  # Convert nut1->0, nut2->1, etc.
                    nut_statuses[nut_index] = 'PRESENT'
                    present_count_assigned += 1
            
            # Verify our assignment matches ML results
            actual_present = nut_statuses.count('PRESENT')
            actual_missing = nut_statuses.count('MISSING')
            
            print(f"DEBUG: Final nut statuses: {nut_statuses}")
            print(f"DEBUG: Assigned - Present: {actual_present}, Missing: {actual_missing}")
            
            # Use ML decision for overall result (this is correct)
            overall_result = 'PASS' if missing_count == 0 else 'FAIL'
            
            # Save to database with CORRECT nut statuses
            inspection = SimpleInspection.objects.create(
                user=request.user,
                image_id=image_id,
                filename=filename,
                overall_result=overall_result,
                nut1_status=nut_statuses[0],  # These should now be correct
                nut2_status=nut_statuses[1],
                nut3_status=nut_statuses[2],
                nut4_status=nut_statuses[3],
                processing_time=detection_data.get('processing_time', 0.0)
            )
            
            print(f"DEBUG: Saved to database - Nut1: {nut_statuses[0]}, Nut2: {nut_statuses[1]}, Nut3: {nut_statuses[2]}, Nut4: {nut_statuses[3]}")
            
            # FIXED: Get the actual annotated image path from processing (MOVED OUTSIDE return statement)
            # FIXED: Get the actual annotated image path from processing
            annotated_image_path = detection_data.get('annotated_image_path', '')
            print(f"DEBUG: Annotated image path from services: {annotated_image_path}")

            if annotated_image_path and os.path.exists(annotated_image_path):
                # Extract just the filename from the full path
                annotated_filename = os.path.basename(annotated_image_path)
                print(f"DEBUG: Using actual annotated filename: {annotated_filename}")
            else:
                # Check what files actually exist in results directory
                import glob
                results_dir = os.path.join(settings.MEDIA_ROOT, 'inspections', 'results')
                pattern = f"{image_id}_*_result.jpg"
                matching_files = glob.glob(os.path.join(results_dir, pattern))
                
                if matching_files:
                    # Use the most recent matching file
                    latest_file = max(matching_files, key=os.path.getctime)
                    annotated_filename = os.path.basename(latest_file)
                    print(f"DEBUG: Found existing result file: {annotated_filename}")
                else:
                    # Fallback filename pattern
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    annotated_filename = f"{image_id}_{timestamp}_result.jpg"
                    print(f"DEBUG: Using fallback filename: {annotated_filename}")
            
            # Return results using the CORRECT counts from ML
            # ADD THIS LINE RIGHT HERE:
            print(f"DEBUG: Returning annotated path: /media/inspections/results/{annotated_filename}")

            # Return results using the CORRECT counts from ML
            return JsonResponse({
                'success': True,
                'image_id': image_id,
                'overall_result': overall_result,
                'nut_results': {
                    'nut1': {'status': nut_statuses[0], 'confidence': nut_results.get('nut1', {}).get('confidence', 0.0)},
                    'nut2': {'status': nut_statuses[1], 'confidence': nut_results.get('nut2', {}).get('confidence', 0.0)},
                    'nut3': {'status': nut_statuses[2], 'confidence': nut_results.get('nut3', {}).get('confidence', 0.0)},
                    'nut4': {'status': nut_statuses[3], 'confidence': nut_results.get('nut4', {}).get('confidence', 0.0)},
                },
                'summary': {
                    'present_count': present_count,
                    'missing_count': missing_count,
                    'quality_score': (present_count / 4) * 100
                },
                'processing_info': {
                    'processing_time': detection_data.get('processing_time', 0.0),
                    'method': image_source,
                    'filename': filename,
                    'total_detections': detection_data.get('total_detections', 0),
                    'confidence_threshold': detection_data.get('confidence_threshold', 0.5)
                },
                'detection_details': {
                    'detections': detection_data.get('detections', []),
                    'center_validation': detection_data.get('center_validation', {}),
                    'business_decision': decision
                },
                'image_paths': {
                    'original': f"/media/inspections/original/{filename}",
                    'annotated': f"/media/inspections/results/{annotated_filename}",
                },
                'inspection_id': str(inspection.id),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': f'Processing error: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Method not allowed'
    })

@login_required
def results_display_view(request):
    """
    Step 4: Results Display - Show processing results
    Complete function with proper imports and error handling
    """
    import glob
    import os
    from django.conf import settings
    
    image_id = request.GET.get('image_id', '')
    
    if not image_id:
        messages.error(request, 'No Image ID provided.')
        return redirect('ml_api:image_id_entry')
    
    # Try to get the most recent inspection for this image_id
    try:
        inspection = SimpleInspection.objects.filter(
            image_id=image_id,
            user=request.user
        ).latest('created_at')
    except SimpleInspection.DoesNotExist:
        messages.error(request, f'No inspection found for Image ID: {image_id}')
        return redirect('ml_api:image_id_entry')
    
    # Calculate summary statistics
    nuts_present = 0
    nuts_missing = 0
    
    for nut_status in [inspection.nut1_status, inspection.nut2_status, 
                       inspection.nut3_status, inspection.nut4_status]:
        if nut_status == 'PRESENT':
            nuts_present += 1
        else:
            nuts_missing += 1
    
    quality_score = (nuts_present / 4) * 100
    
    # Find the actual annotated image file
    try:
        results_dir = os.path.join(settings.MEDIA_ROOT, 'inspections', 'results')
        pattern = f"{image_id}_*_result.jpg"
        matching_files = glob.glob(os.path.join(results_dir, pattern))
        
        print(f"DEBUG: Looking for annotated images in: {results_dir}")
        print(f"DEBUG: Pattern: {pattern}")
        print(f"DEBUG: Found matching files: {matching_files}")
        
        if matching_files:
            # Use the most recent file
            latest_file = max(matching_files, key=os.path.getctime)
            annotated_filename = os.path.basename(latest_file)
            print(f"DEBUG: Using annotated filename: {annotated_filename}")
        else:
            annotated_filename = f"{image_id}_result.jpg"  # Fallback
            print(f"DEBUG: No matching files found, using fallback: {annotated_filename}")
            
    except Exception as e:
        print(f"DEBUG: Error finding annotated image: {e}")
        annotated_filename = f"{image_id}_result.jpg"  # Fallback
    
    # Debug: Check if the file actually exists
    annotated_path = os.path.join(settings.MEDIA_ROOT, 'inspections', 'results', annotated_filename)
    file_exists = os.path.exists(annotated_path)
    print(f"DEBUG: Annotated file exists at {annotated_path}: {file_exists}")
    
    context = {
        'image_id': image_id,
        'inspection': inspection,
        'nuts_present': nuts_present,
        'nuts_missing': nuts_missing,
        'quality_score': int(quality_score),
        'annotated_filename': annotated_filename,
        'file_exists': file_exists,  # Pass this for debugging
    }
    
    return render(request, 'ml_api/results_display.html', context)

def _save_uploaded_image(uploaded_file, image_id):
    """
    Save uploaded image to processing directory
    """
    import os
    from django.conf import settings
    from django.core.files.storage import default_storage
    
    # Create directories if they don't exist
    original_dir = os.path.join(settings.MEDIA_ROOT, 'inspections', 'original')
    os.makedirs(original_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_extension = os.path.splitext(uploaded_file.name)[1]
    filename = f"{image_id}_{timestamp}{file_extension}"
    
    # Save file
    file_path = os.path.join(original_dir, filename)
    
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    
    return file_path, filename

def _process_with_yolov8_model(image_path, image_id):
    """
    Process image with actual YOLOv8 model (using your exact ML logic)
    """
    try:
        import cv2
        import numpy as np
        from pathlib import Path
        from django.conf import settings
        import os
        
        # Import YOLOv8 model from your services
        from .services import enhanced_nut_detection_service
        
        # Verify image exists
        if not os.path.exists(image_path):
            return {
                'success': False,
                'error': f'Image file not found: {image_path}'
            }
        
        # Load and validate image
        image = cv2.imread(image_path)
        if image is None:
            return {
                'success': False,
                'error': 'Could not load image file'
            }
        
        print(f"Processing image: {image_path}")
        print(f"Image shape: {image.shape}")
        
        # Use your enhanced nut detection service with your ML logic
        start_time = datetime.now()
        
        # Process with your YOLOv8 model using your exact business logic
        result = enhanced_nut_detection_service.process_image_with_id(
            image_path=image_path,
            image_id=image_id,
            user_id=None
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if not result['success']:
            return {
                'success': False,
                'error': result.get('error', 'YOLOv8 processing failed')
            }
        
        # Extract results using your business logic
        nut_results = result['nut_results']
        decision = result['decision']
        center_validation = result.get('center_validation', {})
        detections = result.get('detection_summary', {}).get('detections', [])
        
        return {
            'success': True,
            'data': {
                'nut_results': nut_results,
                'decision': decision,
                'detections': detections,
                'center_validation': center_validation,
                'processing_time': processing_time,
                'total_detections': len(detections),
                'confidence_threshold': 0.5,
                'annotated_image_path': result.get('annotated_image_path')
            }
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': f'YOLOv8 processing error: {str(e)}'
        }

def simple_logout_view(request):
    """
    Simple logout
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('ml_api:simple_login')

# 🆕 NEW: FILE TRANSFER MANAGEMENT VIEWS - ADD THESE AT THE END OF THE FILE

@login_required
def file_transfer_dashboard(request):
    """
    Dashboard for monitoring file transfer system
    """
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('ml_api:simple_user_dashboard')
    
    try:
        # Initialize transfer service
        transfer_service = FileTransferService()
        
        # Get statistics
        stats = transfer_service.get_transfer_statistics()
        
        context = {
            'stats': stats,
            'page_title': 'File Transfer Dashboard'
        }
        
        return render(request, 'ml_api/file_transfer_dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading file transfer dashboard: {str(e)}')
        return redirect('ml_api:simple_admin_dashboard')

@login_required
def retry_failed_transfers(request):
    """
    AJAX endpoint to retry failed file transfers
    """
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Admin access required'})
    
    if request.method == 'POST':
        try:
            print(f"\n🔄 Manual retry initiated by: {request.user.username}")
            
            # Initialize transfer service
            transfer_service = FileTransferService()
            
            # Retry failed transfers
            results = transfer_service.retry_failed_transfers()
            
            return JsonResponse({
                'success': True,
                'message': f"Retry completed: {results.get('successful', 0)} successful, {results.get('failed', 0)} failed",
                'results': results
            })
            
        except Exception as e:
            error_msg = f"Retry failed: {str(e)}"
            print(f"💥 {error_msg}")
            return JsonResponse({'success': False, 'error': error_msg})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

@login_required
def test_file_transfer_system(request):
    """
    AJAX endpoint to test file transfer system
    """
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Admin access required'})
    
    if request.method == 'POST':
        try:
            print(f"\n🧪 System test initiated by: {request.user.username}")
            
            # Initialize transfer service
            transfer_service = FileTransferService()
            
            # Run system test
            test_results = transfer_service.test_system()
            
            return JsonResponse({
                'success': test_results.get('overall', False),
                'message': 'System test completed',
                'results': test_results
            })
            
        except Exception as e:
            error_msg = f"System test failed: {str(e)}"
            print(f"💥 {error_msg}")
            return JsonResponse({'success': False, 'error': error_msg})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

@login_required
def override_authentication_view(request):
    """
    Override authentication for status changes
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            image_id = data.get('image_id')
            
            # Check if this is a predefined admin
            is_admin = False
            if username in PREDEFINED_ADMINS and password == PREDEFINED_ADMINS[username]:
                is_admin = True
            
            # Authenticate user
            user = authenticate(request, username=username, password=password)
            
            if user is not None or is_admin:
                # Find the inspection record
                try:
                    inspection = InspectionRecord.objects.filter(image_id=image_id).latest('capture_datetime')
                except InspectionRecord.DoesNotExist:
                    # Try SimpleInspection as fallback
                    try:
                        simple_inspection = SimpleInspection.objects.filter(image_id=image_id).latest('created_at')
                        return JsonResponse({
                            'success': False,
                            'error': 'Legacy inspection format not supported for override'
                        })
                    except SimpleInspection.DoesNotExist:
                        return JsonResponse({
                            'success': False,
                            'error': 'Inspection not found'
                        })
                
                # Determine user role
                if is_admin:
                    user_role = 'admin'
                elif user:
                    user_role = user.role
                else:
                    user_role = 'user'
                
                # Check permissions
                if user_role == 'user':
                    if user and inspection.user != user:
                        return JsonResponse({
                            'success': False,
                            'error': 'Users can only modify their own inspections'
                        })
                    
                    # Check if this is the latest inspection
                    if user:
                        latest_inspection = InspectionRecord.objects.filter(
                            user=user
                        ).order_by('-capture_datetime').first()
                        
                        if latest_inspection and inspection.id != latest_inspection.id:
                            return JsonResponse({
                                'success': False,
                                'error': 'Users can only modify their current/latest inspection'
                            })
                
                return JsonResponse({
                    'success': True,
                    'user_role': user_role,
                    'inspection_id': str(inspection.id),
                    'current_status': inspection.test_status,
                    'message': f'Authentication successful for {username}'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid username or password'
                })
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

# Helper Functions

def _validate_image_id_format(image_id):
    """
    Validate Image ID format according to requirements
    """
    if not image_id:
        return {'valid': False, 'message': 'Image ID cannot be empty'}
    
    if len(image_id) < 3:
        return {'valid': False, 'message': 'Image ID must be at least 3 characters long'}
    
    if len(image_id) > 50:
        return {'valid': False, 'message': 'Image ID cannot exceed 50 characters'}
    
    # Allow letters, numbers, underscore, and hyphen - FIXED: Added missing closing quote
    if not re.match(r'^[A-Za-z0-9_-]+$', image_id):
        return {'valid': False, 'message': 'Image ID can only contain letters, numbers, underscore, and hyphen'}
    
    return {'valid': True, 'message': f'Valid Image ID: {image_id}'}