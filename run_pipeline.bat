@echo off
chcp 65001 >nul
echo.
echo ========================================
echo 🚀 TraceParts Pipeline V2 - 后端流水线
echo ========================================
echo.

REM 设置Python路径
set PYTHONPATH=%cd%

REM 创建日志目录
if not exist "results" mkdir results
if not exist "results\logs" mkdir results\logs

REM 生成时间戳
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set timestamp=%datetime:~0,8%_%datetime:~8,6%

echo 📝 日志将保存到: results\logs\pipeline_%timestamp%.log
echo ⏱️  开始时间: %date% %time%
echo.

REM 运行流水线
python run_pipeline_v2.py --workers 32

if errorlevel 1 (
    echo.
    echo ❌ 流水线运行失败
    echo 💡 请检查日志文件
) else (
    echo.
    echo ✅ 流水线运行完成
    echo 📋 使用 copy_data.bat 复制数据到前端
)

echo.
pause
