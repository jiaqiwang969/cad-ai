#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修复产品缓存文件中的URL格式
=========================
将相对URL转换为绝对URL，确保所有URL都包含完整的https://www.traceparts.cn前缀
"""

import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
import argparse


def backup_file(file_path: Path, backup_dir: Path) -> Path:
    """备份文件到指定目录"""
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / file_path.name
    shutil.copy2(file_path, backup_path)
    return backup_path


def fix_urls_in_list(urls: List[str], base_url: str = "https://www.traceparts.cn") -> List[str]:
    """修复URL列表中的相对URL"""
    fixed_urls = []
    for url in urls:
        if isinstance(url, str):
            if url.startswith("http"):
                # 已经是绝对URL
                fixed_urls.append(url)
            elif url.startswith("/"):
                # 相对URL，添加base_url
                fixed_urls.append(f"{base_url}{url}")
            else:
                # 其他格式，保持原样并记录警告
                print(f"  ⚠️ 未知URL格式: {url}")
                fixed_urls.append(url)
        else:
            # 非字符串类型，保持原样
            fixed_urls.append(url)
    return fixed_urls


def process_json_file(file_path: Path, base_url: str = "https://www.traceparts.cn", backup_dir: Path = None) -> Dict[str, Any]:
    """处理单个JSON文件"""
    result = {
        'file': str(file_path),
        'success': False,
        'original_count': 0,
        'fixed_count': 0,
        'error': None,
        'backup_path': None
    }
    
    try:
        # 读取原始文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            result['error'] = f"文件内容不是列表格式: {type(data)}"
            return result
        
        result['original_count'] = len(data)
        
        # 检查是否需要修复
        needs_fix = False
        for item in data:
            if isinstance(item, str) and item.startswith("/"):
                needs_fix = True
                break
        
        if not needs_fix:
            result['success'] = True
            result['fixed_count'] = 0
            return result
        
        # 备份原文件
        if backup_dir:
            backup_path = backup_file(file_path, backup_dir)
            result['backup_path'] = str(backup_path)
        
        # 修复URL
        fixed_data = fix_urls_in_list(data, base_url)
        result['fixed_count'] = len([url for url in fixed_data if isinstance(url, str) and url.startswith("http")])
        
        # 保存修复后的文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(fixed_data, f, ensure_ascii=False, indent=2)
        
        result['success'] = True
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def scan_product_cache_dir(cache_dir: Path) -> List[Path]:
    """扫描产品缓存目录，找到所有JSON文件"""
    json_files = []
    
    if not cache_dir.exists():
        print(f"❌ 缓存目录不存在: {cache_dir}")
        return json_files
    
    # 查找所有JSON文件
    for json_file in cache_dir.glob("*.json"):
        if json_file.is_file():
            json_files.append(json_file)
    
    return sorted(json_files)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='批量修复产品缓存文件中的URL格式')
    
    parser.add_argument(
        '--cache-dir', 
        type=str, 
        default='results/cache/products',
        help='产品缓存目录 (默认: results/cache/products)'
    )
    
    parser.add_argument(
        '--base-url',
        type=str,
        default='https://www.traceparts.cn',
        help='基础URL (默认: https://www.traceparts.cn)'
    )
    
    parser.add_argument(
        '--backup',
        action='store_true',
        help='是否备份原文件'
    )
    
    parser.add_argument(
        '--backup-dir',
        type=str,
        default='results/backup/products',
        help='备份目录 (默认: results/backup/products)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅模拟运行，不实际修改文件'
    )
    
    args = parser.parse_args()
    
    cache_dir = Path(args.cache_dir)
    backup_dir = Path(args.backup_dir) if args.backup else None
    
    print("=" * 60)
    print("🔧 批量修复产品URL格式工具")
    print("=" * 60)
    print(f"📁 缓存目录: {cache_dir}")
    print(f"🌐 基础URL: {args.base_url}")
    print(f"💾 备份模式: {'启用' if args.backup else '禁用'}")
    if args.backup:
        print(f"📦 备份目录: {backup_dir}")
    print(f"🧪 模拟模式: {'启用' if args.dry_run else '禁用'}")
    print("=" * 60)
    
    # 扫描文件
    print("🔍 正在扫描JSON文件...")
    json_files = scan_product_cache_dir(cache_dir)
    
    if not json_files:
        print("❌ 没有找到JSON文件")
        return
    
    print(f"📊 找到 {len(json_files)} 个JSON文件")
    
    # 统计信息
    stats = {
        'total_files': len(json_files),
        'processed_files': 0,
        'successful_files': 0,
        'failed_files': 0,
        'fixed_files': 0,
        'total_urls': 0,
        'fixed_urls': 0
    }
    
    failed_files = []
    
    # 处理每个文件
    print("\n🚀 开始处理文件...")
    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i:3d}/{len(json_files)}] 处理: {json_file.name}")
        
        if args.dry_run:
            # 仅读取和分析，不修改
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    relative_count = sum(1 for url in data if isinstance(url, str) and url.startswith("/"))
                    print(f"  📊 总URL数: {len(data)}, 需修复: {relative_count}")
                else:
                    print(f"  ⚠️ 非列表格式: {type(data)}")
            except Exception as e:
                print(f"  ❌ 读取失败: {e}")
        else:
            # 实际处理文件
            result = process_json_file(json_file, args.base_url, backup_dir)
            
            stats['processed_files'] += 1
            stats['total_urls'] += result['original_count']
            
            if result['success']:
                stats['successful_files'] += 1
                if result['fixed_count'] > 0:
                    stats['fixed_files'] += 1
                    stats['fixed_urls'] += result['fixed_count']
                    print(f"  ✅ 修复完成: {result['original_count']} → {result['fixed_count']} 个URL")
                    if result['backup_path']:
                        print(f"  💾 备份至: {Path(result['backup_path']).name}")
                else:
                    print(f"  ✅ 无需修复: {result['original_count']} 个URL已是绝对URL")
            else:
                stats['failed_files'] += 1
                failed_files.append({'file': json_file.name, 'error': result['error']})
                print(f"  ❌ 处理失败: {result['error']}")
    
    # 打印总结
    print("\n" + "=" * 60)
    print("📊 处理完成 - 总结报告")
    print("=" * 60)
    
    if args.dry_run:
        print("🧪 这是模拟运行，没有实际修改文件")
    
    print(f"📁 总文件数: {stats['total_files']}")
    print(f"✅ 处理成功: {stats['successful_files']}")
    print(f"❌ 处理失败: {stats['failed_files']}")
    
    if not args.dry_run:
        print(f"🔧 需要修复的文件: {stats['fixed_files']}")
        print(f"🌐 总URL数: {stats['total_urls']}")
        print(f"🔗 修复URL数: {stats['fixed_urls']}")
        
        if stats['fixed_urls'] > 0:
            print(f"📈 修复比例: {stats['fixed_urls']/stats['total_urls']*100:.1f}%")
    
    # 显示失败的文件
    if failed_files:
        print(f"\n❌ 处理失败的文件:")
        for failed in failed_files:
            print(f"  • {failed['file']}: {failed['error']}")
    
    print("=" * 60)
    
    if not args.dry_run and stats['fixed_files'] > 0:
        print("✅ URL修复完成！现在所有产品URL都包含完整的https前缀")


if __name__ == "__main__":
    main()