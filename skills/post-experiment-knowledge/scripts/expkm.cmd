@echo off
setlocal
if not exist "%~dp0..\python\python.exe" (
  echo Bundled Python is missing. Use the Windows x64 release package. 1>&2
  exit /b 2
)
"%~dp0..\python\python.exe" -I -B "%~dp0expkm.py" %*
exit /b %errorlevel%
