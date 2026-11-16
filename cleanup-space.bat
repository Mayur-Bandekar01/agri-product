@echo off
echo.
echo ================================================================
echo    SPACE CLEANUP - REMOVING OLD BUILD ARTIFACTS
echo ================================================================
echo.
echo This will delete:
echo   - dist/ (1.9 GB)
echo   - desktop/release/ (1.3 GB)
echo   - build-archive/ (233 MB)
echo   - desktop/backend-dist/ (65 MB)
echo   - build/ (46 MB)
echo   - desktop/.pyinstaller-work/ (44 MB)
echo.
echo Total space to reclaim: ~3.5 GB
echo.
echo Your source code, database, and dependencies will NOT be touched.
echo These folders will be regenerated on next build.
echo.
pause
echo.

REM Delete dist
if exist "dist" (
    echo Deleting dist...
    rmdir /s /q "dist"
    echo   - dist deleted
)

REM Delete build
if exist "build" (
    echo Deleting build...
    rmdir /s /q "build"
    echo   - build deleted
)

REM Delete build-archive
if exist "build-archive" (
    echo Deleting build-archive...
    rmdir /s /q "build-archive"
    echo   - build-archive deleted
)

REM Delete desktop/release
if exist "desktop\release" (
    echo Deleting desktop/release...
    rmdir /s /q "desktop\release"
    echo   - desktop/release deleted
)

REM Delete desktop/backend-dist
if exist "desktop\backend-dist" (
    echo Deleting desktop/backend-dist...
    rmdir /s /q "desktop\backend-dist"
    echo   - desktop/backend-dist deleted
)

REM Delete desktop/.pyinstaller-work
if exist "desktop\.pyinstaller-work" (
    echo Deleting desktop/.pyinstaller-work...
    rmdir /s /q "desktop\.pyinstaller-work"
    echo   - desktop/.pyinstaller-work deleted
)

REM Delete .pytest_cache
if exist ".pytest_cache" (
    echo Deleting .pytest_cache...
    rmdir /s /q ".pytest_cache"
    echo   - .pytest_cache deleted
)

echo.
echo ================================================================
echo    CLEANUP COMPLETE!
echo ================================================================
echo.
echo Freed approximately 3.5 GB of space.
echo.
echo Your project size: ~4 GB --^> ~500 MB
echo.
echo Next build (build-production.bat) will regenerate these folders.
echo.
echo IMPORTANT: node_modules and backend/venv were kept intact.
echo            Your project is ready to build immediately!
echo.
pause
