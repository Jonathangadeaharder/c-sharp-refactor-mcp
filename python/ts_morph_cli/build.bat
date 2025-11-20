@echo off
setlocal

echo Building ts-morph CLI...

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Node.js is not installed
    echo Please install Node.js 18+ from https://nodejs.org/
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
call npm install
if %ERRORLEVEL% neq 0 (
    echo Error: npm install failed
    exit /b 1
)

REM Build TypeScript
echo Compiling TypeScript...
call npm run build
if %ERRORLEVEL% neq 0 (
    echo Error: TypeScript compilation failed
    exit /b 1
)

echo.
echo Build complete!
echo Binary location: %CD%\dist\index.js
echo.
echo Test with: echo {"command":"version","parameters":{}} ^| node dist\index.js

endlocal
