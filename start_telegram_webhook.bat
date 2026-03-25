@echo off
echo 🚀 Starting Telegram Webhook Server...
echo.
echo 📡 Webhook will handle interactive button callbacks
echo.
echo 🌐 Server will run on: http://localhost:8443
echo.
echo 📱 Telegram buttons will be processed automatically
echo.
echo Press Ctrl+C to stop the server
echo.

cd /d "C:\Users\ESSENCE\CascadeProjects\windsurf-project"
python telegram_webhook.py

pause
