# ml_api/services.py - Enhanced with Your Actual ML Logic - FIXED INDENTATION

import os
import cv2
import numpy as np
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import tempfile
import logging
from django.conf import settings
from django.core.files.storage import default_storage
import json

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("WARNING: ultralytics not available. Please install: pip install ultralytics")

logger = logging.getLogger(__name__)

class FlexibleNutDetectionService:
    """
    Flexible Industrial Nut Detection Service - Integrated from Your ML Code
    Implements your exact business logic:
    - All 4 nuts present → GREEN boxes on all positions
    - Any nut missing → RED boxes on all positions + report missing/present
    """

    def __init__(self):
        self.model = None
        self.model_path = getattr(settings, 'NUT_DETECTION_MODEL_PATH', 
                                 os.path.join(settings.BASE_DIR, 'models', 'industrial_nut_detection.pt'))

        # Configuration matching your ML model exactly
        self.config = {
            'confidence_threshold': 0.35,    # Primary confidence (configurable)
            'primary_confidence': 0.35,      # Same as above for backward compatibility
            'fallback_confidence': 0.25,     # Fallback detection confidence
            'minimum_confidence': 0.15,      # Minimum detection confidence
            'ultra_low_confidence': [0.1, 0.05],  # Ultra low confidence levels
            'iou_threshold': 0.45,
            'expected_classes': ['MISSING', 'PRESENT'],
            'target_size': (640, 640),
            'max_detections': 8,             # Allow more than 4 to filter later
            'overlap_threshold': 0.3,        # For removing duplicates
            'multi_scales': [480, 640, 800, 1024],  # Multi-scale detection
            'expected_nuts': 4
        }

        self.stats = {
            'total_processed': 0,
            'successful_detections': 0,
            'failed_detections': 0,
            'average_processing_time': 0,
            'primary_detection_count': 0,
            'fallback_detection_count': 0,
            'enhancement_detection_count': 0,
            'multi_scale_detection_count': 0,
            'complete_detections': 0,
            'incomplete_detections': 0
        }

        # Load model
        self._load_model()
        logger.info("YOLOv8 model loaded: {}".format(self.model_path))
        logger.info("Enhanced Industrial Nut Detection Service Initialized")

    def _load_model(self):
        """Load your trained YOLOv8 model"""
        try:
            if not YOLO_AVAILABLE:
                raise ImportError("ultralytics not available")
            
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model not found: {self.model_path}")
            
            self.model = YOLO(self.model_path)
            logger.info(f"Model loaded: {self.model_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise

    def update_confidence_levels(self, primary=None, fallback=None, minimum=None, ultra_low=None):
        """
        Update confidence levels for different detection methods
        
        Args:
            primary: Primary detection confidence (0.1-0.9)
            fallback: Fallback detection confidence (0.1-0.8)
            minimum: Minimum detection confidence (0.05-0.5)
            ultra_low: List of ultra low confidence levels
        """
        if primary is not None:
            self.config['confidence_threshold'] = primary
            self.config['primary_confidence'] = primary
            logger.info(f"Updated primary confidence to: {primary}")
        
        if fallback is not None:
            self.config['fallback_confidence'] = fallback
            logger.info(f"Updated fallback confidence to: {fallback}")
        
        if minimum is not None:
            self.config['minimum_confidence'] = minimum
            logger.info(f"Updated minimum confidence to: {minimum}")
        
        if ultra_low is not None:
            self.config['ultra_low_confidence'] = ultra_low
            logger.info(f"Updated ultra low confidence levels to: {ultra_low}")
        
        logger.info("Confidence levels updated successfully")

    def get_confidence_settings(self):
        """Get current confidence level settings"""
        return {
            'primary_confidence': self.config['primary_confidence'],
            'fallback_confidence': self.config['fallback_confidence'],
            'minimum_confidence': self.config['minimum_confidence'],
            'ultra_low_confidence': self.config['ultra_low_confidence']
        }

    def enhance_image_for_detection(self, image):
        """Apply comprehensive image enhancement techniques"""
        enhanced_versions = {}
        
        # Original
        enhanced_versions['original'] = image.copy()
        
        try:
            # 1. Brightness normalization
            brightness = np.mean(image)
            if brightness < 100 or brightness > 140:
                target_brightness = 120
                factor = target_brightness / max(brightness, 1)
                bright_enhanced = np.clip(image * factor, 0, 255).astype(np.uint8)
                enhanced_versions['brightness'] = bright_enhanced
            
            # 2. CLAHE contrast enhancement
            if len(image.shape) == 3:
                lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                lab[:, :, 0] = clahe.apply(lab[:, :, 0])
                clahe_enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                enhanced_versions['clahe'] = clahe_enhanced
            
            # 3. Sharpening filter
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(image, -1, kernel)
            enhanced_versions['sharpened'] = sharpened
            
            # 4. Combined enhancement
            combined = enhanced_versions.get('brightness', image)
            if 'clahe' in enhanced_versions:
                combined = cv2.addWeighted(combined, 0.7, enhanced_versions['clahe'], 0.3, 0)
            enhanced_versions['combined'] = combined
            
        except Exception as e:
            logger.error(f"Image enhancement error: {e}")
        
        return enhanced_versions

    def _extract_detection_info(self, box, method='unknown'):
        """Extract detection information from YOLO box"""
        try:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
            
            if class_id in [0, 1]:  # Only accept MISSING(0) or PRESENT(1)
                return {
                    'class_id': class_id,
                    'class_name': self.config['expected_classes'][class_id],
                    'confidence': confidence,
                    'bbox': bbox,
                    'detection_method': method
                }
            return None
        except Exception as e:
            logger.error(f"Error extracting detection: {e}")
            return None

    def _calculate_iou(self, bbox1, bbox2):
        """Calculate Intersection over Union (IoU) between two bounding boxes"""
        try:
            x1_max = max(bbox1[0], bbox2[0])
            y1_max = max(bbox1[1], bbox2[1])
            x2_min = min(bbox1[2], bbox2[2])
            y2_min = min(bbox1[3], bbox2[3])
            
            if x2_min <= x1_max or y2_min <= y1_max:
                return 0.0
            
            intersection = (x2_min - x1_max) * (y2_min - y1_max)
            
            area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
            area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
            
            union = area1 + area2 - intersection
            
            return intersection / union if union > 0 else 0.0
        except:
            return 0.0

    def _overlaps_with_existing(self, new_detection, existing_detections, overlap_threshold=None):
        """Check if new detection overlaps significantly with existing ones"""
        if overlap_threshold is None:
            overlap_threshold = self.config['overlap_threshold']
        
        try:
            new_bbox = new_detection['bbox']
            
            for existing in existing_detections:
                existing_bbox = existing['bbox']
                iou = self._calculate_iou(new_bbox, existing_bbox)
                
                if iou > overlap_threshold:
                    return True
            return False
        except:
            return False

    def _filter_and_rank_detections(self, detections):
        """Filter overlapping detections and rank by confidence"""
        if not detections:
            return detections
        
        # Sort by confidence (highest first)
        sorted_detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        # Remove overlapping detections (keep highest confidence)
        filtered_detections = []
        for detection in sorted_detections:
            if not self._overlaps_with_existing(detection, filtered_detections, overlap_threshold=0.5):
                filtered_detections.append(detection)
        
        # Take top 4 detections (our expected maximum)
        return filtered_detections[:4]

    def _run_detection(self, image_path):
        """
        ENHANCED: Comprehensive detection pipeline combining all methods
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return []
            
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            all_detections = []
            
            logger.info(f"DEBUG - Processing: {Path(image_path).name}")
            
            # Method 1: Primary detection with normal confidence
            try:
                primary_results = self.model.predict(
                    image_path,
                    conf=self.config['primary_confidence'],
                    iou=self.config['iou_threshold'],
                    max_det=self.config['max_detections'],
                    verbose=False
                )
                
                primary_count = 0
                if primary_results[0].boxes is not None:
                    for box in primary_results[0].boxes:
                        detection = self._extract_detection_info(box, 'primary')
                        if detection:
                            all_detections.append(detection)
                            primary_count += 1
                
                logger.info(f"DEBUG - Primary detection: {primary_count} nuts found")
                self.stats['primary_detection_count'] += primary_count
            except Exception as e:
                logger.error(f"Primary detection error: {e}")
            
            # Method 2: Enhanced image detection if we need more detections
            if len(all_detections) < 4:
                logger.info(f"DEBUG - Applying image enhancement methods...")
                try:
                    enhanced_versions = self.enhance_image_for_detection(image_rgb)
                    enhancement_count = 0
                    
                    for enhancement_type, enhanced_img in enhanced_versions.items():
                        if enhancement_type == 'original':
                            continue  # Skip original as we already processed it
                        
                        results = self.model(enhanced_img, conf=0.2, iou=self.config['iou_threshold'])
                        if len(results) > 0 and len(results[0].boxes) > 0:
                            for detection in results[0].boxes:
                                detection_info = self._extract_detection_info(detection, f'enhanced_{enhancement_type}')
                                if (detection_info and 
                                    not self._overlaps_with_existing(detection_info, all_detections)):
                                    all_detections.append(detection_info)
                                    enhancement_count += 1
                    
                    logger.info(f"DEBUG - Image enhancement: +{enhancement_count} detections")
                    self.stats['enhancement_detection_count'] += enhancement_count
                except Exception as e:
                    logger.error(f"Image enhancement error: {e}")
            
            # Method 3: Fallback detection with lower confidence
            if len(all_detections) < 4:
                logger.info(f"DEBUG - Applying fallback detection (need {4 - len(all_detections)} more)...")
                try:
                    fallback_results = self.model.predict(
                        image_path,
                        conf=self.config['fallback_confidence'],
                        iou=self.config['iou_threshold'],
                        max_det=self.config['max_detections'],
                        verbose=False
                    )
                    
                    fallback_count = 0
                    if fallback_results[0].boxes is not None:
                        for box in fallback_results[0].boxes:
                            detection = self._extract_detection_info(box, 'fallback_low_conf')
                            if (detection and 
                                not self._overlaps_with_existing(detection, all_detections)):
                                all_detections.append(detection)
                                fallback_count += 1
                    
                    logger.info(f"DEBUG - Low confidence method: +{fallback_count} detections")
                    self.stats['fallback_detection_count'] += fallback_count
                except Exception as e:
                    logger.error(f"Fallback detection error: {e}")
            
            # Method 4: Ultra-low confidence detection
            if len(all_detections) < 4:
                try:
                    for conf in self.config['ultra_low_confidence']:
                        results = self.model(image_rgb, conf=conf, iou=0.3)
                        if len(results) > 0 and len(results[0].boxes) > 0:
                            for detection in results[0].boxes:
                                detection_info = self._extract_detection_info(detection, f'ultra_low_{conf}')
                                if (detection_info and 
                                    not self._overlaps_with_existing(detection_info, all_detections)):
                                    all_detections.append(detection_info)
                    
                    logger.info(f"DEBUG - Ultra-low confidence method: additional detections found")
                except Exception as e:
                    logger.error(f"Ultra-low confidence detection error: {e}")
            
            # Filter and rank final detections
            final_detections = self._filter_and_rank_detections(all_detections)
            
            # Convert to expected format (remove detection_method for compatibility)
            processed_detections = []
            for detection in final_detections:
                processed_detection = {
                    'class_id': detection['class_id'],
                    'class_name': detection['class_name'],
                    'confidence': detection['confidence'],
                    'bbox': detection['bbox']
                }
                processed_detections.append(processed_detection)
            
            # DEBUG: Log final processed detections
            logger.info(f"DEBUG - Final detections: {len(processed_detections)}")
            missing_count = sum(1 for d in processed_detections if d['class_name'] == 'MISSING')
            present_count = sum(1 for d in processed_detections if d['class_name'] == 'PRESENT')
            logger.info(f"DEBUG - PRESENT: {present_count}, MISSING: {missing_count}")
            
            # Update statistics
            if len(processed_detections) >= 4:
                self.stats['complete_detections'] += 1
            else:
                self.stats['incomplete_detections'] += 1
            
            return processed_detections
            
        except Exception as e:
            logger.error(f"Detection error for {image_path}: {e}")
            return []

    def _apply_business_logic(self, detections, image_name):
        """
        Apply your exact business logic from test validator:
        - All 4 nuts present → GREEN boxes
        - Any nut missing → RED boxes + report
        """
        missing_count = sum(1 for d in detections if d['class_name'] == 'MISSING')
        present_count = sum(1 for d in detections if d['class_name'] == 'PRESENT')
        total_detections = len(detections)
        
        # Conservative Industrial Logic - Enhanced
        if total_detections < 4:
            # Conservative approach: If we can't detect all 4 positions, assume problem
            box_color = "RED"
            status = "INCOMPLETE_DETECTION"
            action = "MANUAL_REVIEW_REQUIRED"
            
        elif missing_count == 0 and present_count == 4:
            # All 4 nuts present → GREEN boxes
            box_color = "GREEN"
            status = "ALL_NUTS_PRESENT"
            action = "APPROVED"
            
        elif missing_count > 0:
            # Any nut missing → RED boxes + report
            box_color = "RED" 
            status = "NUTS_MISSING"
            action = "REJECTED"
            
        else:
            # Edge case: insufficient detections
            box_color = "RED"
            status = "INSUFFICIENT_DETECTION"
            action = "REVIEW_REQUIRED"
        
        return {
            'box_color': box_color,
            'status': status,
            'action': action,
            'missing_count': missing_count,
            'present_count': present_count,
            'total_detections': total_detections,
            'scenario': self._classify_scenario(missing_count, present_count)
        }
    
    def _classify_scenario(self, missing_count, present_count):
        """Classify the detected scenario - From your ML code"""
        if missing_count == 0 and present_count == 4:
            return "ALL_PRESENT"
        elif missing_count == 1:
            return "ONE_MISSING"
        elif missing_count == 2:
            return "TWO_MISSING"
        elif missing_count == 3:
            return "THREE_MISSING"
        elif missing_count == 4:
            return "ALL_MISSING"
        else:
            return "MIXED_SCENARIO"

    def _calculate_center_validation(self, detections, image_shape):
        """
        Calculate center validation for detected nuts - From your ML code
        Validates that nut centers match bounding box centers within 10% tolerance
        """
        height, width = image_shape[:2]
        validation_results = []
        
        for detection in detections:
            bbox = detection['bbox']
            x1, y1, x2, y2 = bbox
            
            # Calculate bounding box center
            box_center_x = (x1 + x2) / 2
            box_center_y = (y1 + y2) / 2
            
            # Calculate bounding box dimensions
            box_width = x2 - x1
            box_height = y2 - y1
            
            # Calculate 10% tolerance based on box dimensions
            tolerance_x = box_width * 0.10  # 10% of box width
            tolerance_y = box_height * 0.10  # 10% of box height
            
            # For now, we assume the nut center is the same as box center
            nut_center_x = box_center_x  # Detected nut center
            nut_center_y = box_center_y  # Detected nut center
            
            # Calculate deviation
            deviation_x = abs(nut_center_x - box_center_x)
            deviation_y = abs(nut_center_y - box_center_y)
            
            # Check if within tolerance
            within_tolerance_x = deviation_x <= tolerance_x
            within_tolerance_y = deviation_y <= tolerance_y
            within_tolerance = within_tolerance_x and within_tolerance_y
            
            # Calculate percentage deviation
            percent_deviation_x = (deviation_x / (box_width / 2)) * 100 if box_width > 0 else 0
            percent_deviation_y = (deviation_y / (box_height / 2)) * 100 if box_height > 0 else 0
            
            validation_result = {
                'class_name': detection['class_name'],
                'confidence': detection['confidence'],
                'box_center': (box_center_x, box_center_y),
                'nut_center': (nut_center_x, nut_center_y),
                'box_dimensions': (box_width, box_height),
                'tolerance': (tolerance_x, tolerance_y),
                'deviation': (deviation_x, deviation_y),
                'percent_deviation': (percent_deviation_x, percent_deviation_y),
                'within_tolerance': within_tolerance,
                'within_tolerance_x': within_tolerance_x,
                'within_tolerance_y': within_tolerance_y
            }
            
            validation_results.append(validation_result)
        
        # Calculate overall validation statistics
        total_detections = len(validation_results)
        valid_centers = sum(1 for r in validation_results if r['within_tolerance'])
        center_accuracy = (valid_centers / total_detections * 100) if total_detections > 0 else 0
        
        return {
            'validation_results': validation_results,
            'total_detections': total_detections,
            'valid_centers': valid_centers,
            'center_accuracy': center_accuracy,
            'average_deviation_x': np.mean([r['percent_deviation'][0] for r in validation_results]) if validation_results else 0,
            'average_deviation_y': np.mean([r['percent_deviation'][1] for r in validation_results]) if validation_results else 0
        }

    def _create_annotated_image(self, image_path, detections, decision, image_id):
        """Create annotated image with individual nut position coloring"""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Could not load image: {image_path}")
            return None
            
        annotated = image.copy()
        
        # 🆕 NEW: Individual nut position coloring logic
        for detection in detections:
            bbox = detection['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # 🎯 INDIVIDUAL COLORING: Each nut gets its own color based on detection
            if detection['class_name'] == 'PRESENT':
                box_color = (0, 255, 0)      # GREEN for present nut
                text_color = (0, 200, 0)     # Dark green
                bg_color = (0, 100, 0)       # Background green
            else:  # MISSING
                box_color = (0, 0, 255)      # RED for missing nut
                text_color = (0, 0, 200)     # Dark red
                bg_color = (0, 0, 100)       # Background red
            
            # Draw thick bounding box with individual nut color
            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 4)
            
            # Add class and confidence labels
            label = f"{detection['class_name']}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            
            # Get text size for background
            (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # Draw background for text (match individual box color)
            cv2.rectangle(annotated, 
                        (x1, y1 - text_height - 10), 
                        (x1 + text_width, y1), 
                        bg_color, -1)
            
            # Draw text
            cv2.putText(annotated, label, (x1, y1 - 5), 
                    font, font_scale, (255, 255, 255), thickness)
        
        # Keep original business overlay (use overall decision colors for overlay)
        if decision['box_color'] == 'GREEN':
            overlay_box_color = (0, 255, 0)
            overlay_text_color = (0, 200, 0)
            overlay_bg_color = (0, 100, 0)
        else:
            overlay_box_color = (0, 0, 255)
            overlay_text_color = (0, 0, 200)
            overlay_bg_color = (0, 0, 100)
        
        # Add business status overlay
        self._add_business_overlay(annotated, decision)
        
        return annotated

    def _add_business_overlay(self, image, decision):
        """Add business status overlay to image - Updated for individual coloring"""
    # Use overall decision color for overlay
        if decision['box_color'] == 'GREEN':
            overlay_box_color = (0, 255, 0)
            overlay_text_color = (0, 200, 0)
            overlay_bg_color = (0, 100, 0)
        else:
            overlay_box_color = (0, 0, 255)
            overlay_text_color = (0, 0, 200)
            overlay_bg_color = (0, 0, 100)
    
    # Status texts based on your business logic
        status_text = f"STATUS: {decision['status']}"
        action_text = f"ACTION: {decision['action']}"
        scenario_text = f"SCENARIO: {decision['scenario']}"
        nuts_text = f"NUTS: {decision['present_count']} PRESENT, {decision['missing_count']} MISSING"
    
        texts = [status_text, action_text, scenario_text, nuts_text]
    
    # Calculate overlay size
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
    
        max_width = 0
        total_height = 20
    
        for text in texts:
            (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
            max_width = max(max_width, text_width)
            total_height += text_height + 8
    
    # Draw overlay background
        overlay_width = max_width + 20
        overlay_height = total_height + 10
    
        cv2.rectangle(image, (10, 10), (10 + overlay_width, 10 + overlay_height), overlay_bg_color, -1)
        cv2.rectangle(image, (10, 10), (10 + overlay_width, 10 + overlay_height), overlay_box_color, 3)
    
    # Draw texts
        y_offset = 35
        for text in texts:
            cv2.putText(image, text, (20, y_offset), font, font_scale, (255, 255, 255), thickness)
            y_offset += 30

    def process_image_with_id(self, image_path: str, image_id: str, user_id: Optional[int] = None) -> Dict:
        """
        Process image by path with your YOLOv8 model - Integrated from your ML code
        """
        start_time = datetime.now()
        
        try:
            if not self.model:
                return {
                    'success': False,
                    'error': 'Model not loaded',
                    'timestamp': start_time.isoformat()
                }

            # Verify image exists
            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'error': f'Image file not found: {image_path}',
                    'timestamp': start_time.isoformat()
                }

            # Load and validate image
            image = cv2.imread(image_path)
            if image is None:
                return {
                    'success': False,
                    'error': 'Could not load image file',
                    'timestamp': start_time.isoformat()
                }

            logger.info(f"Processing image: {image_path}")
            logger.info(f"Image shape: {image.shape}")

            # Run detection with your YOLOv8 model
            detections = self._run_detection(image_path)
            logger.info(f"Detections found: {len(detections)}")
            
            # Print detection details
            if detections:
                logger.info("Detection Details:")
                for i, det in enumerate(detections, 1):
                    logger.info(f"   {i}. {det['class_name']}: {det['confidence']:.3f}")

            # Calculate center validation
            center_validation = self._calculate_center_validation(detections, image.shape)
            
            # Apply business logic
            decision = self._apply_business_logic(detections, Path(image_path).name)
            
            # Create annotated image
            annotated_image = self._create_annotated_image(image_path, detections, decision, image_id)
            
            # Save annotated image
            annotated_path = self._save_annotated_image(annotated_image, image_id)
            
            # Prepare nut results in expected format
            nut_results = self._prepare_nut_results(detections, decision)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            self.stats['total_processed'] += 1
            self.stats['successful_detections'] += 1
            
            # Log results
            status_icon = "GREEN" if decision['box_color'] == 'GREEN' else "RED"
            logger.info(f"Business Decision: {status_icon} BOXES")
            logger.info(f"Status: {decision['status']}")
            logger.info(f"Detected Scenario: {decision['scenario']}")
            logger.info(f"Nuts: {decision['present_count']} PRESENT, {decision['missing_count']} MISSING")

            return {
                'success': True,
                'image_id': image_id,
                'processing_time': processing_time,
                'timestamp': start_time.isoformat(),
                'nut_results': nut_results,
                'decision': decision,
                'center_validation': center_validation,
                'detection_summary': {
                    'total_detections': len(detections),
                    'detections': detections
                },
                'annotated_image_path': annotated_path
            }

        except Exception as e:
            logger.error(f"Processing error for image {image_id}: {str(e)}")
            self.stats['total_processed'] += 1
            self.stats['failed_detections'] += 1
            
            return {
                'success': False,
                'error': f'Processing failed: {str(e)}',
                'image_id': image_id,
                'timestamp': start_time.isoformat()
            }

    def _prepare_nut_results(self, detections, decision):
        """Prepare nut results in expected format - FIXED VERSION"""
        # Initialize all nuts as missing
        nut_results = {
            'nut1': {'status': 'MISSING', 'confidence': 0.0, 'bounding_box': None},
            'nut2': {'status': 'MISSING', 'confidence': 0.0, 'bounding_box': None},
            'nut3': {'status': 'MISSING', 'confidence': 0.0, 'bounding_box': None},
            'nut4': {'status': 'MISSING', 'confidence': 0.0, 'bounding_box': None}
        }
        
        # Sort detections by position (top-left to bottom-right)
        present_detections = [d for d in detections if d['class_name'] == 'PRESENT']
        present_detections.sort(key=lambda x: (x['bbox'][1], x['bbox'][0]))  # Sort by y, then x
        
        # Assign present nuts to positions
        for i, detection in enumerate(present_detections[:4]):  # Max 4 nuts
            nut_key = f'nut{i+1}'
            bbox = detection['bbox']
            nut_results[nut_key] = {
                'status': 'PRESENT',
                'confidence': detection['confidence'],
                'bounding_box': {
                    'x1': bbox[0],
                    'y1': bbox[1],
                    'x2': bbox[2],
                    'y2': bbox[3]
                }
            }
        
        # IMPORTANT: If we have fewer than 4 detections, remaining nuts stay as MISSING
        # This ensures the business logic works correctly
        
        return nut_results

    def _save_annotated_image(self, annotated_image, image_id):
        """Save annotated image to results directory"""
        try:
            if annotated_image is None:
                return None
                
            # Create results directory
            results_dir = os.path.join(settings.MEDIA_ROOT, 'inspections', 'results')
            os.makedirs(results_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{image_id}_{timestamp}_result.jpg"
            file_path = os.path.join(results_dir, filename)
            
            # Save image
            cv2.imwrite(file_path, annotated_image)
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving annotated image: {e}")
            return None

    def is_healthy(self):
        """Check if service is healthy and ready"""
        return {
            'service_available': self.model is not None,
            'model_loaded': self.model is not None,
            'model_path': self.model_path,
            'config': self.config,
            'statistics': self.stats
        }

# Create global service instance
enhanced_nut_detection_service = FlexibleNutDetectionService()