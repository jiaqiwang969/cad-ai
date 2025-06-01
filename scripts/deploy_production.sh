#!/bin/bash
# 生产环境部署脚本
# ==================
# 部署优化版Pipeline到生产环境

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 未安装，请先安装"
        exit 1
    fi
}

# 主部署函数
deploy() {
    log_info "开始部署TraceParts优化版Pipeline..."
    
    # 1. 检查依赖
    log_info "检查系统依赖..."
    check_command python3
    check_command pip3
    check_command git
    
    # 2. 检查Python版本
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Python版本: $PYTHON_VERSION"
    
    # 3. 创建虚拟环境（如果不存在）
    if [ ! -d "venv" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv venv
    fi
    
    # 4. 激活虚拟环境
    log_info "激活虚拟环境..."
    source venv/bin/activate
    
    # 5. 升级pip
    log_info "升级pip..."
    pip install --upgrade pip
    
    # 6. 安装依赖
    log_info "安装Python依赖..."
    pip install -r requirements.txt
    
    # 7. 安装额外的生产环境依赖
    log_info "安装生产环境依赖..."
    pip install psutil requests
    
    # 8. 创建必要的目录
    log_info "创建目录结构..."
    mkdir -p results/{cache,products}
    mkdir -p logs
    
    # 9. 设置环境变量
    log_info "设置生产环境变量..."
    export ENV=production
    export MAX_WORKERS=32
    export HEADLESS=true
    export DISABLE_IMAGES=true
    export CACHE_ENABLED=true
    export MONITOR_ENABLED=true
    
    # 10. 运行健康检查
    log_info "运行部署前健康检查..."
    python scripts/health_monitor.py --once
    
    # 11. 创建systemd服务文件（如果在Linux上）
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_info "创建systemd服务..."
        create_systemd_service
    fi
    
    # 12. 创建定时任务
    setup_cron_jobs
    
    log_info "部署完成！"
    log_info "使用以下命令运行："
    log_info "  make pipeline-optimized     # 运行优化版pipeline"
    log_info "  make monitor               # 启动健康监控"
}

# 创建systemd服务
create_systemd_service() {
    CURRENT_DIR=$(pwd)
    SERVICE_FILE="/tmp/traceparts-pipeline.service"
    
    cat > $SERVICE_FILE << EOF
[Unit]
Description=TraceParts Optimized Pipeline
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="ENV=production"
Environment="MAX_WORKERS=32"
Environment="HEADLESS=true"
ExecStart=$CURRENT_DIR/venv/bin/python $CURRENT_DIR/src/pipelines/optimized_full_pipeline.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    log_info "systemd服务文件已创建: $SERVICE_FILE"
    log_info "使用以下命令安装服务："
    log_info "  sudo cp $SERVICE_FILE /etc/systemd/system/"
    log_info "  sudo systemctl daemon-reload"
    log_info "  sudo systemctl enable traceparts-pipeline"
    log_info "  sudo systemctl start traceparts-pipeline"
}

# 设置定时任务
setup_cron_jobs() {
    log_info "设置定时任务..."
    
    # 创建cron脚本
    CRON_SCRIPT="$PWD/scripts/cron_runner.sh"
    cat > $CRON_SCRIPT << 'EOF'
#!/bin/bash
cd $(dirname $0)/..
source venv/bin/activate
export ENV=production
export MAX_WORKERS=32
export HEADLESS=true
export DISABLE_IMAGES=true
export CACHE_ENABLED=true

# 运行pipeline
python src/pipelines/optimized_full_pipeline.py >> logs/cron.log 2>&1

# 运行健康检查
python scripts/health_monitor.py --once >> logs/health_cron.log 2>&1
EOF

    chmod +x $CRON_SCRIPT
    
    # 添加到crontab
    CRON_LINE="0 2 * * * $CRON_SCRIPT"
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    
    log_info "定时任务已设置（每天凌晨2点运行）"
}

# 回滚函数
rollback() {
    log_warn "执行回滚操作..."
    
    # 恢复之前的版本
    if [ -d "backup" ]; then
        log_info "恢复备份..."
        cp -r backup/* .
    fi
    
    log_info "回滚完成"
}

# 主函数
main() {
    case "$1" in
        deploy)
            deploy
            ;;
        rollback)
            rollback
            ;;
        *)
            echo "使用方法: $0 {deploy|rollback}"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@" 