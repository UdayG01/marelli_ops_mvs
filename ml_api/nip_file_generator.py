# ml_api/nip_file_generator.py - Generate .nip files for external server transfer

import json
import os
from datetime import datetime
from pathlib import Path
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class NipFileGenerator:
    """
    Generate .nip files containing inspection results for external server transfer
    """
    
    def __init__(self):
        self.nip_folder = Path(settings.MEDIA_ROOT) / 'nip_files'
        self.nip_folder.mkdir(parents=True, exist_ok=True)
        
        # Create subfolders for organization
        self.pending_folder = self.nip_folder / 'pending'
        self.sent_folder = self.nip_folder / 'sent'
        self.failed_folder = self.nip_folder / 'failed'
        
        for folder in [self.pending_folder, self.sent_folder, self.failed_folder]:
            folder.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 NIP file folders initialized:")
        print(f"   - Pending: {self.pending_folder}")
        print(f"   - Sent: {self.sent_folder}")
        print(f"   - Failed: {self.failed_folder}")
    
    def generate_nip_content(self, inspection_record):
        """
        Generate .nip file content based on inspection results
        
        Content includes:
        - QR Code (Image ID)
        - OK/NG status of each nut
        - Timestamp
        - Overall result
        """
        timestamp = datetime.now().isoformat()
        
        # Determine individual nut statuses based on inspection
        if hasattr(inspection_record, 'nut1_status'):
            # SimpleInspection model
            nut_statuses = {
                'nut1': inspection_record.nut1_status,
                'nut2': inspection_record.nut2_status,
                'nut3': inspection_record.nut3_status,
                'nut4': inspection_record.nut4_status,
            }
            overall_status = 'OK' if inspection_record.overall_result == 'PASS' else 'NG'

            # Convert PRESENT/MISSING to OK/NG for .nip file
            converted_statuses = {}
            for nut_key, status in nut_statuses.items():
                converted_statuses[nut_key] = 'OK' if status == 'PRESENT' else 'NG'
            nut_statuses = converted_statuses
        else:
            # InspectionRecord model
            # Determine individual statuses based on present/absent counts
            total_present = inspection_record.nuts_present
            total_absent = inspection_record.nuts_absent
            
            # For now, mark first 'present_count' nuts as OK, rest as NG
            nut_statuses = {}
            for i in range(1, 5):
                if i <= total_present:
                    nut_statuses[f'nut{i}'] = 'OK'
                else:
                    nut_statuses[f'nut{i}'] = 'NG'
            
            overall_status = inspection_record.test_status
        
        # Create .nip file content structure
        nip_content = {
            'metadata': {
                'qr_code': inspection_record.image_id,
                'timestamp': timestamp,
                'generated_by': 'Industrial_Nut_Detection_System',
                'version': '1.0'
            },
            'inspection_results': {
                'overall_status': overall_status,
                'individual_nuts': nut_statuses,
                'summary': {
                    'nuts_ok': list(nut_statuses.values()).count('OK'),
                    'nuts_ng': list(nut_statuses.values()).count('NG'),
                    'total_nuts': 4
                }
            },
            'processing_info': {
                'inspection_datetime': inspection_record.created_at.isoformat() if hasattr(inspection_record, 'created_at') else inspection_record.capture_datetime.isoformat(),
                'processing_time': getattr(inspection_record, 'processing_time', 0.0),
                'user': inspection_record.user.username if inspection_record.user else 'system'
            }
        }
        
        return nip_content
    
    def create_nip_file(self, inspection_record, folder='pending'):
        """
        Create .nip file from inspection record
        
        Args:
            inspection_record: SimpleInspection or InspectionRecord instance
            folder: 'pending', 'sent', or 'failed'
        
        Returns:
            tuple: (success, file_path, message)
        """
        try:
            # Generate content
            nip_content = self.generate_nip_content(inspection_record)
            
            # Generate filename: QRcode.nip
            qr_code = inspection_record.image_id
            filename = f"{qr_code}.nip"
            
            # Determine target folder
            if folder == 'pending':
                target_folder = self.pending_folder
            elif folder == 'sent':
                target_folder = self.sent_folder
            elif folder == 'failed':
                target_folder = self.failed_folder
            else:
                target_folder = self.pending_folder
            
            file_path = target_folder / filename
            
            # Write .nip file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(nip_content, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Created .nip file: {file_path}")
            print(f"📄 Content preview:")
            print(f"   - QR Code: {qr_code}")
            print(f"   - Overall Status: {nip_content['inspection_results']['overall_status']}")
            print(f"   - Nuts OK: {nip_content['inspection_results']['summary']['nuts_ok']}")
            print(f"   - Nuts NG: {nip_content['inspection_results']['summary']['nuts_ng']}")
            
            logger.info(f"Created .nip file: {file_path} for QR: {qr_code}")
            
            return True, str(file_path), f"Successfully created {filename}"
            
        except Exception as e:
            error_msg = f"Failed to create .nip file for {inspection_record.image_id}: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            return False, None, error_msg
    
    def move_nip_file(self, file_path, from_folder, to_folder):
        """
        Move .nip file between folders (pending -> sent/failed)
        
        Args:
            file_path: Current file path
            from_folder: Source folder name
            to_folder: Destination folder name
        
        Returns:
            tuple: (success, new_path, message)
        """
        try:
            source_path = Path(file_path)
            filename = source_path.name
            
            # Determine destination folder
            if to_folder == 'sent':
                dest_folder = self.sent_folder
            elif to_folder == 'failed':
                dest_folder = self.failed_folder
            elif to_folder == 'pending':
                dest_folder = self.pending_folder
            else:
                return False, None, f"Invalid destination folder: {to_folder}"
            
            dest_path = dest_folder / filename
            
            # Move file
            if source_path.exists():
                source_path.rename(dest_path)
                print(f"📁 Moved {filename}: {from_folder} → {to_folder}")
                logger.info(f"Moved .nip file: {source_path} → {dest_path}")
                return True, str(dest_path), f"Moved to {to_folder}"
            else:
                return False, None, f"Source file not found: {file_path}"
                
        except Exception as e:
            error_msg = f"Failed to move file {file_path}: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            return False, None, error_msg
    
    def get_pending_files(self):
        """Get list of pending .nip files"""
        try:
            pending_files = list(self.pending_folder.glob('*.nip'))
            print(f"📋 Found {len(pending_files)} pending .nip files")
            return pending_files
        except Exception as e:
            print(f"❌ Error getting pending files: {e}")
            return []
    
    def get_failed_files(self):
        """Get list of failed .nip files for retry"""
        try:
            failed_files = list(self.failed_folder.glob('*.nip'))
            print(f"⚠️ Found {len(failed_files)} failed .nip files")
            return failed_files
        except Exception as e:
            print(f"❌ Error getting failed files: {e}")
            return []
    
    def read_nip_file(self, file_path):
        """Read and parse .nip file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            print(f"📖 Read .nip file: {Path(file_path).name}")
            return True, content, "File read successfully"
            
        except Exception as e:
            error_msg = f"Failed to read .nip file {file_path}: {str(e)}"
            print(f"❌ {error_msg}")
            return False, None, error_msg
    
    def cleanup_old_files(self, days_old=30):
        """Clean up old .nip files from sent/failed folders"""
        import time
        from pathlib import Path
        
        current_time = time.time()
        cutoff_time = current_time - (days_old * 24 * 3600)
        
        cleaned_count = 0
        
        for folder in [self.sent_folder, self.failed_folder]:
            for file_path in folder.glob('*.nip'):
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                        print(f"🗑️ Cleaned old file: {file_path.name}")
                    except Exception as e:
                        print(f"⚠️ Could not clean {file_path.name}: {e}")
        
        print(f"🧹 Cleaned {cleaned_count} old .nip files")
        return cleaned_count
    
    def get_file_statistics(self):
        """Get statistics about .nip files"""
        stats = {
            'pending': len(list(self.pending_folder.glob('*.nip'))),
            'sent': len(list(self.sent_folder.glob('*.nip'))),
            'failed': len(list(self.failed_folder.glob('*.nip'))),
        }
        
        print(f"📊 .nip File Statistics:")
        print(f"   - Pending: {stats['pending']}")
        print(f"   - Sent: {stats['sent']}")
        print(f"   - Failed: {stats['failed']}")
        print(f"   - Total: {sum(stats.values())}")
        
        return stats