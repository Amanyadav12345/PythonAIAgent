@echo off
echo Setting up AI Agent Chat Application...

echo.
echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Installing Node.js dependencies...
cd frontend\ai-chat
npm install
cd ..\..

echo.
echo Setup complete!
echo.
echo To run the application:
echo 1. Run start-backend.bat to start the FastAPI server
echo 2. Run start-frontend.bat to start the React development server
echo 3. Open http://localhost:3000 in your browser
echo.
echo Default login credentials:
echo Username: admin
echo Password: secret
echo.
pause