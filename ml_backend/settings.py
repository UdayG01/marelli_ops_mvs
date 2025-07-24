# ml_backend/settings.py

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-your-secret-key-here-change-in-production'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Add this line to settings.py
AUTH_USER_MODEL = 'ml_api.CustomUser'

# Add these for login/logout redirects
LOGIN_URL = '/api/ml/login/'
LOGIN_REDIRECT_URL = '/api/ml/dashboard/'
LOGOUT_REDIRECT_URL = '/api/ml/login/'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',  # Add this for CORS
    'ml_api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Keep CORS at the top
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # Sessions before CSRF
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF after sessions and common
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS Configuration - Fixed for CSRF compatibility
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

CORS_ALLOW_CREDENTIALS = True
# CORS_ALLOW_ALL_ORIGINS = True  # Disabled to prevent CSRF conflicts

# CSRF Configuration - Added for better security
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000", 
    "http://localhost:3001",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Session Configuration - Added for CSRF token stability
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS
CSRF_COOKIE_HTTPONLY = False  # Must be False for JavaScript access
CSRF_COOKIE_SAMESITE = 'Lax'

ROOT_URLCONF = 'ml_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ml_backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10MB

# Industrial Nut Detection Settings
NUT_DETECTION_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'industrial_nut_detection.pt')

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'nut_detection.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'ml_api': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}


# 🆕 NEW: Enhanced Media Settings for Auto-Processing
# Media directories for auto-processing workflow
MEDIA_SUBDIRS = {
    'INSPECTIONS_ORIGINAL': 'inspections/original/',
    'INSPECTIONS_RESULTS': 'inspections/results/',
    'DETECTION_RESULTS': 'detection_results/',
    'THUMBNAILS': 'thumbnails/',
}

# Create media directories on startup
for subdir in MEDIA_SUBDIRS.values():
    full_path = os.path.join(MEDIA_ROOT, subdir)
    os.makedirs(full_path, exist_ok=True)

# 🆕 NEW: Auto-Processing Configuration
AUTO_PROCESSING_CONFIG = {
    'ENABLED': True,
    'AUTO_SAVE_RESULTS': True,
    'AUTO_ADVANCE_TO_NEXT': True,
    'DEFAULT_CONFIDENCE_THRESHOLD': 0.5,
    'DEFAULT_IOU_THRESHOLD': 0.45,
    'EXPECTED_NUT_COUNT': 4,
    'PROCESSING_TIMEOUT_SECONDS': 300,
    'MAX_IMAGE_SIZE_MB': 10,
    'SUPPORTED_IMAGE_FORMATS': ['jpg', 'jpeg', 'png', 'bmp'],
}

# 🆕 NEW: Result Visualization Settings
RESULT_VISUALIZATION = {
    'SHOW_CONFIDENCE_SCORES': True,
    'SHOW_BOUNDING_BOXES': True,
    'SHOW_CENTER_MARKERS': False,
    'BOX_THICKNESS': 4,
    'FONT_SCALE': 0.6,
    'OVERLAY_TRANSPARENCY': 0.7,
}

# 🆕 NEW: QR Scanner Settings (for future implementation)
QR_SCANNER_CONFIG = {
    'ENABLED': False,  # Will be enabled when RS-232 integration is ready
    'PORT': 'COM1',
    'BAUDRATE': 9600,
    'TIMEOUT_SECONDS': 5,
    'VALIDATION_REGEX': r'^[A-Za-z0-9_-]+$',
    'MAX_ID_LENGTH': 50,
}



# ml_backend/settings.py - Add at the end

# YOLOv8 Model Configuration
NUT_DETECTION_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'industrial_nut_detection.pt')

# Media files configuration for image storage
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 📷 CAMERA SETTINGS - Added for Hikrobot Camera Integration
# Create camera captures directory
os.makedirs(os.path.join(MEDIA_ROOT, 'captures'), exist_ok=True)

# Camera-specific logging (extends existing logging configuration)
LOGGING['loggers']['camera'] = {
    'handlers': ['file', 'console'],
    'level': 'INFO',
    'propagate': True,
}

