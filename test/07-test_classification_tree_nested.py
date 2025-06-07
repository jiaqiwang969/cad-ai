#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 07  —— 读取 test-06 生成的扁平分类列表，按 CatalogPath TP 代码建立真正的树结构，
并标注叶节点；输出 2 份文件：
  • results/traceparts_tree_nested.json   —— 完整嵌套结构
  • results/traceparts_tree_leaves.jsonl  —— 每行一个叶节点（方便后续批量爬取）
"""

import os, json, logging
from datetime import datetime
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger('test-07')

FLAT_FILE = 'results/traceparts_classification_tree_full.json'
NESTED_FILE = 'results/traceparts_tree_nested.json'
LEAF_FILE = 'results/traceparts_tree_leaves.jsonl'


def tp_code_from_url(url: str) -> str:
    """提取 CatalogPath 中的 TP 编码，如 TP01001001"""
    if 'CatalogPath=TRACEPARTS%3A' not in url:
        return ''
    return url.split('CatalogPath=TRACEPARTS%3A')[1].split('&')[0]


def build_nested_tree(records):
    """根据 records 构建嵌套树，返回根节点和叶节点列表"""
    # 预创建虚拟根
    root = {
    'name': 'TraceParts Classification',
    'url': 'https://www.traceparts.cn',
    'level': 1,
    'code': 'TRACEPARTS_ROOT',
    'children': []
}
    code_map = {'TRACEPARTS_ROOT': root}

    # 先为每条记录添加 code
    for rec in records:
        rec['code'] = tp_code_from_url(rec['url'])

    # 按 level 排序，确保父节点在前
    records.sort(key=lambda r: r['level'])

    for rec in records:
    node = {
        'name': rec['name'],
        'url': rec['url'],
        'level': rec['level'],
        'code': rec['code'],
        'children': []
    }
        code_map[node['code']] = node

        # 确定父 code
        if node['level'] == 2:
            parent_code = 'TRACEPARTS_ROOT'
        else:
            parent_code = node['code'][:-3]  # 每 3 位上溯一级
        parent = code_map.get(parent_code)
        if not parent:
            # 创建占位父节点（名称稍后可补全）
            parent = code_map.setdefault(parent_code, {
                'name': '(placeholder)',
                'url': '',
                'level': node['level'] - 1,
                'code': parent_code,
                'children': []
            })
        parent['children'].append(node)

    # 递归标注叶子
    leaves = []

    def mark(node):
        if node.get('children'):
            node['is_leaf'] = False
            for ch in node['children']:
                mark(ch)
else:
            node['is_leaf'] = True
            leaves.append(node)

    mark(root)
    return root, leaves


def main():
    if not os.path.isfile(FLAT_FILE):
        LOG.error('请先运行 make test-06 生成扁平分类列表')
        return False
    with open(FLAT_FILE, 'r', encoding='utf-8') as f:
        flat = json.load(f)
    records = flat.get('records', [])
    LOG.info(f'加载扁平记录 {len(records)} 条')

    root, leaves = build_nested_tree(records)
    LOG.info(f'嵌套树 L2 主类目: {len(root["children"])}，叶节点: {len(leaves)}')

    os.makedirs('results', exist_ok=True)
    with open(NESTED_FILE, 'w', encoding='utf-8') as f:
        json.dump({'generated': datetime.now().isoformat(), 'root': root}, f, ensure_ascii=False, indent=2)
    with open(LEAF_FILE, 'w', encoding='utf-8') as f:
        for leaf in leaves:
            f.write(json.dumps(leaf, ensure_ascii=False) + '\n')
    LOG.info(f'✅ 已保存嵌套树到 {NESTED_FILE}，叶节点 {len(leaves)} 条到 {LEAF_FILE}')
    return True


if __name__ == '__main__':
    print('✅ test-07 成功' if main() else '❌ test-07 失败') 