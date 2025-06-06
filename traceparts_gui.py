#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TraceParts 数据可视化GUI
========================

主要功能：
- 左侧导航栏：显示缓存数据的层级结构
- 右侧可视化区域：预留用于图形展示
- 支持分类树、产品链接、产品规格的多级导航
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading
import webbrowser


class TracepartsDataViewer:
    """TraceParts数据查看器"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TraceParts 数据可视化工具")
        self.root.geometry("1400x800")
        self.root.configure(bg='#f0f0f0')
        
        # 数据存储
        self.cache_data = None
        self.cache_level = None
        self.cache_dir = Path("results/cache")
        self.specs_cache_dir = Path("results/cache/specifications")
        
        # 设置样式
        self.setup_styles()
        
        # 创建界面
        self.create_interface()
        
        # 自动加载数据
        self.auto_load_data()
    
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置样式
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background='#f0f0f0')
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), background='#f0f0f0')
        style.configure('Info.TLabel', font=('Arial', 10), background='#f0f0f0')
        style.configure('Tree.Treeview', font=('Arial', 9))
        style.configure('Tree.Treeview.Heading', font=('Arial', 10, 'bold'))
    
    def create_interface(self):
        """创建主界面"""
        # 主容器
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 创建左右分栏
        paned_window = ttk.PanedWindow(main_frame, orient='horizontal')
        paned_window.pack(fill='both', expand=True)
        
        # 左侧导航栏 (1/3)
        self.create_navigation_panel(paned_window)
        
        # 右侧可视化区域 (2/3)
        self.create_visualization_panel(paned_window)
        
        # 设置分栏比例
        self.root.after(100, lambda: paned_window.sashpos(0, 460))  # 1/3位置
    
    def create_navigation_panel(self, parent):
        """创建左侧导航面板"""
        nav_frame = ttk.Frame(parent, width=460)
        parent.add(nav_frame, weight=1)
        
        # 标题和控制按钮
        header_frame = ttk.Frame(nav_frame)
        header_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(header_frame, text="📂 数据导航", style='Title.TLabel').pack(side='left')
        
        # 控制按钮
        btn_frame = ttk.Frame(header_frame)
        btn_frame.pack(side='right')
        
        ttk.Button(btn_frame, text="🔄 刷新", command=self.auto_load_data, width=8).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="📁 选择", command=self.select_cache_dir, width=8).pack(side='left', padx=2)
        
        # 缓存状态信息
        self.info_frame = ttk.LabelFrame(nav_frame, text="📊 缓存状态", padding=10)
        self.info_frame.pack(fill='x', pady=(0, 10))
        
        self.cache_info_text = tk.Text(self.info_frame, height=6, wrap='word', 
                                       font=('Consolas', 9), bg='#f8f8f8', 
                                       relief='flat', borderwidth=0)
        self.cache_info_text.pack(fill='x')
        
        # 数据树形结构
        tree_frame = ttk.LabelFrame(nav_frame, text="🌳 数据结构", padding=5)
        tree_frame.pack(fill='both', expand=True)
        
        # 创建Treeview
        self.tree = ttk.Treeview(tree_frame, style='Tree.Treeview')
        self.tree.pack(side='left', fill='both', expand=True)
        
        # 滚动条
        tree_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        tree_scroll.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        # 配置树形列
        self.tree['columns'] = ('type', 'count', 'info')
        self.tree.heading('#0', text='名称', anchor='w')
        self.tree.heading('type', text='类型', anchor='center')
        self.tree.heading('count', text='数量', anchor='center')
        self.tree.heading('info', text='信息', anchor='w')
        
        # 设置列宽
        self.tree.column('#0', width=200, minwidth=150)
        self.tree.column('type', width=60, minwidth=50)
        self.tree.column('count', width=50, minwidth=40)
        self.tree.column('info', width=120, minwidth=100)
        
        # 绑定双击事件
        self.tree.bind('<Double-1>', self.on_tree_double_click)
        self.tree.bind('<Button-3>', self.on_tree_right_click)  # 右键菜单
        
        # 底部状态栏
        status_frame = ttk.Frame(nav_frame)
        status_frame.pack(fill='x', pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="准备就绪", style='Info.TLabel')
        self.status_label.pack(side='left')
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.pack(side='right', fill='x', expand=True, padx=(10, 0))
    
    def create_visualization_panel(self, parent):
        """创建右侧可视化面板"""
        viz_frame = ttk.Frame(parent)
        parent.add(viz_frame, weight=2)
        
        # 标题
        ttk.Label(viz_frame, text="📈 数据可视化区域", style='Title.TLabel').pack(pady=10)
        
        # 预留的可视化容器
        self.viz_container = ttk.LabelFrame(viz_frame, text="🎯 即将推出：交互式图表", padding=20)
        self.viz_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 占位内容
        placeholder_text = """
        🚧 此区域预留用于图形可视化 🚧
        
        📊 计划功能：
        • 分类树可视化图表
        • 产品分布热力图  
        • 规格数据统计图
        • 失败URL分析图
        • 实时处理进度图
        
        🎯 即将支持：
        • 交互式节点图
        • 数据钻取功能
        • 自定义筛选器
        • 数据导出功能
        """
        
        placeholder_label = tk.Label(self.viz_container, text=placeholder_text, 
                                   font=('Arial', 12), justify='center',
                                   bg='#f0f0f0', fg='#666666')
        placeholder_label.pack(expand=True)
    
    def auto_load_data(self):
        """自动加载缓存数据"""
        self.update_status("🔍 正在扫描缓存目录...")
        self.progress.start()
        
        # 在后台线程中加载数据
        threading.Thread(target=self._load_data_thread, daemon=True).start()
    
    def _load_data_thread(self):
        """后台线程加载数据"""
        try:
            # 检查缓存目录
            if not self.cache_dir.exists():
                self.root.after(0, lambda: self.update_status("❌ 缓存目录不存在"))
                return
            
            # 读取缓存索引
            cache_index_file = self.cache_dir / 'cache_index.json'
            latest_data = None
            cache_level = "NONE"
            
            if cache_index_file.exists():
                with open(cache_index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    
                latest_files = index_data.get('latest_files', {})
                
                # 按优先级查找最新的缓存文件
                for level in ['specifications', 'products', 'classification']:
                    if level in latest_files:
                        cache_file = self.cache_dir / latest_files[level]
                        if cache_file.exists():
                            with open(cache_file, 'r', encoding='utf-8') as f:
                                latest_data = json.load(f)
                            cache_level = level.upper()
                            break
            
            # 更新UI
            self.root.after(0, lambda: self._update_ui_with_data(latest_data, cache_level))
            
        except Exception as e:
            self.root.after(0, lambda: self.update_status(f"❌ 加载失败: {str(e)}"))
        finally:
            self.root.after(0, self.progress.stop)
    
    def _update_ui_with_data(self, data: Optional[Dict], cache_level: str):
        """更新UI显示数据"""
        self.cache_data = data
        self.cache_level = cache_level
        
        if data is None:
            self.update_status("⚠️ 未找到有效的缓存数据")
            self.update_cache_info("无缓存数据")
            return
        
        # 更新缓存信息
        self.update_cache_info_display(data, cache_level)
        
        # 更新树形结构
        self.update_tree_view(data, cache_level)
        
        self.update_status(f"✅ 已加载 {cache_level} 级别缓存数据")
    
    def update_cache_info_display(self, data: Dict, cache_level: str):
        """更新缓存信息显示"""
        metadata = data.get('metadata', {})
        
        info_lines = [
            f"🎯 缓存级别: {cache_level}",
            f"📅 生成时间: {metadata.get('generated', 'Unknown')[:19]}",
            f"📊 版本号: {metadata.get('version', 'Unknown')}",
            f"🌿 叶节点数: {metadata.get('total_leaves', 0)}",
            f"📦 产品总数: {metadata.get('total_products', 0)}",
            f"📋 规格总数: {metadata.get('total_specifications', 0)}"
        ]
        
        # 添加失败统计
        failed_count = self.get_failed_specs_count()
        if failed_count > 0:
            info_lines.append(f"❌ 失败记录: {failed_count}")
        
        # 添加缓存文件统计
        cached_files = self.get_cached_files_count()
        if cached_files > 0:
            info_lines.append(f"💾 缓存文件: {cached_files}")
        
        self.update_cache_info('\n'.join(info_lines))
    
    def update_tree_view(self, data: Dict, cache_level: str):
        """更新树形视图"""
        # 清空现有内容
        self.tree.delete(*self.tree.get_children())
        
        if not data:
            return
        
        # 获取根节点和叶节点信息
        root_data = data.get('root', {})
        leaves_data = data.get('leaves', [])
        
        # 添加根节点
        total_leaves = len(leaves_data)
        total_products = sum(leaf.get('product_count', 0) for leaf in leaves_data)
        total_specs = 0
        
        if cache_level == 'SPECIFICATIONS':
            for leaf in leaves_data:
                for product in leaf.get('products', []):
                    if isinstance(product, dict):
                        total_specs += product.get('spec_count', 0)
        
        root_info = f"{total_leaves}叶 {total_products}品"
        if total_specs > 0:
            root_info += f" {total_specs}规格"
        
        # 添加根节点
        if root_data:
            root_name = root_data.get('name', 'TraceParts Classification')
            root_node = self.tree.insert('', 'end', text=f"🌳 {root_name}", 
                                        values=('ROOT', total_leaves, root_info))
            
            # 递归构建树形结构
            if 'children' in root_data:
                self._build_tree_recursive(root_node, root_data['children'], cache_level, leaves_data)
        else:
            # 如果没有root数据，直接显示叶节点
            root_node = self.tree.insert('', 'end', text='📊 TraceParts数据', 
                                        values=('ROOT', total_leaves, root_info))
            
            # 直接添加叶节点
            for leaf in leaves_data:
                self._add_leaf_node(root_node, leaf, cache_level)
        
        # 展开根节点
        self.tree.item(root_node, open=True)
    
    def _build_tree_recursive(self, parent_node, children_data: List[Dict], cache_level: str, leaves_data: List[Dict]):
        """递归构建树形结构"""
        for child in children_data:
            child_name = child.get('name', 'Unknown')
            child_code = child.get('code', 'Unknown')
            child_level = child.get('level', 0)
            is_leaf = child.get('is_leaf', False)
            
            # 选择合适的图标
            if is_leaf:
                icon = "🌿"
                node_type = "LEAF"
            else:
                if child_level <= 2:
                    icon = "📁"
                elif child_level <= 4:
                    icon = "📂"
                else:
                    icon = "📄"
                node_type = f"LEVEL_{child_level}"
            
            # 计算该节点的统计信息
            if is_leaf:
                # 从leaves_data中查找对应的叶节点数据
                leaf_data = None
                for leaf in leaves_data:
                    if leaf.get('code') == child_code:
                        leaf_data = leaf
                        break
                
                if leaf_data:
                    product_count = leaf_data.get('product_count', 0)
                    spec_count = 0
                    
                    if cache_level == 'SPECIFICATIONS':
                        for product in leaf_data.get('products', []):
                            if isinstance(product, dict):
                                spec_count += product.get('spec_count', 0)
                    
                    node_info = f"{product_count} 个产品"
                    if spec_count > 0:
                        node_info += f", {spec_count} 个规格"
                    
                    # 创建叶节点
                    leaf_node = self.tree.insert(parent_node, 'end', text=f"{icon} {child_name}", 
                                                values=(node_type, product_count, node_info))
                    
                    # 如果是规格级别，添加产品节点
                    if cache_level == 'SPECIFICATIONS' and product_count > 0:
                        self._add_products_to_leaf(leaf_node, leaf_data)
                else:
                    # 叶节点但没有找到数据
                    self.tree.insert(parent_node, 'end', text=f"{icon} {child_name}", 
                                   values=(node_type, 0, "无数据"))
            else:
                # 非叶节点，计算子节点统计
                child_leaves = self._count_child_leaves(child, leaves_data)
                child_products = sum(leaf.get('product_count', 0) for leaf in child_leaves)
                child_specs = 0
                
                if cache_level == 'SPECIFICATIONS':
                    for leaf in child_leaves:
                        for product in leaf.get('products', []):
                            if isinstance(product, dict):
                                child_specs += product.get('spec_count', 0)
                
                node_info = f"{len(child_leaves)}叶 {child_products}品"
                if child_specs > 0:
                    node_info += f" {child_specs}规格"
                
                # 创建中间节点
                child_node = self.tree.insert(parent_node, 'end', text=f"{icon} {child_name}", 
                                             values=(node_type, len(child_leaves), node_info))
                
                # 递归处理子节点
                if 'children' in child and child['children']:
                    self._build_tree_recursive(child_node, child['children'], cache_level, leaves_data)
    
    def _count_child_leaves(self, node: Dict, leaves_data: List[Dict]) -> List[Dict]:
        """统计节点下的所有叶节点"""
        result = []
        node_code = node.get('code', '')
        
        # 查找以该节点code开头的叶节点
        for leaf in leaves_data:
            leaf_code = leaf.get('code', '')
            if leaf_code.startswith(node_code):
                result.append(leaf)
        
        return result
    
    def _add_leaf_node(self, parent_node, leaf_data: Dict, cache_level: str):
        """添加单个叶节点"""
        leaf_name = leaf_data.get('name', 'Unknown')
        leaf_code = leaf_data.get('code', 'Unknown')
        product_count = leaf_data.get('product_count', 0)
        
        spec_count = 0
        if cache_level == 'SPECIFICATIONS':
            for product in leaf_data.get('products', []):
                if isinstance(product, dict):
                    spec_count += product.get('spec_count', 0)
        
        leaf_info = f"{product_count} 个产品"
        if spec_count > 0:
            leaf_info += f", {spec_count} 个规格"
        
        leaf_node = self.tree.insert(parent_node, 'end', text=f"🌿 {leaf_name}", 
                                   values=('LEAF', product_count, leaf_info))
        
        # 如果是规格级别，添加产品节点
        if cache_level == 'SPECIFICATIONS' and product_count > 0:
            self._add_products_to_leaf(leaf_node, leaf_data)
    
    def _add_products_to_leaf(self, leaf_node, leaf_data: Dict):
        """为叶节点添加产品信息"""
        products = leaf_data.get('products', [])
        display_products = products[:5]  # 只显示前5个产品避免太多
        
        for i, product in enumerate(display_products):
            if isinstance(product, dict):
                product_url = product.get('product_url', 'Unknown')
                spec_count = product.get('spec_count', 0)
                
                # 从URL提取产品名
                product_name = self.extract_product_name(product_url)
                
                product_info = f"{spec_count} 个规格"
                product_node = self.tree.insert(leaf_node, 'end', text=f"📦 {product_name}", 
                                              values=('PRODUCT', spec_count, product_info))
                
                # 添加规格详情（只显示前3个）
                if spec_count > 0:
                    specs = product.get('specifications', [])[:3]
                    for j, spec in enumerate(specs):
                        if isinstance(spec, dict):
                            spec_ref = spec.get('reference', f'Spec {j+1}')
                            spec_dims = spec.get('dimensions', '')
                            spec_info = f"规格: {spec_dims}" if spec_dims else "规格详情"
                            
                            self.tree.insert(product_node, 'end', text=f"⚙️ {spec_ref}", 
                                           values=('SPEC', 1, spec_info))
                    
                    # 如果规格太多，添加提示
                    if spec_count > 3:
                        remaining = spec_count - 3
                        self.tree.insert(product_node, 'end', text=f"... 还有 {remaining} 个规格", 
                                       values=('MORE_SPECS', remaining, '点击查看更多'))
        
        # 如果产品太多，添加提示
        if len(products) > 5:
            remaining = len(products) - 5
            self.tree.insert(leaf_node, 'end', text=f"... 还有 {remaining} 个产品", 
                           values=('MORE_PRODUCTS', remaining, '点击查看更多'))
    
    def extract_product_name(self, url: str) -> str:
        """从URL提取产品名称"""
        try:
            if '/product/' in url:
                product_part = url.split('/product/')[-1].split('?')[0]
                return product_part.replace('-', ' ').title()[:30]
            return "Unknown Product"
        except:
            return "Unknown Product"
    
    def get_failed_specs_count(self) -> int:
        """获取失败记录数量"""
        try:
            failed_file = self.cache_dir / 'failed_specs.jsonl'
            if failed_file.exists():
                with open(failed_file, 'r', encoding='utf-8') as f:
                    return len([line for line in f if line.strip()])
            return 0
        except:
            return 0
    
    def get_cached_files_count(self) -> int:
        """获取缓存文件数量"""
        try:
            if self.specs_cache_dir.exists():
                # 统计唯一产品数（通过base_name去重）
                base_names = set()
                for file in self.specs_cache_dir.glob("*_complete.json"):
                    base_name = file.name.replace('_complete.json', '')
                    base_names.add(base_name)
                for file in self.specs_cache_dir.glob("*.json"):
                    if not file.name.endswith(('_complete.json', '_list.json')):
                        base_name = file.name.replace('.json', '')
                        base_names.add(base_name)
                return len(base_names)
            return 0
        except:
            return 0
    
    def on_tree_double_click(self, event):
        """处理树形视图双击事件"""
        try:
            item = self.tree.selection()[0]
            item_text = self.tree.item(item, 'text')
            item_values = self.tree.item(item, 'values')
            
            if len(item_values) > 0:
                item_type = item_values[0]
                
                if item_type == 'PRODUCT':
                    # 双击产品时尝试打开产品URL
                    self.open_product_details(item)
                elif item_type in ['MORE_PRODUCTS', 'MORE_SPECS']:
                    # 展开显示更多产品或规格
                    self.show_more_items(item, item_type)
                elif item_type == 'SPEC':
                    # 双击规格时显示详细信息
                    self.show_spec_details(item)
                elif item_type.startswith('LEVEL_') or item_type in ['ROOT', 'LEAF']:
                    # 展开/折叠节点
                    current_open = self.tree.item(item, 'open')
                    self.tree.item(item, open=not current_open)
        except IndexError:
            # 没有选中项目
            pass
    
    def on_tree_right_click(self, event):
        """处理右键菜单"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            
            # 创建右键菜单
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="📋 复制信息", command=lambda: self.copy_item_info(item))
            menu.add_command(label="🔍 查看详情", command=lambda: self.show_item_details(item))
            
            item_values = self.tree.item(item, 'values')
            if len(item_values) > 0 and item_values[0] == 'PRODUCT':
                menu.add_separator()
                menu.add_command(label="🌐 在浏览器中打开", command=lambda: self.open_product_details(item))
            
            menu.post(event.x_root, event.y_root)
    
    def copy_item_info(self, item):
        """复制项目信息到剪贴板"""
        item_text = self.tree.item(item, 'text')
        item_values = self.tree.item(item, 'values')
        
        info = f"{item_text}\n类型: {item_values[0] if item_values else 'Unknown'}"
        if len(item_values) > 2:
            info += f"\n信息: {item_values[2]}"
        
        self.root.clipboard_clear()
        self.root.clipboard_append(info)
        self.update_status("📋 已复制到剪贴板")
    
    def show_item_details(self, item):
        """显示项目详细信息"""
        item_text = self.tree.item(item, 'text')
        item_values = self.tree.item(item, 'values')
        
        details = f"项目: {item_text}\n"
        if item_values:
            details += f"类型: {item_values[0]}\n"
            if len(item_values) > 1:
                details += f"数量: {item_values[1]}\n"
            if len(item_values) > 2:
                details += f"信息: {item_values[2]}\n"
        
        messagebox.showinfo("详细信息", details)
    
    def open_product_details(self, item):
        """打开产品详情（在浏览器中）"""
        # 这里可以实现打开产品URL的功能
        messagebox.showinfo("功能预留", "此功能将在未来版本中实现\n可以在浏览器中打开产品页面")
    
    def show_more_items(self, item, item_type: str):
        """显示更多产品或规格"""
        if item_type == 'MORE_PRODUCTS':
            messagebox.showinfo("功能预留", "此功能将在未来版本中实现\n可以展开显示所有产品")
        elif item_type == 'MORE_SPECS':
            messagebox.showinfo("功能预留", "此功能将在未来版本中实现\n可以展开显示所有规格")
    
    def show_spec_details(self, item):
        """显示规格详细信息"""
        item_text = self.tree.item(item, 'text')
        item_values = self.tree.item(item, 'values')
        
        details = f"规格详情:\n{item_text}\n"
        if len(item_values) > 2:
            details += f"信息: {item_values[2]}\n"
        
        # 这里可以扩展显示更详细的规格信息
        messagebox.showinfo("规格详情", details)
    
    def select_cache_dir(self):
        """选择缓存目录"""
        dir_path = filedialog.askdirectory(title="选择缓存目录", initialdir=str(self.cache_dir))
        if dir_path:
            self.cache_dir = Path(dir_path)
            self.specs_cache_dir = self.cache_dir / "specifications"
            self.auto_load_data()
    
    def update_cache_info(self, text: str):
        """更新缓存信息文本"""
        self.cache_info_text.delete(1.0, tk.END)
        self.cache_info_text.insert(1.0, text)
    
    def update_status(self, message: str):
        """更新状态栏"""
        self.status_label.config(text=f"{datetime.now().strftime('%H:%M:%S')} - {message}")


def main():
    """主函数"""
    root = tk.Tk()
    app = TracepartsDataViewer(root)
    
    # 设置窗口图标和其他属性
    try:
        # 设置窗口最小尺寸
        root.minsize(1000, 600)
        
        # 居中显示窗口
        root.eval('tk::PlaceWindow . center')
        
    except:
        pass
    
    # 启动GUI
    root.mainloop()


if __name__ == "__main__":
    main()