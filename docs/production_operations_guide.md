# TraceParts爬虫生产环境运维指南

## 目录

1. [系统架构概述](#系统架构概述)
2. [部署流程](#部署流程)
3. [日常运维](#日常运维)
4. [监控与告警](#监控与告警)
5. [故障处理](#故障处理)
6. [性能优化](#性能优化)
7. [备份与恢复](#备份与恢复)
8. [安全注意事项](#安全注意事项)

## 系统架构概述

### 核心组件

1. **优化版Pipeline** (`src/pipelines/optimized_full_pipeline.py`)
   - 主要爬取流程
   - 并发控制
   - 缓存管理

2. **线程安全日志系统** (`src/utils/thread_safe_logger.py`)
   - 并发日志处理
   - 进度追踪
   - 批量输出

3. **健康监控系统** (`scripts/health_monitor.py`)
   - 系统资源监控
   - Pipeline状态检查
   - 告警发送

### 系统要求

- Python 3.8+
- 内存: 最少8GB，推荐16GB+
- CPU: 4核+，推荐8核+
- 磁盘: 100GB+ (用于缓存和结果存储)
- 网络: 稳定的互联网连接

## 部署流程

### 1. 初始部署

```bash
# 克隆代码
git clone <repository_url>
cd traceparts-crawler

# 运行部署脚本
chmod +x scripts/deploy_production.sh
./scripts/deploy_production.sh deploy
```

### 2. 环境变量配置

创建 `.env` 文件：

```bash
# 基础配置
ENV=production
MAX_WORKERS=32
BATCH_SIZE=50

# 性能配置
HEADLESS=true
DISABLE_IMAGES=true
CACHE_ENABLED=true

# 监控配置
MONITOR_ENABLED=true
HEALTH_CHECK_INTERVAL=300
ALERT_WEBHOOK=https://your-webhook-url

# 数据库配置（可选）
DB_ENABLED=false
DB_HOST=localhost
DB_PORT=5432
DB_NAME=traceparts
DB_USER=traceparts
DB_PASSWORD=your_password
```

### 3. 启动服务

```bash
# 手动运行
make pipeline-optimized

# 或使用systemd（Linux）
sudo systemctl start traceparts-pipeline
sudo systemctl enable traceparts-pipeline

# 启动健康监控
make monitor
```

## 日常运维

### 常用命令

```bash
# 运行爬虫
make pipeline-optimized          # 32并发
make pipeline-optimized-max      # 64并发
make pipeline-optimized-nocache  # 不使用缓存

# 监控相关
make monitor                     # 启动持续监控
python scripts/health_monitor.py --once  # 单次健康检查

# 日志查看
tail -f logs/opt-pipeline.log    # 查看爬虫日志
tail -f logs/health_monitor.log  # 查看监控日志

# 清理缓存
make clean-cache
```

### 定时任务管理

```bash
# 查看定时任务
crontab -l

# 编辑定时任务
crontab -e

# 默认定时任务（每天凌晨2点运行）
0 2 * * * /path/to/scripts/cron_runner.sh
```

### 日志管理

日志文件位置：
- 爬虫日志: `logs/opt-pipeline.log`
- 监控日志: `logs/health_monitor.log`
- 定时任务日志: `logs/cron.log`

日志轮转配置（logrotate）：

```bash
# /etc/logrotate.d/traceparts
/path/to/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 user group
}
```

## 监控与告警

### 监控指标

1. **系统资源**
   - CPU使用率 (告警阈值: >90%)
   - 内存使用率 (告警阈值: >90%)
   - 磁盘使用率 (告警阈值: >90%)
   - 活跃线程数

2. **Pipeline指标**
   - 运行状态
   - 成功率 (告警阈值: <80%)
   - 错误数量 (告警阈值: >10/小时)
   - 最后运行时间

### 告警级别

- **Critical**: 立即发送告警，需要紧急处理
- **Warning**: 连续3次检查后发送告警
- **Info**: 仅记录日志

### 健康报告

健康报告保存在: `logs/health_report.json`

查看最新健康状态：
```bash
cat logs/health_report.json | jq .
```

## 故障处理

### 常见问题及解决方案

#### 1. 内存溢出

**症状**: 程序崩溃，日志显示内存错误

**解决方案**:
```bash
# 减少并发数
export MAX_WORKERS=16

# 增加系统swap
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 2. 网络超时

**症状**: 大量超时错误

**解决方案**:
```bash
# 增加超时时间
export REQUEST_TIMEOUT=60

# 减少并发数
export MAX_WORKERS=8
```

#### 3. 缓存损坏

**症状**: 读取缓存时出错

**解决方案**:
```bash
# 清理缓存
rm -rf results/cache/*

# 禁用缓存运行
make pipeline-optimized-nocache
```

#### 4. 浏览器驱动问题

**症状**: Chrome启动失败

**解决方案**:
```bash
# 更新Chrome和ChromeDriver
sudo apt update
sudo apt install google-chrome-stable

# 下载匹配的ChromeDriver
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
```

### 紧急恢复流程

1. **停止服务**
   ```bash
   sudo systemctl stop traceparts-pipeline
   pkill -f "optimized_full_pipeline"
   ```

2. **检查系统状态**
   ```bash
   # 检查进程
   ps aux | grep python
   
   # 检查资源
   htop
   df -h
   ```

3. **恢复服务**
   ```bash
   # 清理临时文件
   rm -f /tmp/.com.google.Chrome.*
   
   # 重启服务
   sudo systemctl start traceparts-pipeline
   ```

## 性能优化

### 并发优化

根据系统资源调整并发数：

| CPU核心数 | 内存 | 推荐并发数 |
|----------|------|-----------|
| 4        | 8GB  | 16        |
| 8        | 16GB | 32        |
| 16       | 32GB | 64        |

### 缓存策略

1. **分类树缓存**: 7天
2. **产品规格缓存**: 24小时
3. **清理策略**: 每周清理超过30天的缓存

### 网络优化

```bash
# 增加系统文件描述符限制
ulimit -n 65536

# 优化TCP参数
echo "net.ipv4.tcp_keepalive_time = 120" >> /etc/sysctl.conf
echo "net.ipv4.tcp_keepalive_intvl = 30" >> /etc/sysctl.conf
echo "net.ipv4.tcp_keepalive_probes = 3" >> /etc/sysctl.conf
sysctl -p
```

## 备份与恢复

### 自动备份

创建备份脚本 `scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backup/traceparts"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份结果数据
tar -czf $BACKUP_DIR/results_$DATE.tar.gz results/

# 备份配置
tar -czf $BACKUP_DIR/config_$DATE.tar.gz config/ .env

# 保留最近7天的备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

添加到crontab:
```bash
0 3 * * * /path/to/scripts/backup.sh
```

### 数据恢复

```bash
# 恢复结果数据
tar -xzf /backup/traceparts/results_20240101_030000.tar.gz

# 恢复配置
tar -xzf /backup/traceparts/config_20240101_030000.tar.gz
```

## 安全注意事项

### 1. 访问控制

- 限制对生产服务器的SSH访问
- 使用密钥认证而非密码
- 配置防火墙规则

### 2. 敏感信息管理

- 不要在代码中硬编码密码
- 使用环境变量存储敏感信息
- 定期轮换密钥和令牌

### 3. 日志安全

- 避免在日志中记录敏感信息
- 定期清理旧日志
- 设置适当的文件权限

### 4. 更新策略

- 定期更新系统和依赖包
- 在测试环境验证更新
- 保持更新记录

## 附录

### A. 性能基准

| 指标 | 数值 |
|-----|------|
| 平均爬取速度 | 1000-1500 产品/分钟 |
| 内存使用 | 4-6 GB (32并发) |
| CPU使用 | 60-80% (8核) |
| 网络带宽 | 10-20 Mbps |

### B. 故障诊断检查清单

- [ ] 检查系统资源（CPU、内存、磁盘）
- [ ] 查看最近的错误日志
- [ ] 验证网络连接
- [ ] 检查Chrome/ChromeDriver版本
- [ ] 确认环境变量配置
- [ ] 检查文件权限
- [ ] 验证Python依赖完整性

### C. 联系信息

- 技术支持: support@example.com
- 紧急联系: +86-xxx-xxxx-xxxx
- 文档更新: https://docs.example.com 