# Legacy Scripts

本目录包含在开发终极自动 CAD 下载脚本过程中的探索和实验性代码。

## 演进历程

### 阶段 1: 登录与隐身浏览 (11-系列)
- `11-test_login_and_session.py` - 基础登录和 Cookie 保存
- `11b-test_manual_login.py` - 手动登录测试
- `11c-test_login_simple.py` - 简化登录流程
- `11d-test_login_and_navigate.py` - 登录后页面导航
- `11e-test_stealth_cad_download.py` - 早期隐身下载尝试
- `11f-test_real_chrome.py` - 真实 Chrome 浏览器测试
- `11g-diagnose_traceparts_detection.py` - TraceParts 检测机制诊断
- `11h-advanced_cad_access.py` - 高级 CAD 访问分析
- `11i-stealth_cad_downloader.py` - **核心隐身浏览器实现** (被 test/10 引用)
- `11j-stealth_cad_downloader_captcha.py` - 隐身浏览器 + 验证码识别

### 阶段 2: 验证码识别与处理 (12-系列)
- `12-test_capture_captcha.py` - 验证码图片捕获
- `12h-auto_captcha_download.py` - 自动验证码识别下载
- `12k-extract_captcha_region.py` - 精确验证码区域提取

### 阶段 3: OCR 优化 (13-系列)
- `13-test_ocr_captcha.py` - OCR 验证码识别测试

### 阶段 4: 最终整合 (字母系列)
- `j-auto_captcha_download.py` - 早期自动验证码下载尝试
- `k-auto_captcha_download.py` - **GPT-4o 验证码识别完整实现** (最接近最终版)
- `l-extract_captcha.py` - 极简验证码提取

## 最终成果

所有这些探索最终整合为 `test/10-test_product_cad_download.py`，实现了：
- 隐身浏览器 (基于 11i)
- GPT-4o 验证码识别 (基于 k 脚本)
- 自动化下载流程
- 文件自动保存

## 保留原因

这些脚本保留用于：
1. 技术参考 - 了解不同方法的尝试过程
2. 调试支持 - 当主脚本出现问题时可回溯分析
3. 功能扩展 - 为未来增强功能提供代码基础
4. 学习价值 - 展示从概念到实现的完整开发历程 