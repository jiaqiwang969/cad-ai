@echo off
chcp 65001 >nul
echo.
echo ========================================
echo 📋 复制后端数据到前端
echo ========================================
echo.

if not exist "cad-ai-frontend" (
    echo ❌ 前端项目不存在，请先运行 setup_windows.bat
    echo.
    pause
    exit /b 1
)

if not exist "results