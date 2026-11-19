@echo off
title AI Viral Video Clipper
echo ===================================================
echo       Starting AI Viral Video Clipper (9:16)
echo ===================================================
echo.

if not exist .venv (
    echo Virtual environment not found. Please setup first.
    pause
    exit /b 1
)

echo Opening web browser at http://localhost:5000 ...
start http://localhost:5000

echo Starting Flask server...
.\.venv\Scripts\python.exe app.py
pause
