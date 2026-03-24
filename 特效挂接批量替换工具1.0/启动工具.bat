@echo off
chcp 65001 >nul
echo ========================================
echo 特效挂接批量替换工具
echo ========================================
echo.
echo 正在启动工具...
echo.

python effect_address_replacer.py

if %errorlevel% neq 0 (
    echo.
    echo 启动失败！请检查：
    echo 1. 是否已安装Python
    echo 2. Python是否已添加到系统PATH
    echo.
    pause
)