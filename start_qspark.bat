@echo off
title QSPARK Smart Parking System

:: Change to project directory
cd /D "C:\Users\PawanSimha\Conneqtion\Internship\FDE - Projects\SQLITE - QSPARK\BACKUP-QSPARK"

:: Start Flask in background (no console window)
:: Note: "Input redirection is not supported" message may appear but server starts anyway
start "QSPARK_Background" /B python run.py

:: Wait for server to initialize
timeout /t 3

:: Open in default web browser
start "" http://localhost:8000

:: Close this batch window
exit