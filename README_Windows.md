# TraceParts Pipeline V2 - Windows 使用指南

## 📋 系统要求

- Windows 10/11
- Python 3.8+
- Node.js 16+
- Git

## 🚀 快速开始

### 1. 首次安装
```cmd
# 双击运行或在命令行执行
setup_windows.bat
```

### 2. 运行后端流水线
```cmd
# 爬取数据
run_pipeline.bat
```

### 3. 复制数据到前端
```cmd
# 将后端数据复制到前端
copy_data.bat
```

### 4. 启动前端界面
```cmd
# 启动Web界面
start_frontend.bat
```

## 📁 批处理文件说明

| 文件名 | 功能 | 使用场景 |
|--------|------|----------|
| `setup_windows.bat` | 环境安装和配置 | 首次使用或重新安装 |
| `run_pipeline.bat` | 运行后端爬虫流水线 | 获取最新数据 |
| `copy_data.bat` | 复制数据到前端 | 数据更新后同步 |
| `start_frontend.bat` | 启动前端Web界面 | 查看和管理数据 |
| `check_env.bat` | 检查环境状态 | 故障排除 |
| `clean.bat` | 清理临时文件 | 清理缓存和日志 |

## 🔧 常见问题

### Python 相关
- **问题**: `python 不是内部或外部命令`
- **解决**: 安装Python并确保添加到PATH

### Node.js 相关
- **问题**: `npm install` 失败
- **解决**: 清除npm缓存 `npm cache clean --force`

### 网络问题
- **问题**: Playwright 安装失败
- **解决**: 使用VPN或手动下载浏览器内核

### 权限问题
- **问题**: 文件创建失败
- **解决**: 以管理员身份运行批处理文件

## 📊 使用流程

1. **环境准备**: `setup_windows.bat`
2. **数据爬取**: `run_pipeline.bat`
3. **数据同步**: `copy_data.bat`
4. **界面启动**: `start_frontend.bat`
5. **浏览数据**: 在浏览器中访问 http://localhost:3000

## 💡 提示

- 所有脚本支持中文显示
- 可以双击直接运行，无需命令行知识
- 首次运行可能需要较长时间下载依赖
- 建议定期运行 `clean.bat` 清理临时文件

## 🆘 获取帮助

如果遇到问题，请：
1. 运行 `check_env.bat` 检查环境
2. 查看 `results/logs/` 目录下的日志文件
3. 检查控制台输出的错误信息
