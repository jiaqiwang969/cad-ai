# 渐进式缓存系统指南

## 概述

TraceParts爬虫系统V2引入了**渐进式缓存管理器**，支持三个级别的缓存：

1. **Level 1 - CLASSIFICATION**：仅分类树结构
2. **Level 2 - PRODUCTS**：分类树 + 产品链接
3. **Level 3 - SPECIFICATIONS**：分类树 + 产品链接 + 产品规格（完整数据）

系统会自动识别当前缓存级别，并根据需要逐步扩展到目标级别。

## 系统架构

```
缓存管理器 (CacheManager)
    ├── 分类树爬取器 (Classification Crawler)
    ├── 产品链接爬取器 (Products Crawler)
    └── 产品规格爬取器 (Specifications Crawler)

缓存目录结构：
results/cache/
    ├── classification_tree_full.json    # 主缓存文件
    ├── classification_tree_full.json.bak # 备份文件
    ├── products/                        # 产品链接缓存
    │   └── {TP_CODE}.json              # 每个叶节点的产品链接
    └── specifications/                  # 产品规格缓存
        └── {LEAF_CODE}_{HASH}.json     # 每个产品的规格
```

## 数据结构

### 主缓存文件结构

```json
{
  "metadata": {
    "generated": "2024-01-20T10:00:00",
    "cache_level": 3,
    "cache_level_name": "SPECIFICATIONS",
    "version": "3.0-specifications",
    "total_leaves": 1234,
    "total_products": 56789,
    "total_specifications": 234567
  },
  "root": {
    "name": "TraceParts Classification",
    "code": "TRACEPARTS_ROOT",
    "children": [...],
    "is_leaf": false
  },
  "leaves": [
    {
      "name": "Bearings",
      "code": "TP01002002006",
      "url": "https://...",
      "level": 7,
      "is_leaf": true,
      "product_count": 123,
      "products": [
        {
          "product_url": "https://...",
          "spec_count": 15,
          "specifications": [
            {
              "reference": "TXCE-H1-6-1515-L100",
              "description": "Linear actuator",
              "manufacturer": "Thomson",
              ...
            }
          ]
        }
      ]
    }
  ]
}
```

## 使用方法

### 1. 使用缓存管理器

```bash
# 构建到分类树级别
python run_cache_manager.py --level classification

# 构建到产品链接级别
python run_cache_manager.py --level products

# 构建到完整级别（包含规格）
python run_cache_manager.py --level specifications

# 强制刷新所有缓存
python run_cache_manager.py --force

# 指定并发数
python run_cache_manager.py --workers 32
```

### 2. 使用优化流水线V2

```bash
# 默认运行（构建完整缓存）
python run_pipeline_v2.py

# 只构建到产品级别
python run_pipeline_v2.py --level products

# 强制刷新缓存
python run_pipeline_v2.py --no-cache

# 导出结果到文件
python run_pipeline_v2.py --output results/export.json

# 自定义配置
python run_pipeline_v2.py --workers 16 --cache-dir custom/cache
```

### 3. 查看缓存状态

```bash
# 运行演示脚本
python scripts/demo_progressive_cache.py
```

这会显示：
- 当前缓存级别
- 数据统计（叶节点数、产品数、规格数）
- 缓存文件结构
- 示例数据

## 缓存策略

### 缓存有效期

- **分类树**：7天（网站分类结构很少变化）
- **产品链接**：3天（产品列表可能有更新）
- **产品规格**：1天（产品详情可能频繁更新）

### 缓存更新机制

1. **自动更新**：缓存过期时自动重新爬取
2. **增量更新**：只更新需要的部分
   - 如果只需要产品链接，不会重新爬取分类树
   - 如果需要规格，会检查产品链接是否需要更新

3. **断点续传**：每个爬取单元独立缓存
   - 叶节点产品链接独立缓存
   - 产品规格独立缓存
   - 中断后可从断点继续

## 性能优化

### 1. 并行处理

- 分类树：单线程递归遍历
- 产品链接：多线程并行爬取各叶节点
- 产品规格：多线程并行爬取各产品

### 2. 内存优化

- 流式处理大数据
- 独立缓存避免一次性加载所有数据
- 使用生成器处理大列表

### 3. 网络优化

- 自动重试机制
- 连接池复用
- 智能限速避免被封

## 常见场景

### 场景1：日常更新产品规格

```bash
# 只更新规格，保留现有分类树和产品链接
python run_pipeline_v2.py --level specifications
```

### 场景2：完全重建数据

```bash
# 强制刷新所有缓存
python run_pipeline_v2.py --no-cache
```

### 场景3：快速获取分类结构

```bash
# 只爬取分类树
python run_cache_manager.py --level classification
```

### 场景4：导出特定数据

```bash
# 导出到指定文件
python run_pipeline_v2.py --output exports/$(date +%Y%m%d).json
```

## 故障排除

### 问题1：缓存文件损坏

```bash
# 从备份恢复
mv results/cache/classification_tree_full.json.bak results/cache/classification_tree_full.json

# 或清理后重建
rm -rf results/cache/
python run_pipeline_v2.py
```

### 问题2：部分数据缺失

```bash
# 检查缓存状态
python scripts/demo_progressive_cache.py

# 强制更新到目标级别
python run_cache_manager.py --level specifications --force
```

### 问题3：内存不足

```bash
# 减少并发数
python run_pipeline_v2.py --workers 8

# 分阶段构建
python run_cache_manager.py --level products
python run_cache_manager.py --level specifications
```

## 高级用法

### 自定义缓存管理

```python
from src.pipelines.cache_manager import CacheManager, CacheLevel

# 创建管理器
manager = CacheManager(cache_dir='custom/cache', max_workers=16)

# 获取当前缓存
level, data = manager.get_cache_level()

# 扩展到指定级别
if level.value < CacheLevel.PRODUCTS.value:
    data = manager.extend_to_products(data)
    manager.save_cache(data, CacheLevel.PRODUCTS)
```

### 数据分析

```python
# 加载缓存数据
import json
with open('results/cache/classification_tree_full.json', 'r') as f:
    data = json.load(f)

# 分析数据
leaves = data['leaves']
total_products = sum(leaf['product_count'] for leaf in leaves)
avg_products_per_leaf = total_products / len(leaves)

print(f"平均每个叶节点有 {avg_products_per_leaf:.1f} 个产品")
```

## 最佳实践

1. **定期更新**：设置定时任务定期更新缓存
2. **监控缓存**：监控缓存大小和更新频率
3. **备份重要数据**：定期备份完整缓存文件
4. **优化并发**：根据服务器性能调整并发数
5. **错误处理**：记录失败的爬取任务，后续重试

## 总结

渐进式缓存系统提供了灵活、高效的数据管理方案：

- ✅ **灵活性**：可以选择构建到任意级别
- ✅ **效率**：避免重复爬取，节省时间
- ✅ **可靠性**：支持断点续传和错误恢复
- ✅ **可扩展**：易于添加新的缓存级别
- ✅ **透明性**：自动管理缓存生命周期

通过合理使用缓存系统，可以大大提高爬虫效率和稳定性。 