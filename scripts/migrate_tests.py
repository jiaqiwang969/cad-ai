#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本迁移工具
===============
将旧的测试脚本迁移到新的目录结构
"""

import os
import shutil
from pathlib import Path

def migrate_tests():
    """迁移测试脚本"""
    old_test_dir = Path('test')
    new_test_dir = Path('tests')
    
    if not old_test_dir.exists():
        print("❌ 旧测试目录不存在")
        return
    
    # 创建新测试目录
    new_test_dir.mkdir(exist_ok=True)
    
    # 创建子目录
    subdirs = ['unit', 'integration', 'legacy']
    for subdir in subdirs:
        (new_test_dir / subdir).mkdir(exist_ok=True)
    
    # 迁移文件
    migrations = {
        # 单元测试
        '01-test_openai_api.py': 'unit/test_openai_api.py',
        '02-test_langchain_api.py': 'unit/test_langchain_api.py',
        
        # 集成测试
        '03-test_langchain_web_scraping.py': 'integration/test_web_scraping.py',
        '04-test_async_web_scraping.py': 'integration/test_async_scraping.py',
        '05-test_category_drill_down.py': 'integration/test_category_drill.py',
        '06-test_classification_tree_recursive.py': 'integration/test_classification.py',
        '07-test_classification_tree_nested.py': 'integration/test_tree_builder.py',
        '08-test_leaf_product_links.py': 'integration/test_product_links.py',
        '09-test_batch_leaf_product_links.py': 'integration/test_batch_products.py',
        '09-1-test_product_specifications_extractor.py': 'integration/test_specifications.py',
        '10-test_product_cad_download.py': 'integration/test_cad_download.py',
    }
    
    # 复制legacy目录
    if (old_test_dir / 'legacy').exists():
        shutil.copytree(
            old_test_dir / 'legacy',
            new_test_dir / 'legacy',
            dirs_exist_ok=True
        )
        print("✅ 迁移 legacy 目录")
    
    # 迁移测试文件
    for old_name, new_name in migrations.items():
        old_path = old_test_dir / old_name
        new_path = new_test_dir / new_name
        
        if old_path.exists():
            shutil.copy2(old_path, new_path)
            print(f"✅ 迁移: {old_name} → {new_name}")
        else:
            print(f"⚠️  跳过: {old_name} (文件不存在)")
    
    # 创建 __init__.py
    for root, dirs, files in os.walk(new_test_dir):
        root_path = Path(root)
        if not (root_path / '__init__.py').exists():
            (root_path / '__init__.py').touch()
    
    print("\n📋 迁移完成！")
    print(f"测试文件已迁移到 {new_test_dir} 目录")
    print("\n建议后续步骤:")
    print("1. 检查迁移的文件")
    print("2. 更新导入路径")
    print("3. 运行测试确保正常")
    print("4. 删除旧的 test 目录")


if __name__ == '__main__':
    migrate_tests() 