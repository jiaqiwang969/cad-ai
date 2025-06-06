#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 06-2  —— 增强版分类树提取测试
支持登录、滚动和Show More Results点击
"""

import os
import json
import logging
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# 添加项目根目录到路径
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.crawler.classification_enhanced import EnhancedClassificationCrawler

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("test-06-2")


def main():
    """主函数"""
    try:
        LOG.info("🚀 开始测试增强版分类树提取...")
        LOG.info("=" * 80)
        
        # 创建增强版爬取器
        crawler = EnhancedClassificationCrawler(log_level=logging.INFO)
        
        # 爬取分类树
        root, leaves = crawler.crawl_full_tree_enhanced()
        
        if not root or not leaves:
            LOG.error("❌ 爬取失败")
            return False
        
        # 统计信息
        total_nodes = root.get('total_nodes', 0)
        total_leaves = len(leaves)
        
        LOG.info("=" * 80)
        LOG.info("📊 爬取结果统计:")
        LOG.info(f"   总节点数: {total_nodes}")
        LOG.info(f"   叶节点数: {total_leaves}")
        
        # 统计层级分布
        def count_levels(node):
            level_stats = defaultdict(int)
            
            def traverse(n):
                if n.get('level', 0) > 0:
                    level_stats[n['level']] += 1
                for child in n.get('children', []):
                    traverse(child)
            
            traverse(node)
            return level_stats
        
        level_stats = count_levels(root)
        LOG.info("📊 层级分布:")
        for level in sorted(level_stats.keys()):
            LOG.info(f"   Level {level}: {level_stats[level]} 个节点")
        
        # 对比基准
        LOG.info("\n📋 与test-06基准对比:")
        test06_total = 1745
        test06_levels = {2: 13, 3: 100, 4: 458, 5: 557, 6: 436, 7: 147, 8: 32, 9: 2}
        
        LOG.info(f"   总节点数: {total_nodes} vs {test06_total} (差异: {total_nodes - test06_total:+d})")
        for level in sorted(test06_levels.keys()):
            current = level_stats.get(level, 0)
            expected = test06_levels[level]
            diff = current - expected
            status = "✅" if diff == 0 else "❌" if diff < 0 else "➕"
            LOG.info(f"   Level {level}: {current} vs {expected} (差异: {diff:+d}) {status}")
        
        # 构建完整数据结构
        data = {
            'root': root,
            'leaves': leaves,
            'metadata': {
                'generated': datetime.now().isoformat(),
                'cache_level': 1,
                'cache_level_name': 'CLASSIFICATION',
                'version': f'enhanced_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'total_leaves': len(leaves),
                'total_nodes': total_nodes,
                'total_products': 0,
                'total_specifications': 0,
                'enhancement': {
                    'login_enabled': True,
                    'show_more_enabled': True,
                    'scroll_enabled': True
                }
            }
        }
        
        # 保存结果
        result_file = "results/classification_tree_enhanced.json"
        os.makedirs("results", exist_ok=True)
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        LOG.info(f"\n✅ 增强版分类树已保存到: {result_file}")
        
        # 评估改进效果
        improvement = total_nodes - test06_total
        if improvement >= 0:
            LOG.info(f"🎉 改进成功！增加了 {improvement} 个节点")
        else:
            LOG.warning(f"⚠️ 节点数量减少了 {abs(improvement)} 个，可能需要进一步调整")
        
        return True
        
    except Exception as e:
        LOG.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)