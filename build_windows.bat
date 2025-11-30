@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo Building Windows Executable...
pyinstaller --name "ColorAnalysis" --add-data "templates;templates" --add-data "static;static" --onefile app.py

echo Build complete! Check the 'dist' folder.
pause
