@echo off
chcp 65001 > nul
title BTRC Company Profile & Upstream Audit System
cd /d "%~dp0"
python "company_profile_system\Apps\company_profile_app.py"
pause
