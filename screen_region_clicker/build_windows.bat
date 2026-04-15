@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"

set "PYTHON_CMD=python"
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] 找不到 python，请先安装 Windows 版 Python 3.10 或更高版本。
    echo 下载地址：https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
  set "PYTHON_CMD=py -3"
)

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] 创建虚拟环境 .venv
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto failed
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto failed

echo [INFO] 安装依赖
python -m pip install --upgrade pip
if errorlevel 1 goto failed
pip install -r requirements.txt
if errorlevel 1 goto failed
pip install pyinstaller
if errorlevel 1 goto failed

echo [INFO] 开始打包 Windows exe
pyinstaller --noconfirm --clean ScreenRegionClicker.spec
if errorlevel 1 goto failed

echo.
echo [OK] 打包完成：
echo %cd%\dist\ScreenRegionClicker.exe
echo.
pause
exit /b 0

:failed
echo.
echo [ERROR] 打包失败，请把上面的错误信息发给我。
pause
exit /b 1
