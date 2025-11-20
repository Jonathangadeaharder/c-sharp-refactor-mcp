@echo off
setlocal

echo Building Go dst CLI...

REM Check if Go is installed
where go >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Go is not installed
    echo Please install Go 1.21+ from https://go.dev/dl/
    exit /b 1
)

REM Download dependencies
echo Downloading dependencies...
go mod download
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to download dependencies
    exit /b 1
)

REM Build binary
echo Building binary...
if not exist bin mkdir bin
go build -o bin\go-dst-cli.exe main.go
if %ERRORLEVEL% neq 0 (
    echo Error: Build failed
    exit /b 1
)

echo.
echo Build complete!
echo Binary location: %CD%\bin\go-dst-cli.exe
echo.
echo Test with: echo {"command":"version","parameters":{}} ^| bin\go-dst-cli.exe

endlocal
