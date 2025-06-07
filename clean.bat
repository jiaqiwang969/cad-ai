@echo off
chcp 65001 >nul
echo.
echo ========================================
echo 🧹 TraceParts Pipeline V2 - 清理脚本
echo ========================================
echo.

echo ⚠️  这将清理以下内容：
echo   🔹 Python 缓存文件 (__pycache__)
echo   🔹 临时文件和日志
echo   🔹 前端 node_modules (可选)
echo.

set /p confirm="确认清理？(y/N): "
if /i "%confirm%" neq "y" (
    echo 操作已取消
    pause
    exit /b 0
)

echo.
echo 🧹 清理 Python 缓存...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc >nul 2>&1

echo 🧹 清理临时文件...
if exist "results\*.json" del /q "results\*.json"
if exist "results\*.jsonl" del /q "results\*.jsonl"

echo 🧹 清理日志文件...
if exist "results\logs\*" del /q "results\logs\*"

set /p clean_node="是否清理前端 node_modules？(会需要重新 npm install) (y/N): "
if /i "%clean_node%" equ "y" (
    if exist "cad-ai-frontend
ode_modules" (
        echo 🧹 清理前端 node_modules...
        rd /s /q "cad-ai-frontend
ode_modules"
    )
    if exist "cad-ai-frontend\package-lock.json" (
        del /q "cad-ai-frontend\package-lock.json"
    )
)

echo.
echo ✅ 清理完成！
echo.
pause
