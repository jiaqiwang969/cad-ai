@echo off
chcp 65001 >nul
echo.
echo ========================================
echo 🔍 TraceParts Pipeline V2 - 环境检查
echo ========================================
echo.

echo 📋 检查系统环境...
echo.

REM 检查Python
echo [Python 环境]
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装
) else (
    echo ✅ Python 版本:
    python --version
    echo 📦 pip 版本:
    python -m pip --version
)

echo.

REM 检查Node.js
echo [Node.js 环境]
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js 未安装
) else (
    echo ✅ Node.js 版本:
    node --version
    echo 📦 npm 版本:
    npm --version
)

echo.

REM 检查项目文件
echo [项目文件]
if exist "requirements.txt" (
    echo ✅ requirements.txt 存在
) else (
    echo ❌ requirements.txt 不存在
)

if exist "run_pipeline_v2.py" (
    echo ✅ run_pipeline_v2.py 存在
) else (
    echo ❌ run_pipeline_v2.py 不存在
)

if exist "src" (
    echo ✅ src 目录存在
) else (
    echo ❌ src 目录不存在
)

if exist "cad-ai-frontend" (
    echo ✅ cad-ai-frontend 目录存在
    if exist "cad-ai-frontend\package.json" (
        echo ✅ 前端项目已配置
    ) else (
        echo ⚠️ 前端项目未完全配置
    )
) else (
    echo ❌ cad-ai-frontend 目录不存在
)

echo.

REM 检查数据文件
echo [数据文件]
if exist "results" (
    echo ✅ results 目录存在
    if exist "results