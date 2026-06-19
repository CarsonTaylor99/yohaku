@echo off
REM yohaku - double-click to launch. Bridges into WSL to run start.sh against
REM the Linux venv (which is where Python and the SDKs actually live).
REM
REM Once you see "Uvicorn running on http://127.0.0.1:8000", open that URL in
REM your browser. Ctrl+C in this window stops the server.

wsl -- bash -lc "cd ~/yohaku && ./start.sh"

echo.
echo Server stopped.
pause
