# 缓存扩展指南

## 概述

TraceParts爬虫系统现在支持**两阶段缓存**：

1. **基础缓存**：仅包含分类树结构（第一阶段）
2. **扩展缓存**：包含分类树 + 产品链接（第一阶段 + 第二阶段）

使用扩展缓存后，系统可以跳过产品链接爬取步骤，直接进入产品规格爬取阶段，大大提高效率。

## 缓存文件结构

扩展后的 `results/cache/classification_tree.json` 文件结构：

```json
{
  "metadata": {
    "generated": "2024-01-20T10:00:00",
    "extended_at": "2024-01-20T12:00:00",
    "version": "2.0-with-products",
    "total_leaves": 1234,
    "total_products": 56789
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
      "products": [
        "https://www.traceparts.cn/en/product/...",
        ...
      ],
      "product_count": 123
    },
    ...
  ]
}
```

## 使用流程

### 1. 初次运行（生成基础缓存）

```bash
# 运行优化流水线，生成基础分类树缓存
python run_optimized_pipeline.py
```

这将在 `results/cache/classification_tree.json` 创建基础缓存（仅包含分类树）。

### 2. 扩展缓存（添加产品链接）

```bash
# 扩展缓存，为每个叶节点添加产品链接
python extend_cache.py --workers 16
```

参数说明：
- `--workers`: 并发线程数（默认16）

这个过程会：
- 读取现有的分类树缓存
- 为每个叶节点爬取产品链接（支持断点续传）
- 将产品链接保存到单独的缓存文件（`results/cache/products/`）
- 最终合并到主缓存文件中

### 3. 使用扩展缓存

再次运行流水线时，系统会自动识别扩展缓存：

```bash
python run_optimized_pipeline.py
```

控制台会显示：
```
📂 使用缓存的分类树
   缓存文件: /path/to/results/cache/classification_tree.json
   缓存年龄: 2.5 小时
   ✨ 缓存版本: 2.0-with-products (包含产品链接)
   产品总数: 56789 个
   
[步骤 2/3] 从叶节点提取产品链接
📦 使用缓存的产品链接数据
✅ 从缓存加载完成:
   • 成功叶节点: 1200/1234
   • 空叶节点: 34
   • 总产品数: 56789 个
```

### 4. 强制重新爬取

如果需要强制重新爬取（忽略缓存）：

```bash
python run_optimized_pipeline.py --no-cache
```

## 缓存管理

### 查看缓存状态

```bash
python scripts/demo_extended_cache.py
```

这会显示当前缓存的详细信息。

### 单独缓存产品链接

产品链接也会单独缓存在 `results/cache/products/` 目录下：
- 每个叶节点一个文件：`{TP_CODE}.json`
- 缓存有效期：24小时
- 支持断点续传

### 清理缓存

```bash
# 清理所有缓存
rm -rf results/cache/

# 仅清理产品缓存（保留分类树）
rm -rf results/cache/products/

# 恢复基础缓存（移除产品链接）
mv results/cache/classification_tree.json.bak results/cache/classification_tree.json
```

## 性能优势

使用扩展缓存的优势：

1. **跳过第二阶段**：不需要重新爬取产品链接（通常是最耗时的步骤）
2. **减少网络请求**：减少数万次HTTP请求
3. **提高稳定性**：避免因网络问题导致的中断
4. **快速迭代**：可以专注于优化第三阶段（产品规格爬取）

## 注意事项

1. 缓存文件可能较大（几十MB），请确保有足够的磁盘空间
2. 缓存有效期为24小时，过期后会自动重新爬取
3. 扩展缓存时会自动备份原文件为 `.json.bak`
4. 如果分类树结构发生变化，建议使用 `--no-cache` 重新爬取

## 故障排除

**问题1**：扩展缓存失败
- 检查是否有基础缓存文件
- 确保网络连接正常
- 查看日志中的错误信息

**问题2**：缓存文件损坏
- 删除缓存文件并重新运行
- 从备份文件恢复：`mv classification_tree.json.bak classification_tree.json`

**问题3**：产品数量不匹配
- 可能是网站更新了内容
- 使用 `--no-cache` 强制重新爬取 