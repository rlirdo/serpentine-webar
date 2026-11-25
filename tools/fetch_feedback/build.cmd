@echo off
chcp 950 >nul
cd /d "%~dp0"
echo [1/3] 安裝相依套件...
python -m pip install -r requirements.txt
echo [2/3] 單元測試...
set PYTHONUTF8=1
python -B test_fetch_feedback.py
if errorlevel 1 (echo 測試失敗，停止打包 & pause & exit /b 1)
echo [3/3] PyInstaller 打包...
python -m PyInstaller --noconfirm --clean --onefile --noconsole --name 撈取GitHub問卷與遊戲前後測資料 --hidden-import openpyxl --hidden-import requests --exclude-module numpy --exclude-module PIL --exclude-module lxml --exclude-module pandas --exclude-module IPython --exclude-module pytest --workpath build --distpath dist --specpath build fetch_feedback.py
if errorlevel 1 (echo 打包失敗 & pause & exit /b 1)
copy /y "dist\撈取GitHub問卷與遊戲前後測資料.exe" "%~dp0" >nul
echo 完成：%~dp0撈取GitHub問卷與遊戲前後測資料.exe
pause
