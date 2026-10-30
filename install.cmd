@echo off
setlocal
if not exist "%~dp0skills\post-experiment-knowledge\python\python.exe" (
  echo This is a source-only or incomplete package. Download the Windows x64 Beta release ZIP. 1>&2
  exit /b 2
)
"%~dp0skills\post-experiment-knowledge\python\python.exe" -I -B "%~dp0scripts\install.py" %*
set "_EXPKM_INSTALL_EXIT=%errorlevel%"
if not "%~1"=="--no-pause" pause
exit /b %_EXPKM_INSTALL_EXIT%
