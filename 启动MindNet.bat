@echo off
chcp 65001 >nul
title MindNet
set PORT=8765
set URL=http://127.0.0.1:%PORT%/
cd /d "%~dp0backend"

rem 服务已经在运行就直接打开窗口
curl.exe -s -o nul --max-time 2 %URL%api/git/status
if %errorlevel%==0 goto open

start "MindNet 服务" /min python -m uvicorn main:app --host 127.0.0.1 --port %PORT%

set /a tries=0
:wait
ping -n 2 127.0.0.1 >nul
curl.exe -s -o nul --max-time 2 %URL%api/git/status
if %errorlevel%==0 goto open
set /a tries+=1
if %tries% lss 20 goto wait
echo MindNet 服务没有启动成功，请打开任务栏里最小化的“MindNet 服务”窗口查看报错。
pause
exit /b 1

:open
set EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe
if not exist "%EDGE%" set EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe
if exist "%EDGE%" (
  start "" "%EDGE%" --app=%URL%
) else (
  start "" %URL%
)
exit /b 0
