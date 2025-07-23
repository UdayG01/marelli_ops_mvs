# ml_api/file_transfer_service.py - Main service for handling .nip file generation and transfer

import os
import json
from datetime import datetime
from pathlib import Path
from django.conf import settings
from .models import InspectionRecord, SimpleInspection
from .nip_file_generator import NipFileGenerator
from .external_server_client import ExternalServerClient
import logging

logger = logging.getLogger(__name__)

class FileTransferService:
    """
    Main service for handling .nip file generation and transfer to external server
    """
    
    def __init__(self):
        """Initialize file transfer service with generators and clients"""
        print(f"\n🚀 Initializing File Transfer Service...")
        
        # Initialize components
        self.nip_generator = NipFileGenerator()
        self.server_client = ExternalServerClient()
        
        # Create transfer log directory
        self.log_folder = Path(settings.MEDIA_ROOT) / 'transfer_logs'
        self.log_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ File Transfer Service initialized")
        print(f"📁 Transfer logs: {self.log_folder}")
        
        logger.info("FileTransferService initialized")
    
    def process_ok_status_change(self, inspection_record):
        """
        Main method: Process when inspection status changes to OK
        
        Args:
            inspection_record: SimpleInspection or InspectionRecord instance with OK status
        
        Returns:
            tuple: (success, message, details)
        """
        try:
            qr_code = inspection_record.image_id
            
            print(f"\n🎯 Processing OK status change:")
            print(f"   - QR Code: {qr_code}")
            print(f"   - Record Type: {type(inspection_record).__name__}")
            print(f"   - User: {inspection_record.user.username if inspection_record.user else 'system'}")
            
            # Step 1: Generate .nip file
            print(f"\n📄 Step 1: Generating .nip file...")
            success, file_path, message = self.nip_generator.create_nip_file(
                inspection_record, 
                folder='pending'
            )
            
            if not success:
                error_msg = f"Failed to generate .nip file: {message}"
                print(f"❌ {error_msg}")
                self._log_transfer_attempt(qr_code, 'generation_failed', error_msg)
                return False, error_msg, {'step': 'generation', 'error': message}
            
            print(f"✅ .nip file generated: {Path(file_path).name}")
            
            # Step 2: Send to external server
            print(f"\n🌐 Step 2: Sending to external server...")
            success, response_data, message, attempts = self.server_client.send_with_retry(
                file_path, 
                qr_code
            )
            
            if success:
                # Step 3: Move file to sent folder
                print(f"\n📁 Step 3: Moving file to sent folder...")
                move_success, new_path, move_msg = self.nip_generator.move_nip_file(
                    file_path, 
                    'pending', 
                    'sent'
                )
                
                if move_success:
                    success_msg = f"Successfully processed {qr_code}: .nip file sent and archived"
                    print(f"🎉 {success_msg}")
                    
                    # Log successful transfer
                    self._log_transfer_attempt(
                        qr_code, 
                        'success', 
                        success_msg, 
                        {
                            'response': response_data,
                            'attempts': attempts,
                            'file_path': new_path
                        }
                    )
                    
                    return True, success_msg, {
                        'step': 'completed',
                        'file_path': new_path,
                        'response': response_data,
                        'attempts': attempts
                    }
                else:
                    # Transfer succeeded but file move failed (not critical)
                    warning_msg = f"Transfer succeeded but file move failed: {move_msg}"
                    print(f"⚠️ {warning_msg}")
                    
                    self._log_transfer_attempt(
                        qr_code, 
                        'success_with_warning', 
                        warning_msg, 
                        {
                            'response': response_data,
                            'attempts': attempts,
                            'file_move_error': move_msg
                        }
                    )
                    
                    return True, warning_msg, {
                        'step': 'completed_with_warning',
                        'response': response_data,
                        'attempts': attempts,
                        'warning': move_msg
                    }
            else:
                # Step 3: Move file to failed folder
                print(f"\n📁 Step 3: Moving file to failed folder...")
                move_success, new_path, move_msg = self.nip_generator.move_nip_file(
                    file_path, 
                    'pending', 
                    'failed'
                )
                
                error_msg = f"Failed to send {qr_code} after {attempts} attempts: {message}"
                print(f"💀 {error_msg}")
                
                # Log failed transfer
                self._log_transfer_attempt(
                    qr_code, 
                    'failed', 
                    error_msg, 
                    {
                        'attempts': attempts,
                        'final_error': message,
                        'file_path': new_path if move_success else file_path
                    }
                )
                
                return False, error_msg, {
                    'step': 'transfer_failed',
                    'attempts': attempts,
                    'error': message,
                    'file_path': new_path if move_success else file_path
                }
                
        except Exception as e:
            error_msg = f"Unexpected error processing OK status for {inspection_record.image_id}: {str(e)}"
            print(f"💥 {error_msg}")
            logger.error(error_msg)
            
            self._log_transfer_attempt(
                getattr(inspection_record, 'image_id', 'unknown'), 
                'error', 
                error_msg
            )
            
            return False, error_msg, {'step': 'error', 'error': str(e)}
    
    def retry_failed_transfers(self):
        """
        Retry all failed .nip file transfers
        
        Returns:
            dict: Results of retry attempts
        """
        try:
            print(f"\n🔄 Starting retry of failed transfers...")
            
            # Get failed files
            failed_files = self.nip_generator.get_failed_files()
            
            if not failed_files:
                print(f"✅ No failed files to retry")
                return {'total': 0, 'successful': 0, 'failed': 0, 'results': []}
            
            results = {
                'total': len(failed_files),
                'successful': 0,
                'failed': 0,
                'results': []
            }
            
            print(f"📋 Found {len(failed_files)} failed files to retry")
            
            for file_path in failed_files:
                qr_code = file_path.stem  # filename without .nip extension
                
                print(f"\n🔄 Retrying: {qr_code}")
                
                # Attempt to send again
                success, response_data, message, attempts = self.server_client.send_with_retry(
                    str(file_path), 
                    qr_code
                )
                
                if success:
                    # Move to sent folder
                    move_success, new_path, move_msg = self.nip_generator.move_nip_file(
                        str(file_path), 
                        'failed', 
                        'sent'
                    )
                    
                    print(f"✅ Retry successful: {qr_code}")
                    results['successful'] += 1
                    
                    # Log successful retry
                    self._log_transfer_attempt(
                        qr_code, 
                        'retry_success', 
                        f"Retry successful after {attempts} attempts", 
                        {
                            'response': response_data,
                            'attempts': attempts,
                            'file_path': new_path if move_success else str(file_path)
                        }
                    )
                    
                    results['results'].append({
                        'qr_code': qr_code,
                        'status': 'success',
                        'attempts': attempts,
                        'message': message
                    })
                else:
                    print(f"❌ Retry failed: {qr_code}")
                    results['failed'] += 1
                    
                    # Log failed retry
                    self._log_transfer_attempt(
                        qr_code, 
                        'retry_failed', 
                        f"Retry failed after {attempts} attempts: {message}", 
                        {
                            'attempts': attempts,
                            'error': message
                        }
                    )
                    
                    results['results'].append({
                        'qr_code': qr_code,
                        'status': 'failed',
                        'attempts': attempts,
                        'message': message
                    })
            
            print(f"\n📊 Retry Summary:")
            print(f"   - Total: {results['total']}")
            print(f"   - Successful: {results['successful']}")
            print(f"   - Failed: {results['failed']}")
            
            return results
            
        except Exception as e:
            error_msg = f"Error during retry process: {str(e)}"
            print(f"💥 {error_msg}")
            logger.error(error_msg)
            return {'error': error_msg}
    
    def test_system(self):
        """
        Test the complete file transfer system
        
        Returns:
            dict: Test results
        """
        try:
            print(f"\n🧪 Testing File Transfer System...")
            
            results = {
                'server_connection': False,
                'nip_generation': False,
                'file_transfer': False,
                'overall': False,
                'details': {}
            }
            
            # Test 1: Server connection
            print(f"\n1️⃣ Testing server connection...")
            connection_success, connection_msg = self.server_client.test_connection()
            results['server_connection'] = connection_success
            results['details']['connection'] = connection_msg
            
            if not connection_success:
                print(f"❌ Server connection failed: {connection_msg}")
                return results
            
            # Test 2: Send test payload
            print(f"\n2️⃣ Testing server communication...")
            test_success, test_response, test_msg = self.server_client.send_test_payload()
            results['file_transfer'] = test_success
            results['details']['communication'] = {
                'success': test_success,
                'message': test_msg,
                'response': test_response
            }
            
            # Test 3: NIP file generation (mock inspection)
            print(f"\n3️⃣ Testing .nip file generation...")
            try:
                # Create a mock inspection record for testing
                mock_inspection = type('MockInspection', (), {
                    'image_id': 'TEST_NIP_001',
                    'overall_result': 'PASS',
                    'nut1_status': 'PRESENT',
                    'nut2_status': 'PRESENT',
                    'nut3_status': 'PRESENT',
                    'nut4_status': 'PRESENT',
                    'created_at': datetime.now(),
                    'processing_time': 1.5,
                    'user': type('MockUser', (), {'username': 'test_user'})()
                })()
                
                nip_success, nip_path, nip_msg = self.nip_generator.create_nip_file(
                    mock_inspection, 
                    folder='pending'
                )
                
                results['nip_generation'] = nip_success
                results['details']['nip_generation'] = {
                    'success': nip_success,
                    'message': nip_msg,
                    'file_path': nip_path
                }
                
                # Clean up test file
                if nip_success and nip_path and os.path.exists(nip_path):
                    os.remove(nip_path)
                    print(f"🗑️ Cleaned up test .nip file")
                
            except Exception as e:
                results['details']['nip_generation'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Overall result
            results['overall'] = (results['server_connection'] and 
                                results['nip_generation'] and 
                                results['file_transfer'])
            
            print(f"\n📊 System Test Results:")
            print(f"   - Server Connection: {'✅' if results['server_connection'] else '❌'}")
            print(f"   - NIP Generation: {'✅' if results['nip_generation'] else '❌'}")
            print(f"   - File Transfer: {'✅' if results['file_transfer'] else '❌'}")
            print(f"   - Overall: {'✅ PASS' if results['overall'] else '❌ FAIL'}")
            
            return results
            
        except Exception as e:
            error_msg = f"System test error: {str(e)}"
            print(f"💥 {error_msg}")
            logger.error(error_msg)
            return {'error': error_msg}
    
    def get_transfer_statistics(self):
        """Get statistics about file transfers"""
        try:
            # Get .nip file statistics
            nip_stats = self.nip_generator.get_file_statistics()
            
            # Get recent transfer logs
            recent_logs = self._get_recent_transfer_logs(limit=10)
            
            # Calculate success rate
            total_attempts = nip_stats['sent'] + nip_stats['failed']
            success_rate = (nip_stats['sent'] / max(total_attempts, 1)) * 100 if total_attempts > 0 else 0
            
            stats = {
                'nip_files': nip_stats,
                'transfer_stats': {
                    'total_attempts': total_attempts,
                    'successful': nip_stats['sent'],
                    'failed': nip_stats['failed'],
                    'pending': nip_stats['pending'],
                    'success_rate': round(success_rate, 2)
                },
                'recent_logs': recent_logs,
                'server_config': self.server_client.get_server_info()
            }
            
            print(f"\n📊 Transfer Statistics:")
            print(f"   - Success Rate: {success_rate:.1f}%")
            print(f"   - Total Attempts: {total_attempts}")
            print(f"   - Successful: {nip_stats['sent']}")
            print(f"   - Failed: {nip_stats['failed']}")
            print(f"   - Pending: {nip_stats['pending']}")
            
            return stats
            
        except Exception as e:
            error_msg = f"Error getting statistics: {str(e)}"
            print(f"💥 {error_msg}")
            return {'error': error_msg}
    
    def _log_transfer_attempt(self, qr_code, status, message, details=None):
        """Log transfer attempt to file"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'qr_code': qr_code,
                'status': status,
                'message': message,
                'details': details or {}
            }
            
            # Create daily log file
            log_date = datetime.now().strftime('%Y%m%d')
            log_file = self.log_folder / f"transfer_log_{log_date}.json"
            
            # Append to log file
            log_entries = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_entries = json.load(f)
                except json.JSONDecodeError:
                    log_entries = []
            
            log_entries.append(log_entry)
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_entries, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Transfer log: {qr_code} - {status} - {message}")
            
        except Exception as e:
            logger.error(f"Failed to write transfer log: {str(e)}")
    
    def _get_recent_transfer_logs(self, limit=10):
        """Get recent transfer log entries"""
        try:
            all_logs = []
            
            # Get recent log files (last 7 days)
            for i in range(7):
                log_date = datetime.now().strftime('%Y%m%d')
                log_file = self.log_folder / f"transfer_log_{log_date}.json"
                
                if log_file.exists():
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            daily_logs = json.load(f)
                            all_logs.extend(daily_logs)
                    except json.JSONDecodeError:
                        continue
            
            # Sort by timestamp and return recent entries
            all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return all_logs[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recent logs: {str(e)}")
            return []
    
    def cleanup_old_files(self, days_old=30):
        """Clean up old files and logs"""
        try:
            print(f"\n🧹 Starting cleanup of files older than {days_old} days...")
            
            # Clean up old .nip files
            nip_cleaned = self.nip_generator.cleanup_old_files(days_old)
            
            # Clean up old log files
            log_cleaned = 0
            import time
            current_time = time.time()
            cutoff_time = current_time - (days_old * 24 * 3600)
            
            for log_file in self.log_folder.glob('transfer_log_*.json'):
                if log_file.stat().st_mtime < cutoff_time:
                    try:
                        log_file.unlink()
                        log_cleaned += 1
                        print(f"🗑️ Cleaned old log: {log_file.name}")
                    except Exception as e:
                        print(f"⚠️ Could not clean {log_file.name}: {e}")
            
            print(f"🧹 Cleanup completed:")
            print(f"   - .nip files cleaned: {nip_cleaned}")
            print(f"   - Log files cleaned: {log_cleaned}")
            
            return {'nip_files': nip_cleaned, 'log_files': log_cleaned}
            
        except Exception as e:
            error_msg = f"Cleanup error: {str(e)}"
            print(f"💥 {error_msg}")
            return {'error': error_msg}