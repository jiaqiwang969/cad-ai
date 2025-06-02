#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本：收集规格数为0的产品链接
用于发现和记录无法提取规格的产品页面
"""

import sys
sys.path.append('.')

import json
import time
from datetime import datetime
from pathlib import Path
from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

# 创建结果目录
DEBUG_DIR = Path("results/debug")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

def collect_zero_specs_products(cache_dir='results/cache/products', sample_size=100):
    """
    从产品缓存中抽样测试，收集规格数为0的产品
    
    Args:
        cache_dir: 产品缓存目录
        sample_size: 每个叶节点的抽样数量
    """
    print("\n" + "="*80)
    print("🔍 调试工具：收集规格数为0的产品链接")
    print("="*80)
    
    # 初始化
    crawler = OptimizedSpecificationsCrawler()
    zero_specs_products = []
    total_tested = 0
    total_zero_specs = 0
    
    # 获取所有产品缓存文件
    cache_path = Path(cache_dir)
    product_files = list(cache_path.glob("*.json"))
    
    print(f"\n📂 找到 {len(product_files)} 个产品缓存文件")
    print(f"📊 每个文件抽样测试 {sample_size} 个产品")
    
    # 遍历每个产品缓存文件
    for file_idx, product_file in enumerate(product_files[:5], 1):  # 先测试前5个文件
        print(f"\n[{file_idx}/{min(5, len(product_files))}] 处理文件: {product_file.name}")
        
        try:
            # 读取产品列表
            with open(product_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            print(f"  📦 文件包含 {len(products)} 个产品")
            
            # 抽样测试
            test_products = products[:sample_size] if len(products) > sample_size else products
            print(f"  🧪 测试 {len(test_products)} 个产品...")
            
            # 测试每个产品
            for i, product_url in enumerate(test_products):
                total_tested += 1
                
                # 显示进度
                if (i + 1) % 10 == 0:
                    print(f"    进度: {i+1}/{len(test_products)}")
                
                try:
                    # 提取规格
                    result = crawler.extract_specifications(product_url)
                    
                    # 检查是否规格数为0
                    if result['success'] and result['count'] == 0:
                        total_zero_specs += 1
                        zero_spec_info = {
                            'product_url': product_url,
                            'leaf_code': product_file.stem,
                            'test_time': datetime.now().isoformat(),
                            'result': result
                        }
                        zero_specs_products.append(zero_spec_info)
                        print(f"    ⚠️ 发现0规格产品 #{total_zero_specs}: {product_url[:80]}...")
                        
                except Exception as e:
                    print(f"    ❌ 测试失败: {e}")
                    
        except Exception as e:
            print(f"  ❌ 读取文件失败: {e}")
    
    # 保存结果
    print(f"\n" + "="*80)
    print(f"📊 测试汇总")
    print(f"="*80)
    print(f"✅ 总测试产品数: {total_tested}")
    print(f"⚠️  0规格产品数: {total_zero_specs}")
    print(f"📈 0规格比例: {total_zero_specs/total_tested*100:.1f}%")
    
    if zero_specs_products:
        # 保存详细结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存JSON格式（包含完整信息）
        json_file = DEBUG_DIR / f"zero_specs_products_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_tested': total_tested,
                    'total_zero_specs': total_zero_specs,
                    'test_time': datetime.now().isoformat(),
                    'sample_size_per_file': sample_size
                },
                'zero_specs_products': zero_specs_products
            }, f, ensure_ascii=False, indent=2)
        
        # 保存简单的URL列表（方便快速查看）
        txt_file = DEBUG_DIR / f"zero_specs_urls_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"# 规格数为0的产品URL列表\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 总数: {len(zero_specs_products)}\n")
            f.write("#" * 80 + "\n\n")
            
            for item in zero_specs_products:
                f.write(f"# 叶节点: {item['leaf_code']}\n")
                f.write(f"{item['product_url']}\n\n")
        
        print(f"\n💾 结果已保存:")
        print(f"  📄 详细信息: {json_file}")
        print(f"  📄 URL列表: {txt_file}")
        
        # 显示前5个示例
        print(f"\n📋 前5个0规格产品示例:")
        for i, item in enumerate(zero_specs_products[:5], 1):
            print(f"\n{i}. 叶节点: {item['leaf_code']}")
            print(f"   URL: {item['product_url']}")
    else:
        print(f"\n✅ 太好了！没有发现规格数为0的产品。")


def test_specific_urls():
    """测试特定的URL列表（用于调试已知问题URL）"""
    print("\n" + "="*80)
    print("🧪 测试特定URL")
    print("="*80)
    
    # 在这里添加需要调试的特定URL
    test_urls = [
        # 示例：添加您发现的0规格URL
        # "https://www.traceparts.cn/en/product/...",
    ]
    
    if not test_urls:
        print("ℹ️ 没有指定测试URL，请在代码中添加需要调试的URL")
        return
    
    crawler = OptimizedSpecificationsCrawler()
    zero_specs = []
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n[{i}/{len(test_urls)}] 测试URL:")
        print(f"  {url}")
        
        try:
            result = crawler.extract_specifications(url)
            print(f"  成功: {result['success']}")
            print(f"  规格数: {result['count']}")
            
            if result['count'] == 0:
                zero_specs.append({
                    'url': url,
                    'result': result
                })
                
        except Exception as e:
            print(f"  ❌ 错误: {e}")
    
    if zero_specs:
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = DEBUG_DIR / f"debug_specific_urls_{timestamp}.json"
        
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(zero_specs, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 调试结果已保存: {debug_file}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='收集规格数为0的产品链接')
    parser.add_argument('--sample-size', type=int, default=20, 
                       help='每个叶节点的抽样数量 (默认: 20)')
    parser.add_argument('--test-specific', action='store_true',
                       help='测试特定的URL列表')
    
    args = parser.parse_args()
    
    if args.test_specific:
        test_specific_urls()
    else:
        collect_zero_specs_products(sample_size=args.sample_size) 