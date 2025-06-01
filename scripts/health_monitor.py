#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康检查和监控脚本
==================
监控优化版Pipeline运行状态并发送告警
"""

import json
import time
import logging
import psutil
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config.production import CONFIG


class HealthMonitor:
    """健康监控器"""
    
    def __init__(self):
        """初始化监控器"""
        self.logger = self._setup_logger()
        self.config = CONFIG
        self.metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'disk_usage': [],
            'active_threads': [],
            'error_count': 0,
            'last_check': None
        }
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger('health-monitor')
        
        # 文件处理器
        log_file = Path(CONFIG['paths']['logs']) / 'health_monitor.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
        
        return logger
    
    def check_system_resources(self) -> Dict[str, float]:
        """检查系统资源使用情况"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'active_threads': len(psutil.Process().threads())
        }
    
    def check_pipeline_status(self) -> Dict[str, Any]:
        """检查Pipeline运行状态"""
        status = {
            'running': False,
            'last_run': None,
            'success_rate': 0,
            'recent_errors': []
        }
        
        # 检查最近的输出文件
        products_dir = Path(self.config['paths']['products'])
        recent_files = sorted(
            products_dir.glob('optimized_pipeline_*.json'),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:5]
        
        if recent_files:
            # 获取最近运行信息
            latest_file = recent_files[0]
            status['last_run'] = datetime.fromtimestamp(
                latest_file.stat().st_mtime
            ).isoformat()
            
            # 分析成功率
            try:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    stats = data.get('metadata', {}).get('stats', {})
                    
                    total_leaves = stats.get('total_leaves', 0)
                    success_leaves = stats.get('success_leaves', 0)
                    
                    if total_leaves > 0:
                        status['success_rate'] = success_leaves / total_leaves * 100
                    
                    # 收集错误信息
                    failed_leaves = stats.get('failed_leaves', [])
                    failed_products = stats.get('failed_products', [])
                    
                    if failed_leaves:
                        status['recent_errors'].append({
                            'type': 'failed_leaves',
                            'count': len(failed_leaves),
                            'samples': failed_leaves[:5]
                        })
                    
                    if failed_products:
                        status['recent_errors'].append({
                            'type': 'failed_products', 
                            'count': len(failed_products),
                            'samples': failed_products[:5]
                        })
                        
            except Exception as e:
                self.logger.error(f"解析输出文件失败: {e}")
        
        # 检查是否正在运行
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('optimized_full_pipeline' in arg for arg in cmdline):
                    status['running'] = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return status
    
    def check_log_errors(self) -> List[str]:
        """检查日志中的错误"""
        errors = []
        log_file = Path(self.config['paths']['logs']) / 'opt-pipeline.log'
        
        if log_file.exists():
            # 读取最近1小时的日志
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '[ERROR]' in line:
                            # 解析时间戳
                            try:
                                timestamp_str = line.split(' ')[0]
                                timestamp = datetime.fromisoformat(timestamp_str)
                                
                                if timestamp > one_hour_ago:
                                    errors.append(line.strip())
                            except:
                                pass
            except Exception as e:
                self.logger.error(f"读取日志文件失败: {e}")
        
        return errors[-10:]  # 只返回最近10条错误
    
    def send_alert(self, alert_type: str, message: str, details: Dict[str, Any] = None):
        """发送告警"""
        if not self.config['monitor']['alert_webhook']:
            return
        
        payload = {
            'alert_type': alert_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        try:
            response = requests.post(
                self.config['monitor']['alert_webhook'],
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            self.logger.info(f"告警发送成功: {alert_type}")
        except Exception as e:
            self.logger.error(f"告警发送失败: {e}")
    
    def analyze_health(self) -> Dict[str, Any]:
        """分析健康状态"""
        # 收集各项指标
        resources = self.check_system_resources()
        pipeline_status = self.check_pipeline_status()
        recent_errors = self.check_log_errors()
        
        # 更新指标历史
        self.metrics['cpu_usage'].append(resources['cpu_percent'])
        self.metrics['memory_usage'].append(resources['memory_percent'])
        self.metrics['disk_usage'].append(resources['disk_percent'])
        self.metrics['active_threads'].append(resources['active_threads'])
        self.metrics['error_count'] = len(recent_errors)
        self.metrics['last_check'] = datetime.now()
        
        # 保持历史记录在合理范围内
        for key in ['cpu_usage', 'memory_usage', 'disk_usage', 'active_threads']:
            if len(self.metrics[key]) > 60:  # 保留最近60次检查
                self.metrics[key] = self.metrics[key][-60:]
        
        # 判断健康状态
        health_status = 'healthy'
        issues = []
        
        # CPU使用率检查
        avg_cpu = sum(self.metrics['cpu_usage'][-5:]) / min(5, len(self.metrics['cpu_usage']))
        if avg_cpu > 90:
            health_status = 'critical'
            issues.append(f"CPU使用率过高: {avg_cpu:.1f}%")
        elif avg_cpu > 70:
            health_status = 'warning'
            issues.append(f"CPU使用率较高: {avg_cpu:.1f}%")
        
        # 内存使用率检查
        avg_memory = sum(self.metrics['memory_usage'][-5:]) / min(5, len(self.metrics['memory_usage']))
        if avg_memory > 90:
            health_status = 'critical'
            issues.append(f"内存使用率过高: {avg_memory:.1f}%")
        elif avg_memory > 70:
            health_status = 'warning' if health_status == 'healthy' else health_status
            issues.append(f"内存使用率较高: {avg_memory:.1f}%")
        
        # 磁盘使用率检查
        if resources['disk_percent'] > 90:
            health_status = 'critical'
            issues.append(f"磁盘使用率过高: {resources['disk_percent']:.1f}%")
        
        # 错误率检查
        if self.metrics['error_count'] > 10:
            health_status = 'critical'
            issues.append(f"最近1小时错误过多: {self.metrics['error_count']}个")
        elif self.metrics['error_count'] > 5:
            health_status = 'warning' if health_status == 'healthy' else health_status
            issues.append(f"最近1小时有错误: {self.metrics['error_count']}个")
        
        # Pipeline状态检查
        if pipeline_status['last_run']:
            last_run_time = datetime.fromisoformat(pipeline_status['last_run'])
            time_since_last_run = datetime.now() - last_run_time
            
            if time_since_last_run > timedelta(hours=24):
                health_status = 'warning' if health_status == 'healthy' else health_status
                issues.append(f"超过24小时未运行")
            
            if pipeline_status['success_rate'] < 80:
                health_status = 'warning' if health_status == 'healthy' else health_status
                issues.append(f"成功率较低: {pipeline_status['success_rate']:.1f}%")
        
        return {
            'status': health_status,
            'issues': issues,
            'resources': resources,
            'pipeline': pipeline_status,
            'recent_errors': recent_errors,
            'metrics': {
                'avg_cpu': avg_cpu,
                'avg_memory': avg_memory,
                'error_count': self.metrics['error_count']
            }
        }
    
    def run_check(self):
        """运行健康检查"""
        self.logger.info("开始健康检查...")
        
        try:
            health_report = self.analyze_health()
            
            # 记录健康状态
            self.logger.info(f"健康状态: {health_report['status']}")
            
            if health_report['issues']:
                self.logger.warning(f"发现问题: {', '.join(health_report['issues'])}")
            
            # 发送告警
            if health_report['status'] == 'critical':
                self.send_alert(
                    'critical',
                    f"Pipeline健康状态严重: {', '.join(health_report['issues'])}",
                    health_report
                )
            elif health_report['status'] == 'warning':
                # 只在状态持续warning超过3次时才发送告警
                if hasattr(self, '_warning_count'):
                    self._warning_count += 1
                else:
                    self._warning_count = 1
                
                if self._warning_count >= 3:
                    self.send_alert(
                        'warning',
                        f"Pipeline健康状态警告: {', '.join(health_report['issues'])}",
                        health_report
                    )
            else:
                self._warning_count = 0
            
            # 保存健康报告
            report_file = Path(self.config['paths']['logs']) / 'health_report.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(health_report, f, ensure_ascii=False, indent=2, default=str)
            
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}", exc_info=True)
            self.send_alert('error', f"健康检查失败: {e}")
    
    def run_continuous(self):
        """持续运行健康检查"""
        interval = self.config['monitor']['health_check_interval']
        self.logger.info(f"开始持续健康监控，检查间隔: {interval}秒")
        
        while True:
            try:
                self.run_check()
                time.sleep(interval)
            except KeyboardInterrupt:
                self.logger.info("健康监控已停止")
                break
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}", exc_info=True)
                time.sleep(60)  # 错误后等待1分钟再重试


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TraceParts爬虫健康监控')
    parser.add_argument('--once', action='store_true', help='只运行一次检查')
    parser.add_argument('--interval', type=int, help='检查间隔（秒）')
    
    args = parser.parse_args()
    
    # 覆盖配置
    if args.interval:
        CONFIG['monitor']['health_check_interval'] = args.interval
    
    # 创建监控器
    monitor = HealthMonitor()
    
    if args.once:
        monitor.run_check()
    else:
        monitor.run_continuous()


if __name__ == '__main__':
    main() 