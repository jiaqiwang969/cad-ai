#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
失败规格调试工具
=============
专门调试 failed_specs.jsonl 中的失败案例
"""

import sys
import json
import logging
import time
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler

def load_failed_specs(failed_specs_file: Path) -> List[Dict]:
    """加载失败的规格记录"""
    failed_records = []
    
    if not failed_specs_file.exists():
        print(f"❌ 失败记录文件不存在: {failed_specs_file}")
        return failed_records
    
    with open(failed_specs_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                failed_records.append(record)
            except:
                continue
    
    return failed_records

def analyze_failed_specs(failed_records: List[Dict]):
    """分析失败记录"""
    print(f"📊 失败记录分析:")
    print(f"   • 总失败记录: {len(failed_records)}")
    
    # 按失败原因分组
    reasons = {}
    for record in failed_records:
        reason = record.get('reason', 'Unknown')
        if reason not in reasons:
            reasons[reason] = []
        reasons[reason].append(record)
    
    print(f"\n🔍 失败原因分布:")
    for reason, records in sorted(reasons.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"   • {reason}: {len(records)} 个")
    
    # 按供应商分析
    print(f"\n🏭 供应商分析:")
    vendors = {}
    for record in failed_records:
        url = record.get('url', '')
        if 'industrietechnik' in url.lower():
            vendor = 'industrietechnik'
        elif 'apostoli' in url.lower():
            vendor = 'apostoli'
        elif 'skf' in url.lower():
            vendor = 'skf'
        elif 'timken' in url.lower():
            vendor = 'timken'
        elif 'traceparts-site' in url.lower():
            vendor = 'traceparts'
        else:
            vendor = 'other'
        
        if vendor not in vendors:
            vendors[vendor] = []
        vendors[vendor].append(record)
    
    for vendor, records in sorted(vendors.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"   • {vendor}: {len(records)} 个")
    
    return reasons, vendors

def debug_specific_urls(urls: List[str], max_debug: int = 5):
    """调试具体的失败URL"""
    print(f"\n🔍 开始调试具体URL (最多 {max_debug} 个):")
    print("=" * 60)
    
    # 创建规格爬取器（使用更详细的日志）
    crawler = OptimizedSpecificationsCrawler(log_level=logging.DEBUG)
    
    results = []
    for i, url in enumerate(urls[:max_debug]):
        print(f"\n[{i+1}/{min(max_debug, len(urls))}] 调试URL:")
        print(f"🔗 {url}")
        print("-" * 60)
        
        try:
            # 尝试提取规格
            start_time = time.time()
            result = crawler.extract_specifications(url)
            elapsed = time.time() - start_time
            
            print(f"⏱️  耗时: {elapsed:.2f}s")
            print(f"✅ 成功: {result.get('success', False)}")
            print(f"📋 规格数: {result.get('count', 0)}")
            
            if result.get('success') and result.get('count', 0) > 0:
                print(f"🎉 成功提取到规格！")
                specs = result.get('specifications', [])
                if specs:
                    print(f"📄 规格示例: {specs[0] if isinstance(specs[0], dict) else str(specs[0])[:100]}")
            else:
                print(f"❌ 提取失败")
                if 'error' in result:
                    print(f"🚨 错误信息: {result['error']}")
            
            results.append({
                'url': url,
                'result': result,
                'elapsed': elapsed
            })
            
        except Exception as e:
            print(f"💥 异常: {e}")
            results.append({
                'url': url,
                'result': {'success': False, 'error': str(e)},
                'elapsed': 0
            })
        
        # 间隔一下避免被检测
        if i < min(max_debug, len(urls)) - 1:
            print(f"\n⏳ 等待 3 秒...")
            time.sleep(3)
    
    return results

def main():
    """主函数"""
    print("🔍 Failed Specs 调试工具")
    print("=" * 50)
    
    # 设置详细日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 加载失败记录
    failed_specs_file = PROJECT_ROOT / 'results' / 'cache' / 'failed_specs.jsonl'
    failed_records = load_failed_specs(failed_specs_file)
    
    if not failed_records:
        print("✅ 没有失败记录需要调试")
        return
    
    # 分析失败记录
    reasons, vendors = analyze_failed_specs(failed_records)
    
    # 选择要调试的URL
    print(f"\n🎯 选择调试模式:")
    print(f"1. 调试最新的 5 个失败案例")
    print(f"2. 调试 industrietechnik 失败案例")
    print(f"3. 调试 ZeroSpecifications 失败案例")
    print(f"4. 调试所有不同原因的代表案例")
    
    choice = input(f"\n请选择 (1-4，默认1): ").strip() or "1"
    
    urls_to_debug = []
    
    if choice == "1":
        # 最新的失败案例
        latest_records = sorted(failed_records, key=lambda x: x.get('ts', ''), reverse=True)[:5]
        urls_to_debug = [r['url'] for r in latest_records]
        print(f"\n🕐 调试最新的 {len(urls_to_debug)} 个失败案例")
        
    elif choice == "2":
        # industrietechnik 案例
        industrietechnik_records = [r for r in failed_records if 'industrietechnik' in r.get('url', '').lower()]
        urls_to_debug = [r['url'] for r in industrietechnik_records[:5]]
        print(f"\n🏭 调试 industrietechnik 的 {len(urls_to_debug)} 个失败案例")
        
    elif choice == "3":
        # ZeroSpecifications 案例
        zero_specs_records = [r for r in failed_records if r.get('reason') == 'ZeroSpecifications']
        urls_to_debug = [r['url'] for r in zero_specs_records[:5]]
        print(f"\n📊 调试 ZeroSpecifications 的 {len(urls_to_debug)} 个失败案例")
        
    elif choice == "4":
        # 每种失败原因的代表
        for reason, records in reasons.items():
            if len(urls_to_debug) < 10:  # 最多10个
                urls_to_debug.append(records[0]['url'])
        print(f"\n🎯 调试各种失败原因的代表案例 ({len(urls_to_debug)} 个)")
    
    if not urls_to_debug:
        print("❌ 没有找到符合条件的URL")
        return
    
    # 开始调试
    results = debug_specific_urls(urls_to_debug)
    
    # 汇总调试结果
    print(f"\n📊 调试结果汇总:")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r['result'].get('success', False))
    print(f"✅ 成功: {success_count}/{len(results)}")
    print(f"❌ 失败: {len(results) - success_count}/{len(results)}")
    
    if success_count > 0:
        print(f"\n🎉 有 {success_count} 个之前失败的URL现在成功了！")
        print(f"💡 建议: 运行清理脚本移除这些已修复的失败记录")
        print(f"   python3 scripts/clean_failed_specs.py")

if __name__ == '__main__':
    main()