@echo off
echo 🚀 Starting Nirob's Complete RTSP Web System...
echo.

echo 📂 Checking project directory...
cd /d "c:\LEVEL-3 SEM-1\LEVEL-3 SEM-1\Computer Networks Sessional-314\RTSP_RTP_Lab"

echo 📦 Installing required packages...
pip install flask flask-socketio pillow > nul 2>&1

echo 🎬 Starting RTSP Server (Background)...
start /B python rtsp_server.py

echo ⏳ Waiting for RTSP server to initialize...
timeout /t 3 /nobreak > nul

echo 🌐 Starting Web Server...
echo.
echo 📱 Access URLs:
echo    Local:    http://localhost:5000
echo    Network:  http://%COMPUTERNAME%:5000
echo.
echo 🎮 Instructions:
echo    1. Open browser and go to http://localhost:5000
echo    2. Click "Start RTSP Server" 
echo    3. Click "Connect"
echo    4. Click "SETUP"
echo    5. Click "PLAY" to watch Nirob video!
echo.
echo Press Ctrl+C to stop all servers...
echo.

python web_rtsp_server.py