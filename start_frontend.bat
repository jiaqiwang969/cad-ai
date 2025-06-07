@echo off
chcp 65001 >nul
echo.
echo ========================================
echo 🎨 TraceParts Pipeline V2 - 前端界面
echo ========================================
echo.

if not exist "cad-ai-frontend" (
    echo ❌ 前端项目不存在，请先运行 setup_windows.bat
    echo.
    pause
    exit /b 1
)

echo 📋 复制数据文件到前端...
call copy_data.bat

echo.
echo 🚀 启动前端开发服务器...
echo 🌐 浏览器将自动打开 http://localhost:3000
echo 💡 按 Ctrl+C 停止服务器
echo.

cd cad-ai-frontend
call npm start

cd ..
pause
