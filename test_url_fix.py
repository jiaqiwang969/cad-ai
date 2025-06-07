#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试URL修复效果
"""
import json
from pathlib import Path

def test_url_format():
    """测试缓存文件中的URL格式"""
    cache_dir = Path("results/cache/products")
    
    if not cache_dir.exists():
        print("❌ 缓存目录不存在，请先运行 make pipeline")
        return
    
    # 检查现有缓存文件
    json_files = list(cache_dir.glob("*.json"))
    
    if not json_files:
        print("❌ 没有找到缓存文件")
        return
    
    print(f"📁 找到 {len(json_files)} 个缓存文件")
    
    relative_url_files = []
    absolute_url_files = []
    
    for json_file in json_files[:10]:  # 只检查前10个文件
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            if not products:
                continue
                
            # 检查第一个URL的格式
            first_url = products[0]
            
            if first_url.startswith("http"):
                absolute_url_files.append(json_file.name)
                print(f"✅ {json_file.name}: 绝对URL - {first_url[:80]}...")
            else:
                relative_url_files.append(json_file.name)
                print(f"❌ {json_file.name}: 相对URL - {first_url[:80]}...")
                
        except Exception as e:
            print(f"⚠️ 读取 {json_file.name} 失败: {e}")
    
    print(f"\n📊 总结:")
    print(f"   绝对URL文件: {len(absolute_url_files)}")
    print(f"   相对URL文件: {len(relative_url_files)}")
    
    if relative_url_files:
        print(f"\n需要修复的文件示例:")
        for file_name in relative_url_files[:3]:
            print(f"   - {file_name}")

if __name__ == "__main__":
    test_url_format()