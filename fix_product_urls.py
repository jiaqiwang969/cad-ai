#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复产品URL脚本
===============
将 results/cache/products 目录下所有 JSON 文件中的相对路径转换为绝对路径
从 "/en/product..." 转换为 "https://www.traceparts.cn/en/product..."
"""

import json
import os
from pathlib import Path
import time


def fix_product_urls():
    """修复产品URL路径"""
    
    # 目标目录
    products_cache_dir = Path("results/cache/products")
    
    if not products_cache_dir.exists():
        print(f"❌ 目录不存在: {products_cache_dir}")
        return
    
    # 统计信息
    total_files = 0
    processed_files = 0
    total_links_fixed = 0
    
    print("🔧 开始修复产品URL...")
    print(f"📁 目标目录: {products_cache_dir.absolute()}")
    print("="*60)
    
    # 遍历所有JSON文件
    for json_file in products_cache_dir.glob("*.json"):
        total_files += 1
        
        try:
            print(f"📄 处理文件: {json_file.name}")
            
            # 读取原始数据
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 记录修复前的数据
            original_data = data.copy() if isinstance(data, list) else [data]
            links_fixed_in_file = 0
            
            # 如果数据是列表（产品链接列表）
            if isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, str) and item.startswith("/en/product"):
                        # 转换为绝对URL
                        data[i] = f"https://www.traceparts.cn{item}"
                        links_fixed_in_file += 1
                        print(f"   ✅ 修复: {item[:50]}... -> https://www.traceparts.cn{item[:40]}...")
            
            # 如果数据是字典，递归处理所有字符串值
            elif isinstance(data, dict):
                links_fixed_in_file += fix_urls_in_dict(data)
            
            # 只有当有修复时才写入文件
            if links_fixed_in_file > 0:
                # 备份原文件
                backup_file = json_file.with_suffix('.json.backup')
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(original_data, f, ensure_ascii=False, indent=2)
                
                # 写入修复后的数据
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"   💾 已修复 {links_fixed_in_file} 个链接")
                print(f"   📦 备份保存到: {backup_file.name}")
                processed_files += 1
                total_links_fixed += links_fixed_in_file
            else:
                print(f"   ✨ 无需修复")
            
        except Exception as e:
            print(f"   ❌ 处理失败: {e}")
        
        print()
    
    # 输出汇总
    print("="*60)
    print("📊 修复完成汇总:")
    print(f"   📁 扫描文件: {total_files} 个")
    print(f"   🔧 修复文件: {processed_files} 个")
    print(f"   🔗 修复链接: {total_links_fixed} 个")
    
    if processed_files > 0:
        print(f"\n💡 提示: 原文件已备份为 .backup 后缀")
        print(f"📍 如需恢复，可运行: mv file.json.backup file.json")


def fix_urls_in_dict(data_dict):
    """递归修复字典中的URL"""
    links_fixed = 0
    
    for key, value in data_dict.items():
        if isinstance(value, str) and value.startswith("/en/product"):
            # 修复字符串值
            data_dict[key] = f"https://www.traceparts.cn{value}"
            links_fixed += 1
            print(f"   ✅ 修复字段 '{key}': {value[:40]}... -> https://www.traceparts.cn{value[:30]}...")
            
        elif isinstance(value, list):
            # 处理列表中的每个元素
            for i, item in enumerate(value):
                if isinstance(item, str) and item.startswith("/en/product"):
                    value[i] = f"https://www.traceparts.cn{item}"
                    links_fixed += 1
                    print(f"   ✅ 修复列表项: {item[:40]}... -> https://www.traceparts.cn{item[:30]}...")
                elif isinstance(item, dict):
                    links_fixed += fix_urls_in_dict(item)
                    
        elif isinstance(value, dict):
            # 递归处理嵌套字典
            links_fixed += fix_urls_in_dict(value)
    
    return links_fixed


def show_sample_before_after():
    """显示修复前后的示例"""
    print("🔍 修复示例:")
    print("   修复前: /en/product/rud-rud-tecdos-cobra-fork-head-hook?CatalogPath=...")
    print("   修复后: https://www.traceparts.cn/en/product/rud-rud-tecdos-cobra-fork-head-hook?CatalogPath=...")
    print()


if __name__ == "__main__":
    print("🚀 产品URL修复工具")
    print("=" * 60)
    
    show_sample_before_after()
    
    # 确认是否继续
    response = input("是否开始修复？(y/N): ").strip().lower()
    if response in ['y', 'yes']:
        fix_product_urls()
    else:
        print("❌ 操作已取消") 