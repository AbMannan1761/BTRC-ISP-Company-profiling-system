@echo off
chcp 65001 > nul
title BTRC Company Profile & Regulatory Dashboard
cd /d "%~dp0"
echo Opening BTRC Interactive Company Profile & Regulatory Dashboard in Browser...
start "" "BTRC_Company_Profile_Dashboard.html"
exit
