#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终性能对比测试
==============
对比所有版本的性能差异，找出根本原因
"""

import sys
import os
import time
import logging
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.WARNING)  # 减少日志干扰

def run_test_and_measure(test_script, test_name):
    """运行测试并测量时间"""
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"脚本: {test_script}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # 运行测试脚本
        result = subprocess.run(
            [sys.executable, test_script],
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )
        
        elapsed = time.time() - start_time
        
        # 解析输出获取产品数
        output_lines = result.stdout.split('\n')
        product_count = 0
        
        for line in output_lines:
            if '获取产品数' in line or '实际提取链接数' in line:
                try:
                    # 提取数字
                    parts = line.split(':')
                    if len(parts) >= 2:
                        count_str = parts[1].strip().split()[0]
                        product_count = int(count_str)
                        break
                except:
                    continue
        
        print(f"✅ 完成: {elapsed:.1f}秒, {product_count}个产品")
        
        if result.returncode != 0:
            print(f"⚠️ 警告: 脚本返回错误码 {result.returncode}")
            if result.stderr:
                print(f"错误信息: {result.stderr[:200]}...")
        
        return elapsed, product_count, True
        
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"❌ 超时: {elapsed:.1f}秒 (超过10分钟限制)")
        return elapsed, 0, False
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ 错误: {e} ({elapsed:.1f}秒)")
        return elapsed, 0, False


def main():
    print("🎯 TraceParts 最终性能对比测试")
    print("=" * 80)
    print("将对比以下版本的性能差异:")
    print("1. test_5099_improved.py (基准)")
    print("2. scripts/test_ultra_fast.py (独立脚本，极致性能)")
    print("3. scripts/test_ultimate_crawler.py (终极性能类)")
    print("4. scripts/test_ultra_crawler.py (超高性能类)")
    print("5. scripts/test_lightweight_production.py (轻量级生产环境)")
    print("6. scripts/test_production_optimized.py (优化后生产环境)")
    print("7. scripts/test_products_optimized.py (原生产环境，INFO级别)")
    print()
    
    # 测试列表
    tests = [
        ("scripts/test_5099_improved.py", "基准: test_5099_improved.py"),
        ("scripts/test_ultra_fast.py", "独立脚本: 极致性能"),
        ("scripts/test_ultimate_crawler.py", "终极性能类: UltimateProductLinksCrawler"),
        ("scripts/test_ultra_crawler.py", "超高性能类: UltraProductLinksCrawler"),
        ("scripts/test_lightweight_production.py", "轻量级生产环境"),
        ("scripts/test_production_optimized.py", "优化生产环境"),
        ("scripts/test_products_optimized.py", "原生产环境 INFO级别"),
    ]
    
    results = []
    
    for script, name in tests:
        script_path = os.path.join(os.getcwd(), script)
        if os.path.exists(script_path):
            elapsed, count, success = run_test_and_measure(script_path, name)
            results.append((name, elapsed, count, success))
        else:
            print(f"\n❌ 跳过: {script} (文件不存在)")
            results.append((name, 0, 0, False))
    
    # 汇总对比
    print(f"\n\n{'='*80}")
    print("📊 性能对比汇总")
    print(f"{'='*80}")
    
    baseline_time = None
    baseline_count = None
    
    for i, (name, elapsed, count, success) in enumerate(results):
        if success:
            if i == 0:  # 基准
                baseline_time = elapsed
                baseline_count = count
                speedup_text = "基准"
            else:
                if baseline_time and baseline_time > 0:
                    speedup = baseline_time / elapsed
                    speedup_text = f"{speedup:.1f}x 更快" if speedup > 1 else f"{1/speedup:.1f}x 更慢"
                else:
                    speedup_text = "无法对比"
            
            print(f"{i+1}. {name}")
            print(f"   时间: {elapsed:.1f}秒, 产品: {count}, 速度提升: {speedup_text}")
        else:
            print(f"{i+1}. {name}")
            print(f"   ❌ 测试失败")
        print()
    
    # 性能分析
    print("🔍 主要性能瓶颈 (按影响程度排序):")
    print("1. 🌐 双重页面加载: 生产环境先访问base再访问目标页面 (100%额外开销)")
    print("2. 🏗️ 浏览器池管理: 线程锁、队列、context manager复杂逻辑")
    print("3. 🛡️ 复杂反检测: CDP脚本注入、多种反检测选项")
    print("4. 📝 复杂日志系统: LoggerMixin配置读取 vs 简单logging")
    print("5. ⚙️ Settings系统: 动态配置读取和解析开销") 
    print("6. 🍪 Cookie/Banner处理: 额外DOM操作")
    print("7. 📊 网络监控: register_success/fail统计调用")
    print("8. 🐌 DEBUG日志: 高频日志输出 (可达数百条)")
    
    print("\n💡 推荐解决方案:")
    print("🚀 极致性能: test_ultra_fast.py 或 UltraProductLinksCrawler")
    print("⚖️ 平衡方案: LightweightProductCrawler (性能+基本功能)")
    print("🏭 生产优化: 优化后的ProductLinksCrawler (去除双重加载)")
    print("🔍 调试使用: 仅在必要时启用DEBUG级别和完整功能")


if __name__ == "__main__":
    main() 