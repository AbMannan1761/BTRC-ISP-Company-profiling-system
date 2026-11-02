@echo off
chcp 65001 > nul
title BTRC Master Excel to System Synchronizer
cd /d "%~dp0"
echo ======================================================================
echo   BTRC_DIS_Master_Database.xlsx হতে সিস্টেমে ডাটা সিঙ্ক ও আপডেট
echo ======================================================================
echo.
python "company_profile_system\Apps\import_excel_to_system.py"
echo.
echo ======================================================================
echo   সিঙ্ক সম্পন্ন হয়েছে! ডাটাবেজ ও ড্যাশবোর্ড সফলভাবে হালনাগাদ করা হয়েছে।
echo ======================================================================
pause
