@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Building with PyInstaller...
python -m PyInstaller --noconfirm --clean --log-level ERROR balance_gui.spec > build.log 2>&1
if errorlevel 1 goto :buildfail

echo [2/4] Extracting product...
if exist app rmdir /s /q app
mkdir app
move /y "dist\EquationBalancer.exe" "app\" >nul
if errorlevel 1 goto :extractfail

echo [3/4] Cleaning up build and dist...
rmdir /s /q build
rmdir /s /q dist
del /q build.log

echo [4/4] Building installer with Inno Setup...
set "ISCC="
where ISCC >nul 2>&1 && set "ISCC=ISCC"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC goto :noinno

"%ISCC%" /Q installer.iss
if errorlevel 1 goto :innofail

echo Done. Launching installer...
start "" /wait "installer\EquationBalancer_Setup.exe"
exit /b 0

:buildfail
echo.
echo PyInstaller failed. Log:
type build.log
exit /b 1

:extractfail
echo Could not find dist\EquationBalancer.exe
exit /b 1

:noinno
echo Inno Setup 6 not found. Install it from https://jrsoftware.org/isdl.php
exit /b 1

:innofail
echo Inno Setup compile failed.
exit /b 1
