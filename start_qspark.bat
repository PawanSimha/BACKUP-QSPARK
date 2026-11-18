@echo off
title QSPARK Smart Parking System

:: Change to this script's directory
cd /D "%~dp0"

:: Start the dev server in a background window
start "QSPARK_Server" /B python run.py < nul

:: Wait for the server to bind port 8000
ping -n 4 127.0.0.1 > nul

:: Open in default web browser
start "" http://localhost:8000

exit
