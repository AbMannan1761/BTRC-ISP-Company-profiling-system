@echo off
chcp 65001 > nul
title BTRC DIS Master Database Cache & Excel Sync Engine
cd /d "%~dp0"
echo ======================================================================
echo   BTRC DIS পোর্টাল হতে সকল অপারেটরের ডাটা ডাউনলোড ও এক্সেল সিঙ্ক
echo ======================================================================
echo.
python "company_profile_system\Apps\sync_dis_master.py"
echo.
echo ======================================================================
echo   সিঙ্ক সম্পন্ন হয়েছে! BTRC_DIS_Master_Database.xlsx হালনাগাদ করা হয়েছে।
echo ======================================================================
pause
