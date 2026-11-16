@echo off
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo    ADINATH AGRI SERVICES - PRODUCTION BUILD SCRIPT
echo ================================================================
echo.
echo This script will:
echo   [1] Clean previous builds
echo   [2] Run backend tests
echo   [3] Build Python backend with PyInstaller
echo   [4] Build Electron desktop application
echo   [5] Create Windows installer
echo.
echo ================================================================
echo.

REM Get start time
set START_TIME=%TIME%

REM Step 1: Clean previous builds
echo [1/5] Cleaning previous builds...
if exist "desktop\backend-dist" (
    rmdir /s /q "desktop\backend-dist" 2>nul
)
if exist "desktop\release" (
    rmdir /s /q "desktop\release" 2>nul
)
if exist "desktop\.pyinstaller-work" (
    rmdir /s /q "desktop\.pyinstaller-work" 2>nul
)
if exist "build" (
    rmdir /s /q "build" 2>nul
)
if exist "dist" (
    rmdir /s /q "dist" 2>nul
)
echo    ✓ Cleanup complete
echo.

REM Step 2: Run backend tests
echo [2/5] Running backend tests...
cd backend
if not exist "venv\Scripts\activate.bat" (
    echo    ERROR: Virtual environment not found!
    echo    Please run: python -m venv venv
    echo    Then: venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python -m pytest -q --tb=short
if !ERRORLEVEL! NEQ 0 (
    echo.
    echo    ✗ Tests FAILED - Build aborted
    echo    Fix the failing tests before building production version
    echo.
    pause
    exit /b 1
)
echo    ✓ All tests passed
cd ..
echo.

REM Step 3: Build backend with PyInstaller
echo [3/5] Building backend executable with PyInstaller...
echo    This may take 2-3 minutes...
python -m PyInstaller --noconfirm --distpath desktop\backend-dist --workpath desktop\.pyinstaller-work AdinathAgriBackend.spec
if !ERRORLEVEL! NEQ 0 (
    echo.
    echo    ✗ Backend build FAILED
    echo    Check the error messages above
    echo.
    pause
    exit /b 1
)
echo    ✓ Backend executable created
echo.

REM Step 4: Verify backend build
echo [4/5] Verifying backend build...
if not exist "desktop\backend-dist\AdinathAgriBackend\AdinathAgriBackend.exe" (
    echo    ✗ Backend executable not found!
    pause
    exit /b 1
)
echo    ✓ Backend verification passed
echo.

REM Step 5: Build Electron desktop application
echo [5/5] Building Windows desktop installer...
echo    This may take 3-5 minutes...
call npm run desktop:dist
if !ERRORLEVEL! NEQ 0 (
    echo.
    echo    ✗ Desktop build FAILED
    echo    Make sure Node.js and npm dependencies are installed
    echo    Run: npm install
    echo.
    pause
    exit /b 1
)
echo    ✓ Desktop installer created
echo.

REM Calculate build time
set END_TIME=%TIME%

echo ================================================================
echo    BUILD COMPLETE!
echo ================================================================
echo.
echo Installer location:
echo    desktop\release\Adinath-Agri-Services-Setup-1.0.0.exe
echo.

if exist "desktop\release\Adinath-Agri-Services-Setup-1.0.0.exe" (
    for %%A in ("desktop\release\Adinath-Agri-Services-Setup-1.0.0.exe") do (
        set SIZE=%%~zA
        set /a SIZE_MB=!SIZE! / 1048576
        echo Installer size: !SIZE_MB! MB
    )
    echo.
    echo NEXT STEPS:
    echo   1. Test the installer on a clean Windows machine
    echo   2. Verify database backups work correctly
    echo   3. Test billing, products, and reports
    echo   4. Create user documentation
    echo   5. Deliver to shop owner
    echo.
    echo IMPORTANT REMINDERS:
    echo   • First run will require admin account creation
    echo   • Database is stored in: %%APPDATA%%\adinath-agri-services-desktop\data
    echo   • Backups are automatic on startup and shutdown
    echo   • Manual backups recommended weekly
    echo.
) else (
    echo ✗ WARNING: Installer file not found!
    echo Check desktop\release directory manually
    echo.
)

echo ================================================================
echo.
pause
