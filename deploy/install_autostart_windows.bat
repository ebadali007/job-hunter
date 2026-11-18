@echo off
echo ==============================================================
echo Installing Global Job Hunter into Windows Startup...
echo ==============================================================

set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT=%STARTUP_DIR%\JobHunterAutostart.lnk
set VBS_TARGET=c:\Users\User\Downloads\job-hunter\deploy\run_silent.vbs

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%VBS_TARGET%\"'; $s.WorkingDirectory = 'c:\Users\User\Downloads\job-hunter'; $s.Save()"

echo.
echo [SUCCESS] Job Hunter added to Windows Startup!
echo It will now run automatically in the background whenever your PC boots up.
echo No terminal window will open, and it will hunt jobs 24/7 every 1 hour.
echo.
pause
