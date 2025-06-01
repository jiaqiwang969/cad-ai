#!/bin/bash
# 生产环境快速启动脚本
# ====================
# 一键启动优化版Pipeline和监控系统

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查虚拟环境
check_venv() {
    if [ ! -d "venv" ]; then
        log_error "虚拟环境不存在，请先运行: make deploy"
        exit 1
    fi
}

# 启动监控
start_monitor() {
    log_info "启动健康监控..."
    
    # 检查是否已在运行
    if pgrep -f "health_monitor.py" > /dev/null; then
        log_warn "健康监控已在运行"
    else
        nohup python scripts/health_monitor.py > logs/monitor.out 2>&1 &
        MONITOR_PID=$!
        echo $MONITOR_PID > .monitor.pid
        log_info "健康监控已启动 (PID: $MONITOR_PID)"
    fi
}

# 启动Pipeline
start_pipeline() {
    log_info "启动优化版Pipeline..."
    
    # 设置环境变量
    export ENV=production
    export MAX_WORKERS=${MAX_WORKERS:-32}
    export HEADLESS=true
    export DISABLE_IMAGES=true
    export CACHE_ENABLED=true
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 运行Pipeline
    python src/pipelines/optimized_full_pipeline.py --workers $MAX_WORKERS
}

# 停止所有服务
stop_all() {
    log_info "停止所有服务..."
    
    # 停止监控
    if [ -f .monitor.pid ]; then
        MONITOR_PID=$(cat .monitor.pid)
        if kill -0 $MONITOR_PID 2>/dev/null; then
            kill $MONITOR_PID
            log_info "健康监控已停止"
        fi
        rm -f .monitor.pid
    fi
    
    # 停止Pipeline
    pkill -f "optimized_full_pipeline" || true
    
    log_info "所有服务已停止"
}

# 查看状态
show_status() {
    echo "===== 系统状态 ====="
    echo ""
    
    # 检查监控状态
    if pgrep -f "health_monitor.py" > /dev/null; then
        echo "✅ 健康监控: 运行中"
    else
        echo "❌ 健康监控: 未运行"
    fi
    
    # 检查Pipeline状态
    if pgrep -f "optimized_full_pipeline" > /dev/null; then
        echo "✅ Pipeline: 运行中"
    else
        echo "❌ Pipeline: 未运行"
    fi
    
    echo ""
    
    # 显示最近的健康报告
    if [ -f logs/health_report.json ]; then
        echo "最近健康报告:"
        cat logs/health_report.json | python -m json.tool | grep -E "(status|last_run|success_rate)" || true
    fi
    
    echo ""
    echo "===================="
}

# 主函数
main() {
    case "${1:-start}" in
        start)
            check_venv
            start_monitor
            sleep 2
            start_pipeline
            ;;
        monitor)
            check_venv
            start_monitor
            log_info "监控已启动，使用 'tail -f logs/monitor.out' 查看输出"
            ;;
        stop)
            stop_all
            ;;
        restart)
            stop_all
            sleep 2
            check_venv
            start_monitor
            sleep 2
            start_pipeline
            ;;
        status)
            show_status
            ;;
        *)
            echo "使用方法: $0 {start|monitor|stop|restart|status}"
            echo ""
            echo "  start   - 启动Pipeline和监控"
            echo "  monitor - 只启动监控"
            echo "  stop    - 停止所有服务"
            echo "  restart - 重启所有服务"
            echo "  status  - 查看运行状态"
            exit 1
            ;;
    esac
}

# 确保在正确的目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# 创建必要的目录
mkdir -p logs

# 执行主函数
main "$@" 