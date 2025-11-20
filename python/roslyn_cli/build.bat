@echo off
REM Build script for Roslyn CLI tool (Windows)

echo Building Roslyn CLI tool...

echo Building release configuration...
dotnet build -c Release
if errorlevel 1 exit /b 1

echo Publishing self-contained executable...
dotnet publish -c Release -r win-x64 --self-contained -o bin
if errorlevel 1 exit /b 1

echo.
echo Build complete!
echo Executable: %CD%\bin\roslyn-cli.exe
echo.
echo Test with:
echo   echo {"command":"version","parameters":{}} ^| .\bin\roslyn-cli.exe