# Camera configuration
CAMERA_CONFIG = {
    'CAPTURE_QUALITY': 80,  # JPEG quality (1-100)
    'STREAM_FPS': 30,       # Video stream frame rate
    'TIMEOUT_MS': 1000,     # Frame capture timeout
    'DEFAULT_SAVE_PATH': os.path.join(MEDIA_ROOT, 'captures'),
}

# Update MEDIA_SUBDIRS to include camera captures
MEDIA_SUBDIRS['CAMERA_CAPTURES'] = 'captures/'

# Create camera captures directory
full_path = os.path.join(MEDIA_ROOT, MEDIA_SUBDIRS['CAMERA_CAPTURES'])
os.makedirs(full_path, exist_ok=True)


# 🆕 NEW: FILE TRANSFER CONFIGURATION - ADD AT THE END OF settings.py

# FILE TRANSFER SETTINGS
FILE_TRANSFER_CONFIG = {
    # 🔧 EXTERNAL SERVER SETTINGS - CHANGE THESE AS NEEDED
    'EXTERNAL_SERVER_IP': '192.168.0.104',      # Target server IP address
    'EXTERNAL_SERVER_PORT': 8080,               # Target server port
    'EXTERNAL_SERVER_ENDPOINT': '/receive_nip', # API endpoint on target server
    
    # 🔧 TRANSFER BEHAVIOR SETTINGS
    'AUTO_TRANSFER_ON_OK': True,                 # Enable/disable automatic transfer
    'MAX_RETRY_ATTEMPTS': 3,                     # Number of retry attempts
    'RETRY_DELAYS': [5, 15, 30],                # Seconds between retries
    'REQUEST_TIMEOUT': 30,                       # HTTP request timeout in seconds
    
    # 🔧 MAINTENANCE SETTINGS
    'CLEANUP_DAYS': 30,                          # Days to keep old files/logs
    'LOG_TRANSFER_ATTEMPTS': True,               # Enable transfer logging
}

# 🆕 NEW: CREATE NIP FILES DIRECTORY
NIP_FILES_ROOT = os.path.join(MEDIA_ROOT, 'nip_files')
os.makedirs(NIP_FILES_ROOT, exist_ok=True)

# 🆕 NEW: CREATE TRANSFER LOGS DIRECTORY  
TRANSFER_LOGS_ROOT = os.path.join(MEDIA_ROOT, 'transfer_logs')
os.makedirs(TRANSFER_LOGS_ROOT, exist_ok=True)

# 🆕 NEW: UPDATE MEDIA_SUBDIRS TO INCLUDE NEW FOLDERS
MEDIA_SUBDIRS.update({
    'NIP_FILES_PENDING': 'nip_files/pending/',
    'NIP_FILES_SENT': 'nip_files/sent/',
    'NIP_FILES_FAILED': 'nip_files/failed/',
    'TRANSFER_LOGS': 'transfer_logs/',
})

# Create new media directories
for subdir in ['nip_files/pending/', 'nip_files/sent/', 'nip_files/failed/', 'transfer_logs/']:
    full_path = os.path.join(MEDIA_ROOT, subdir)
    os.makedirs(full_path, exist_ok=True)

print(f"📁 File transfer directories created:")
print(f"   - NIP Files: {NIP_FILES_ROOT}")
print(f"   - Transfer Logs: {TRANSFER_LOGS_ROOT}")

# ============================================================================
# 🎯 ADMIN CONFIGURATION - YOU CAN EDIT THIS SECTION
# ============================================================================

# Predefined admin usernames (must match simple_auth_views.py)
PREDEFINED_ADMIN_USERS = [
    'admin',
    'supervisor', 
    'manager',
    # ADD MORE ADMIN USERNAMES HERE
]

# Admin settings
ADMIN_AUTO_PROMOTION = True  # Auto-promote predefined admins
ADMIN_EMAIL_DOMAIN = 'company.com'  # Default email domain for admin accounts