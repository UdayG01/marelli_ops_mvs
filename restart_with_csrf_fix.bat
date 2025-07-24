@echo off
echo 🔄 Restarting Django Development Server with CSRF Fixes
echo ====================================================

echo.
echo 🛑 Stopping any existing Django processes...
taskkill /f /im python.exe 2>nul

echo.
echo 🧹 Clearing Django cache...
if exist .\db.sqlite3 (
    echo   - Found database: db.sqlite3
)

echo.
echo 🔧 Running CSRF diagnostics...
python csrf_fix.py

echo.
echo 🚀 Starting Django development server...
echo   Navigate to: http://localhost:8000/api/ml/
echo   CSRF Test page: http://localhost:8000/api/ml/debug/csrf-test/
echo.
echo Press Ctrl+C to stop the server
echo.

python manage.py runserver 0.0.0.0:8000
