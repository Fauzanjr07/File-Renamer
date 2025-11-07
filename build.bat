@echo off
setlocal
cd /d "%~dp0"

REM Build CLI (console) executable
pyinstaller --noconfirm --onefile --name ImageRenamerCLI "rename_images.py"

REM Build GUI (windowed) executable
pyinstaller --noconfirm --onefile --windowed --name ImageRenamerGUI "gui_rename.py"

echo.
echo Build complete. Check the dist\ folder:
echo   dist\ImageRenamerCLI.exe
echo   dist\ImageRenamerGUI.exe
echo.
pause
