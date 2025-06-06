#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试两阶段分离的管道
===============
阶段1：使用简单Selenium方法构建分类树（test-06风格）
阶段2：使用高级Playwright策略提取产品（test-08风格）
"""

import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

from src.crawler.classification_enhanced import EnhancedClassificationCrawler
from src.crawler.ultimate_products_v2 import UltimateProductLinksCrawlerV2

def test_classification_stage():
    """测试阶段1：分类树构建（test-06风格）"""
    print("🚀 开始测试阶段1：分类树构建（简单Selenium方法）")
    
    try:
        # 创建分类爬取器
        classifier = EnhancedClassificationCrawler(headless=True)
        
        # 构建分类树
        tree, leaves = classifier.crawl_full_tree_enhanced()
        
        if tree and leaves:
            print(f"✅ 阶段1成功：构建了分类树，共 {len(leaves)} 个叶节点")
            
            # 显示前几个叶节点
            print("📁 前5个叶节点:")
            for i, leaf in enumerate(leaves[:5]):
                print(f"   {i+1}. {leaf['name']} (L{leaf['level']}) - {leaf['url'][:80]}...")
            
            return leaves[:3]  # 返回前3个叶节点用于测试阶段2
        else:
            print("❌ 阶段1失败：未能构建分类树")
            return []
            
    except Exception as e:
        print(f"❌ 阶段1异常: {e}")
        return []

def test_products_stage(test_leaves):
    """测试阶段2：产品提取（test-08风格）"""
    print("\n🚀 开始测试阶段2：产品提取（高级Playwright策略）")
    
    if not test_leaves:
        print("⚠️ 没有可用的叶节点进行测试")
        return
    
    try:
        # 创建产品爬取器
        products_crawler = UltimateProductLinksCrawlerV2(headless=True)
        
        for i, leaf in enumerate(test_leaves):
            print(f"\n📦 测试叶节点 {i+1}: {leaf['name']}")
            
            try:
                # 提取产品链接
                products, progress_info = products_crawler.collect_all_product_links(leaf['url'])
                
                if products:
                    print(f"✅ 成功提取 {len(products)} 个产品")
                    print(f"📊 进度信息: {progress_info}")
                    
                    # 显示前几个产品（完整URL）
                    print(f"🔗 前3个产品链接（完整URL）:")
                    for j, product_url in enumerate(products[:3]):
                        # 从URL中提取产品名称（简化显示）
                        product_name = product_url.split('Product=')[-1].split('&')[0] if 'Product=' in product_url else 'Unknown'
                        print(f"   {j+1}. 产品名: {product_name}")
                        print(f"       完整URL: {product_url}")
                        print()
                else:
                    print(f"⚠️ 未找到产品")
                    
            except Exception as e:
                print(f"❌ 叶节点 {leaf['name']} 产品提取失败: {e}")
        
        print("\n✅ 阶段2测试完成")
        
    except Exception as e:
        print(f"❌ 阶段2异常: {e}")

def main():
    """主函数"""
    print("🎯 测试两阶段分离的管道")
    print("=" * 50)
    
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 测试阶段1：分类树构建
    test_leaves = test_classification_stage()
    
    # 测试阶段2：产品提取
    test_products_stage(test_leaves)
    
    print("\n" + "=" * 50)
    print("🏁 两阶段分离管道测试完成")

if __name__ == "__main__":
    main()