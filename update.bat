@echo off
echo ===== FromJapan Monitor Update Script =====
echo.

echo Step 1: Stopping any existing Chrome processes...
taskkill /F /IM chrome.exe 2>NUL
taskkill /F /IM chromedriver.exe 2>NUL
taskkill /F /IM fromjapan.exe 2>NUL
echo.

echo Step 2: Pulling latest changes from GitHub...
cd /d %~dp0
git pull
echo.

echo Step 3: Installing/updating dependencies...
C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe -m pip install selenium==4.9.1 bs4 deep_translator requests psutil pyinstaller
echo.

echo Step 4: Rebuilding EXE with hidden console window...
C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe -m PyInstaller fromjapan.spec --clean
echo.

echo Step 5: Copying updated files to run folder...
if not exist "C:\Users\Administrator\Desktop\fromjpbot" mkdir "C:\Users\Administrator\Desktop\fromjpbot"
copy /Y "fromjapan.py" "C:\Users\Administrator\Desktop\fromjpbot\fromjapan.py"
copy /Y "dist\fromjapan.exe" "C:\Users\Administrator\Desktop\fromjpbot\fromjapan.exe"
copy /Y "*.txt" "C:\Users\Administrator\Desktop\fromjpbot\" 2>NUL
echo.

echo ===== Update Complete! =====
echo The updated script and executable have been placed in C:\Users\Administrator\Desktop\fromjpbot
echo.
pause