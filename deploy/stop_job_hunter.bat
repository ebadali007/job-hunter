@echo off
echo Stopping Global Job Hunter background processes...
powershell -Command "Get-NetTCPConnection -LocalPort 8050 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }; Write-Host 'Stopped Job Hunter on Port 8050.'"
pause
