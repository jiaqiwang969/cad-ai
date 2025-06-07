@echo off
chcp 65001 >nul
echo.
echo ========================================
echo 🚀 TraceParts Pipeline V2 - Windows 安装脚本
echo ========================================
echo.

echo 📋 检查环境...
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.8+
    echo 💡 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
) else (
    echo ✅ Python 已安装
    python --version
)

REM 检查Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Node.js，请先安装 Node.js 16+
    echo 💡 下载地址: https://nodejs.org/
    echo.
    pause
    exit /b 1
) else (
    echo ✅ Node.js 已安装
    node --version
)

echo.
echo 🔧 安装 Python 依赖...
python -m pip install -r requirements.txt --break-system-packages
if errorlevel 1 (
    echo ❌ Python 依赖安装失败
    pause
    exit /b 1
) else (
    echo ✅ Python 依赖安装成功
)

echo.
echo 📥 安装 Playwright 浏览器...
python -m playwright install chromium --with-deps
if errorlevel 1 (
    echo ⚠️ Playwright 安装可能失败，但不影响基本功能
) else (
    echo ✅ Playwright 安装成功
)

echo.
echo 🎨 设置前端项目...
if not exist "cad-ai-frontend" (
    echo 🔧 初始化前端项目...
    call npx create-react-app cad-ai-frontend --template typescript
    if errorlevel 1 (
        echo ❌ 前端项目初始化失败
        pause
        exit /b 1
    )
) else (
    echo ✅ 前端项目已存在
)

cd cad-ai-frontend
echo 📦 安装前端依赖...
call npm install antd
if errorlevel 1 (
    echo ❌ 前端依赖安装失败
    cd ..
    pause
    exit /b 1
) else (
    echo ✅ 前端依赖安装成功
)
cd ..

echo.
echo ========================================
echo ✅ 安装完成！
echo ========================================
echo.
echo 📋 使用说明：
echo   🔹 run_pipeline.bat     - 运行后端流水线
echo   🔹 start_frontend.bat   - 启动前端界面
echo   🔹 copy_data.bat        - 复制数据到前端
echo   🔹 check_env.bat        - 检查环境状态
echo.
pause
