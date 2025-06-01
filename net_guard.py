# -*- coding: utf-8 -*-
"""net_guard.py —— 网络异常计数与自动暂停

用法：
    from net_guard import register_fail, register_success
    try:
        ...  # 网络请求
        register_success()
    except Exception:
        register_fail()

逻辑：
1. 记录失败时间戳到 deque（滑动窗口）。
2. 超过阈值 (FAIL_THRESHOLD) 则暂停 PAUSE_SECONDS。
3. 成功访问时仅修剪旧失败记录，无需清零全局。
"""

import time
import collections
import threading
import logging

LOG = logging.getLogger("net_guard")

FAIL_WINDOW_SEC = 180       # 统计最近 3 分钟的失败
FAIL_THRESHOLD   = 5        # 连续失败阈值
PAUSE_SECONDS    = 120      # 暂停时间

_failure_times: "collections.deque[float]" = collections.deque(maxlen=1000)
_lock = threading.Lock()
_last_pause_time = 0.0  # epoch 秒


def _trim(now: float):
    """移除窗口之外的时间戳"""
    while _failure_times and now - _failure_times[0] > FAIL_WINDOW_SEC:
        _failure_times.popleft()


def register_fail():
    """记录一次失败，必要时暂停"""
    global _last_pause_time
    now = time.time()
    with _lock:
        _trim(now)
        _failure_times.append(now)

        # 冷却期：暂停后的一半周期内不再立即触发
        if now - _last_pause_time < PAUSE_SECONDS / 2:
            return

        if len(_failure_times) >= FAIL_THRESHOLD:
            LOG.warning(
                f"🌐 连续失败 {len(_failure_times)} 次 (窗口 {FAIL_WINDOW_SEC}s)，暂停 {PAUSE_SECONDS}s …"
            )
            _last_pause_time = now
    # 锁外 sleep，避免阻塞其他线程
    time.sleep(PAUSE_SECONDS)


def register_success():
    """成功访问后修剪旧记录"""
    now = time.time()
    with _lock:
        _trim(now)
        # 不清空 deque，让历史失败自然过期 