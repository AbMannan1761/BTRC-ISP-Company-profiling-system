@echo off
chcp 65001 > nul
title BTRC Company Profile & Regulatory Web Dashboard
cd /d "%~dp0"
echo Starting BTRC Live Regulatory & Audit Dashboard...
python -m streamlit run "company_profile_system\Apps\web_dashboard.py"
pause
