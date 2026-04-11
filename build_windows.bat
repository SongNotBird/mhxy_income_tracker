@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name MHXYIncomeTracker ^
  main.py

echo.
echo 打包完成，exe 位置：
echo %~dp0dist\MHXYIncomeTracker.exe
pause
