#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
线程安全日志模块
===============
解决多线程并发日志输出混乱问题
"""

import logging
import threading
import queue
import time
from datetime import datetime
from typing import Optional, Dict, Any
from collections import defaultdict


class ThreadSafeLogger:
    """线程安全的日志器，支持进度追踪和批量输出"""
    
    def __init__(self, name: str, level: int = logging.INFO):
        """初始化线程安全日志器"""
        self.name = name
        self.level = level
        self._lock = threading.Lock()
        self._progress_data = defaultdict(dict)
        self._last_progress_update = defaultdict(float)
        
        # 创建基础logger
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(level)
        # 防止日志向上传播到根logger，避免重复输出
        self.logger.propagate = False
    
    def _format_progress_bar(self, current: int, total: int, width: int = 30) -> str:
        """格式化进度条"""
        if total == 0:
            return "[" + " " * width + "]"
        
        percent = current / total
        filled = int(width * percent)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {current}/{total} ({percent*100:.1f}%)"
    
    def log_task_start(self, task_id: str, task_name: str, total: int = 0):
        """记录任务开始"""
        with self._lock:
            self._progress_data[task_id] = {
                'name': task_name,
                'total': total,
                'current': 0,
                'start_time': time.time(),
                'status': 'running'
            }
            self.logger.info(f"\n▶️  开始: {task_name} ({total} 项)")
    
    def log_task_progress(self, task_id: str, current: int, message: str = ""):
        """更新任务进度（带节流）"""
        with self._lock:
            if task_id not in self._progress_data:
                return
            
            # 更新进度数据
            task = self._progress_data[task_id]
            task['current'] = current
            
            # 节流：根据任务规模调整更新频率
            now = time.time()
            last_update = self._last_progress_update.get(task_id, 0)
            
            # 动态节流：任务越大，更新频率越低
            if task['total'] > 1000:
                update_interval = 10.0  # 超大任务每10秒更新一次
            elif task['total'] > 100:
                update_interval = 5.0   # 大任务每5秒更新一次
            elif task['total'] > 50:
                update_interval = 3.0   # 中等任务每3秒更新一次
            else:
                update_interval = 1.0   # 小任务每秒更新一次
            
            # 只在达到更新间隔或任务完成时更新
            if now - last_update < update_interval and current < task['total']:
                return
            
            self._last_progress_update[task_id] = now
            
            # 简化的进度显示
            percent = current / task['total'] * 100 if task['total'] > 0 else 0
            elapsed = now - task['start_time']
            speed = current / elapsed if elapsed > 0 else 0
            
            # 根据任务类型选择显示格式
            if "产品链接" in task['name']:
                msg = f"   进度: {current}/{task['total']} 叶节点 [{percent:3.0f}%]"
                if speed > 0:
                    msg += f" - {speed:.1f} 个/秒"
            elif "产品规格" in task['name']:
                msg = f"   进度: {current}/{task['total']} 产品 [{percent:3.0f}%]"
                if speed > 0:
                    msg += f" - {speed:.1f} 个/秒"
            else:
                msg = f"   [{percent:3.0f}%] {task['name']}: {current}/{task['total']}"
            
            # 添加附加信息
            if message and len(message) < 80:
                msg += f" - {message}"
            
            self.logger.info(msg)
    
    def log_task_complete(self, task_id: str, success: bool = True, message: str = ""):
        """记录任务完成"""
        with self._lock:
            if task_id not in self._progress_data:
                return
            
            task = self._progress_data[task_id]
            elapsed = time.time() - task['start_time']
            
            # 转换时间格式
            if elapsed > 60:
                time_str = f"{elapsed/60:.1f}分钟"
            else:
                time_str = f"{elapsed:.1f}秒"
            
            if success:
                icon = "✓"
                status_msg = f"{icon} 完成: {task['name']} (耗时 {time_str})"
            else:
                icon = "✗"
                status_msg = f"{icon} 失败: {task['name']} (耗时 {time_str})"
            
            if message:
                status_msg += f" - {message}"
            
            self.logger.info(status_msg)
            
            # 清理数据
            del self._progress_data[task_id]
            if task_id in self._last_progress_update:
                del self._last_progress_update[task_id]
    
    def log_batch_results(self, title: str, results: Dict[str, Any]):
        """批量输出结果（避免并发混乱）"""
        with self._lock:
            self.logger.info(f"\n{'─'*50}")
            self.logger.info(f"📊 {title}")
            self.logger.info(f"{'─'*50}")
            
            for key, value in results.items():
                self.logger.info(f"  {key}: {value}")
            
            self.logger.info(f"{'─'*50}")
    
    def info(self, message: str):
        """线程安全的info日志"""
        with self._lock:
            self.logger.info(message)
    
    def warning(self, message: str):
        """线程安全的warning日志"""
        with self._lock:
            self.logger.warning(message)
    
    def error(self, message: str, exc_info=False):
        """线程安全的error日志"""
        with self._lock:
            self.logger.error(message, exc_info=exc_info)
    
    def debug(self, message: str):
        """线程安全的debug日志"""
        with self._lock:
            self.logger.debug(message)


class ProgressTracker:
    """进度追踪器，用于汇总多个任务的进度"""
    
    def __init__(self, logger: ThreadSafeLogger):
        """初始化进度追踪器"""
        self.logger = logger
        self._tasks = {}
        self._lock = threading.Lock()
    
    def register_task(self, category: str, total: int):
        """注册任务类别"""
        with self._lock:
            self._tasks[category] = {
                'total': total,
                'completed': 0,
                'success': 0,
                'failed': 0
            }
    
    def update_task(self, category: str, success: bool = True):
        """更新任务进度"""
        with self._lock:
            if category not in self._tasks:
                return
            
            task = self._tasks[category]
            task['completed'] += 1
            if success:
                task['success'] += 1
            else:
                task['failed'] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """获取进度汇总"""
        with self._lock:
            summary = {}
            for category, task in self._tasks.items():
                summary[category] = {
                    'progress': f"{task['completed']}/{task['total']}",
                    'success_rate': f"{task['success']/task['completed']*100:.1f}%" if task['completed'] > 0 else "0%",
                    'failed': task['failed']
                }
            return summary
    
    def print_summary(self):
        """打印进度汇总"""
        summary = self.get_summary()
        # 简化的汇总格式
        with self._lock:
            self.logger.info("\n📊 任务汇总:")
            for category, stats in summary.items():
                self.logger.info(f"   • {category}: {stats['progress']} 完成, "
                               f"成功率 {stats['success_rate']}, "
                               f"失败 {stats['failed']} 个") 