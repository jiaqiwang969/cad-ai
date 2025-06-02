# TraceParts 爬虫性能优化与版本化缓存系统

## 概述

TraceParts 爬虫已经完全集成了所有性能优化，通过减少等待时间、禁用不必要的资源加载和增加并发来提供最佳的爬取速度。同时采用了先进的版本化缓存管理系统，确保数据的完整性和可追溯性。

## 版本化缓存系统

### 缓存文件命名规范

系统采用三层缓存结构，每个级别使用独立的版本化文件：

```
results/cache/
├── cache_index.json                    # 索引文件，记录最新版本
├── classification_tree_v20250602_171234.json    # 分类树缓存
├── products_links_v20250602_171234.json         # 产品链接缓存  
├── specifications_v20250602_171234.json         # 产品规格缓存
└── [older versions...]                 # 自动保留最近5个版本
```

### 版本格式说明

- **时间戳格式**: `vYYYYMMDD_HHMMSS` (如: `v20250602_171234`)
- **自动清理**: 每个级别自动保留最近5个版本
- **索引管理**: `cache_index.json` 记录最新文件位置和版本历史

### 缓存级别

1. **CLASSIFICATION** - 分类树结构
2. **PRODUCTS** - 产品链接信息  
3. **SPECIFICATIONS** - 产品详细规格

## 主要优化

### 1. **资源加载优化**
- 禁用图片、字体、样式表加载
- 通过 CDP 协议屏蔽广告和分析脚本
- 减少页面渲染时间

### 2. **智能等待策略**
- 动态等待替代固定 sleep
- 域名级弹窗缓存（同域名只处理一次弹窗）
- 条件等待元素出现而非固定时间

### 3. **并发优化**
- 默认最多 12 个并发线程
- 线程本地 driver 池，减少创建/销毁开销
- 智能任务分配，避免单个 URL 占用整个线程

### 4. **输出精简**
- 减少调试信息输出
- 关闭不必要的截图保存
- 简化进度显示

## 使用方法

### 基础命令

```bash
# 运行缓存管理器（已内置所有优化）
python run_cache_manager.py

# 带参数运行
python run_cache_manager.py --workers 12 --level specifications

# 强制刷新
python run_cache_manager.py --force
```

### 缓存管理命令

```bash
# 查看缓存状态
python run_cache_manager.py --status

# 查看版本历史  
python run_cache_manager.py --history

# 清理旧版本文件（保留最近3个版本）
python run_cache_manager.py --cleanup

# 查看最新的错误日志
python run_cache_manager.py --errors

# 指定缓存目录
python run_cache_manager.py --status --cache-dir /path/to/cache
```

### 异常记录系统

系统会自动记录爬取过程中的所有异常情况，并保存为版本化的JSON文件：

```
results/cache/error_logs/
├── error_log_v20250602_171234.json    # 错误日志文件
└── error_log_v20250602_173045.json    # 另一个版本的错误日志
```

#### 记录的错误类型

**产品链接错误：**
- `zero_products` - 页面正常但未找到产品
- `zero_products_no_exception` - 爬取完成但返回空列表
- `product_extraction_failed` - 产品链接爬取过程失败
- `product_extraction_exception` - 爬取过程中发生异常

**产品规格错误：**
- `zero_specifications` - 页面正常但未提取到规格
- `low_specification_count` - 规格数量较少（可能有问题）
- `specification_extraction_failed` - 规格爬取完全失败

#### 错误日志格式

```json
{
  "generated": "2025-06-02T17:34:49.123456",
  "version": "v20250602_173449",
  "summary": {
    "total_product_errors": 3,
    "total_specification_errors": 8,
    "zero_specs_count": 5,
    "exception_count": 3
  },
  "details": {
    "products": [...],
    "specifications": [...]
  }
}
```

### 状态信息示例

