#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理 failed_specs.jsonl 中的重复记录
==================================
移除重复的URL，只保留最新的失败记录
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def clean_failed_specs(failed_specs_file: Path):
    """清理失败记录文件中的重复项"""
    
    if not failed_specs_file.exists():
        print(f"❌ 文件不存在: {failed_specs_file}")
        return
    
    print(f"🔍 清理失败记录文件: {failed_specs_file}")
    
    # 读取所有记录
    records = {}
    duplicate_count = 0
    total_lines = 0
    
    with open(failed_specs_file, 'r', encoding='utf-8') as f:
        for line in f:
            total_lines += 1
            try:
                record = json.loads(line.strip())
                url = record.get('url')
                if url:
                    if url in records:
                        duplicate_count += 1
                        # 保留最新的记录（根据时间戳或tries数）
                        existing_record = records[url]
                        
                        # 比较时间戳
                        existing_ts = existing_record.get('ts', '')
                        new_ts = record.get('ts', '')
                        
                        if new_ts > existing_ts:
                            records[url] = record
                    else:
                        records[url] = record
            except Exception as e:
                print(f"⚠️ 解析行失败: {e}")
                continue
    
    print(f"📊 清理统计:")
    print(f"   • 原始行数: {total_lines}")
    print(f"   • 重复记录: {duplicate_count}")
    print(f"   • 唯一URL: {len(records)}")
    
    # 备份原文件
    backup_file = failed_specs_file.with_suffix('.jsonl.backup')
    failed_specs_file.rename(backup_file)
    print(f"💾 原文件已备份为: {backup_file}")
    
    # 写入清理后的记录
    with open(failed_specs_file, 'w', encoding='utf-8') as f:
        for record in records.values():
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"✅ 清理完成，已写入 {len(records)} 条唯一记录")
    
    return records

def analyze_failed_patterns(records: dict):
    """分析失败模式"""
    print(f"\n📈 失败模式分析:")
    
    # 按失败原因分组
    reasons = {}
    for record in records.values():
        reason = record.get('reason', 'Unknown')
        if reason not in reasons:
            reasons[reason] = []
        reasons[reason].append(record)
    
    print(f"🔍 失败原因分布:")
    for reason, records_list in sorted(reasons.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"   • {reason}: {len(records_list)} 个")
        
        # 显示几个示例URL
        if len(records_list) <= 3:
            for record in records_list:
                url = record.get('url', '')
                print(f"     - {url}")
        else:
            for record in records_list[:2]:
                url = record.get('url', '')
                print(f"     - {url}")
            print(f"     - ... (还有 {len(records_list)-2} 个)")
    
    # 按重试次数分组
    print(f"\n🔄 重试次数分布:")
    retry_counts = {}
    for record in records.values():
        tries = record.get('tries', 0)
        if tries not in retry_counts:
            retry_counts[tries] = 0
        retry_counts[tries] += 1
    
    for tries in sorted(retry_counts.keys()):
        count = retry_counts[tries]
        print(f"   • {tries} 次失败: {count} 个产品")
    
    return reasons

def main():
    """主函数"""
    failed_specs_file = PROJECT_ROOT / 'results' / 'cache' / 'failed_specs.jsonl'
    
    print("🧹 Failed Specs 清理工具")
    print("=" * 50)
    
    # 清理重复记录
    records = clean_failed_specs(failed_specs_file)
    
    if records:
        # 分析失败模式
        analyze_failed_patterns(records)
        
        print(f"\n🎯 建议:")
        print(f"   • 运行 'make test-realtime-specs' 来调试具体失败案例")
        print(f"   • 查看失败原因，针对性优化爬取策略")
        print(f"   • 对于重试次数过多的URL，考虑手动检查")

if __name__ == '__main__':
    main()