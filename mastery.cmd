@echo off
setlocal
set "DIR=%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
if /I "%~1"=="feedback" (%PY% "%DIR%setup\feedback.py" & exit /b)
if /I "%~1"=="setup" (%PY% "%DIR%setup\xlrte_setup.py" & exit /b)
if not exist "%DIR%config\settings.json" (
  echo Erste Nutzung: die Einrichtung oeffnet sich im Browser.
  %PY% "%DIR%setup\xlrte_setup.py"
  exit /b
)
set "CMD=%~1"
if "%CMD%"=="" set "CMD=run"
%PY% "%DIR%_xlrte\scripts\xlrte.py" %CMD% %2 %3 %4
if "%CMD%"=="run" echo Cockpit: %DIR%XLRTE_Cockpit.html