```
============================================================
📊 缓存状态信息
============================================================
📁 缓存目录: results/cache
📈 当前级别: SPECIFICATIONS

📄 最新缓存文件:
   • CLASSIFICATION: classification_tree_v20250602_171234.json (0.1 MB)
   • PRODUCTS: products_links_v20250602_171234.json (0.2 MB)
   • SPECIFICATIONS: specifications_v20250602_171234.json (0.3 MB)

🏷️ 元数据信息:
   • 版本: v20250602_171234
   • 生成时间: 2025-06-02T17:12:34.567890
   • 叶节点数: 2
   • 产品总数: 26
   • 规格总数: 26
============================================================
```

### 代码中使用

```python
from src.pipelines.cache_manager import CacheManager, CacheLevel

# 创建管理器
manager = CacheManager()

# 查看当前状态
current_level, data = manager.get_cache_level()

# 获取详细状态
status = manager.get_cache_status()

# 获取版本历史
history = manager.get_version_history(CacheLevel.SPECIFICATIONS)

# 运行到指定级别
manager.run_progressive_cache(CacheLevel.SPECIFICATIONS)
```

## 版本管理最佳实践

### 1. **定期检查状态**
```bash
# 每天运行前检查缓存状态
python run_cache_manager.py --status
```

### 2. **版本回退**
如需使用旧版本，可手动修改 `cache_index.json` 中的 `latest_files` 指向：
```json
{
  "latest_files": {
    "specifications": "specifications_v20250601_120000.json"
  }
}
```

### 3. **磁盘空间管理**
```bash
# 定期清理旧版本（建议每周运行）
python run_cache_manager.py --cleanup
```

### 4. **备份重要版本**
对于重要的完整数据集，建议手动备份：
```bash
cp results/cache/specifications_v20250602_171234.json backups/
```

## 性能提升效果

### 性能对比

| 测试场景 | 优化前 | 优化后 | 提升 |
|----------|--------|--------|------|
| 26个产品规格爬取 | 17分钟 | 4-5分钟 | **3-4x** |
| 单页面处理 | 31秒 | 12秒 | **61%减少** |
| 并发线程数 | 8个 | 12个 | **50%提升** |

### 主要优化技术

1. **资源屏蔽**: 减少50%页面加载时间
2. **智能等待**: 节省60%等待时间  
3. **弹窗缓存**: 节省8-10秒/域名
4. **线程优化**: 减少创建销毁开销
5. **批量处理**: 最大化并行效率

## 故障排除

### 常见问题

**Q: 缓存文件过多占用磁盘空间？**
A: 使用 `--cleanup` 参数定期清理，或调整保留版本数量

**Q: 如何恢复到之前的版本？**  
A: 查看 `--history` 找到目标版本，手动修改索引文件指向

**Q: 索引文件损坏怎么办？**
A: 删除 `cache_index.json`，系统会自动重建并检测现有缓存文件

**Q: 如何完全重置缓存？**
A: 删除整个 `results/cache` 目录，重新运行爬虫

## 注意事项

1. **网站兼容性**
   - 某些网站可能依赖 CSS/图片进行布局
   - 如遇到问题，请联系开发者

2. **反爬虫策略**
   - 优化后请求频率更高，可能触发反爬
   - 建议监控失败率，必要时降低并发

3. **内存使用**
   - 更多并发线程会增加内存使用
   - 建议系统至少有 8GB 内存

## 最佳实践

1. **批量处理**：URL 数量 > 10 时效果明显
2. **监控日志**：关注失败率和错误信息
3. **定期维护**：清理缓存文件，避免磁盘占用过多
4. **合理并发**：根据系统性能调整 max_workers 参数

## 技术细节

### 资源屏蔽列表
- 图片：*.png, *.jpg, *.jpeg, *.gif, *.svg, *.webp
- 字体：*.woff*, *.ttf, *.otf, *.eot
- 分析脚本：*googletagmanager*, *google-analytics*, *doubleclick*
- 社交媒体：*facebook*, *twitter*, *linkedin*

### 默认配置
- 页面加载等待：1 秒
- 滚动等待：0.3 秒
- 弹窗超时：3 秒
- 操作等待：0.5 秒
- 最大线程数：12
- 隐式等待：5 秒
- 页面超时：30 秒 