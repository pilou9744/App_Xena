@echo off
setlocal
cd /d "%~dp0"
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --onefile --name GeckoCareXena --add-data "templates;templates" --add-data "static;static" --add-data "schema.sql;." --add-data "data;data" desktop_launcher.py
echo.
echo Fichier cree dans dist\GeckoCareXena.exe
pause
