@echo off
rem Build a standalone aff4.exe for Windows using PyInstaller.
rem
rem Usage:
rem   build_binary.bat
rem
rem Prerequisites:
rem   pip install pyinstaller
rem   pip install -r requirements.txt
rem
rem Output: dist\aff4.exe

setlocal enableextensions

echo =^> Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo =^> Building standalone binary...
pyinstaller aff4.spec

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo.
echo =^> Build complete. Binary is at: dist\aff4.exe
echo     Test with: dist\aff4.exe --help
