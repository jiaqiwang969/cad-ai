# TraceParts 自动 CAD 下载器

## 项目概述

**终极自动化解决方案**：全自动 TraceParts CAD 文件下载，集成隐身浏览、GPT-4o 验证码识别、智能格式选择和文件管理。

🎯 **一键下载**：`make test-10` 即可完成从登录到文件保存的全流程自动化。

## 核心功能

- 🥷 **隐身浏览器**：绕过自动化检测，模拟真实用户行为
- 🤖 **GPT-4o OCR**：高精度验证码自动识别（95%+ 准确率）
- 📁 **智能格式选择**：自动选择 STEP AP214、STL、IGES 等常用格式
- 💾 **自动文件管理**：下载文件直接保存至 `results/downloads/`
- 🔄 **失败重试**：验证码错误时自动重新识别并重试

## 快速开始

### 1. 安装依赖
```bash
make install
```

### 2. 配置账号（可选）
```bash
export TRACEPARTS_EMAIL=your@email.com
export TRACEPARTS_PASSWORD=yourpassword
```

### 3. 自动下载 CAD 文件
```bash
make test-10
```

### 4. 自定义产品下载
```bash
TRACEPARTS_PRODUCT_URL=https://www.traceparts.cn/en/product/your-product make test-10
```

## 项目结构

```
50-爬虫01/
├── test/
│   ├── 10-test_product_cad_download.py    # 🎯 终极自动下载脚本
│   ├── legacy/                            # 开发历程脚本存档
│   │   ├── 11i-stealth_cad_downloader.py # 隐身浏览器核心
│   │   ├── k-auto_captcha_download.py    # GPT-4o 验证码识别
│   │   └── README.md                      # 演进历程说明
│   ├── 01-09-*.py                        # 早期探索脚本
│   └── ...
├── utils/
│   └── captcha_solver.py                 # GPT-4o OCR 识别引擎
├── results/
│   └── downloads/                         # 自动下载的 CAD 文件
└── requirements.txt                       # 精简版依赖包
```

## 工作原理

1. **隐身登录**：使用高级反检测技术登录 TraceParts
2. **页面导航**：自动跳转到指定产品页面
3. **格式选择**：智能选择最优 CAD 文件格式
4. **验证码识别**：GPT-4o 实时 OCR 识别并填写
5. **触发下载**：模拟用户点击操作启动下载
6. **文件保存**：监听下载事件，自动保存到本地

## 技术架构

### 核心组件

- **Playwright + playwright-stealth**：隐身浏览器自动化
- **GPT-4o Vision API**：验证码图像识别
- **OpenCV + Pillow**：图像处理与验证码区域定位
- **动态模块加载**：灵活复用 legacy 代码组件

### 验证码识别流程

```
页面截图 → 刷新图标定位 → 验证码区域裁剪 → GPT-4o OCR → 结果填写
     ↓
如识别错误 → 重新OCR（告知上次错误） → 重试填写 → 重新下载
```

## 可用命令

| 命令 | 说明 |
|------|------|
| `make install` | 安装项目依赖包 |
| `make test-10` | 🎯 **运行终极自动 CAD 下载** |
| `make test-01` ~ `make test-09` | 早期探索功能测试 |
| `make verify` | 快速验证 API 连接 |
| `make check` | 检查依赖包状态 |
| `make list` | 列出测试文件 |
| `make results` | 查看下载结果文件 |
| `make clean` | 清理临时文件 |
| `make help` | 显示帮助信息 |

## 配置选项

### 环境变量

```bash
# TraceParts 账号（必填）
TRACEPARTS_EMAIL=your@email.com
TRACEPARTS_PASSWORD=yourpassword

# 自定义产品 URL（可选，默认有示例产品）
TRACEPARTS_PRODUCT_URL=https://www.traceparts.cn/en/product/...

# GPT-4o API 配置（已内置，可自定义）
GPT4O_API_KEY=sk-...
GPT4O_BASE_URL=https://ai.pumpkinai.online/v1
```

### 格式优先级

脚本自动按以下优先级选择 CAD 格式：
1. STEP AP214
2. STEP AP203  
3. STL
4. IGES
5. SOLIDWORKS
6. Parasolid

## 下载示例

```bash
$ make test-10
🎯 运行测试 10: 终极自动 CAD 下载...
🔐 开始快速隐身登录...
✅ 登录成功！
选择格式: STEP AP214
🤖 初始化GPT-4o验证码识别器...
✅ 验证码识别成功 (GPT-4o): VZLA
📝 找到验证码输入框，准备填入识别结果
✅ 已向定位到的输入框填入: VZLA
🔽 尝试点击下载按钮...
✅ 找到下载按钮并点击
💾 下载完成: /path/to/results/downloads/681592.step
🎉 脚本结束，可在 results/downloads 查看文件。
```

## 依赖包

精简版核心依赖：

```
# Web 自动化
playwright>=1.44.0
playwright-stealth>=1.0.6

# HTTP 请求 (GPT-4o API)  
requests>=2.28.0

# 图像处理与 OCR
opencv-python>=4.8.0
pillow>=10.0.0
numpy>=1.21.0

# 机器学习 (备用 TrOCR 支持)
transformers>=4.20.0
torch>=1.12.0
```

## 故障排除

### 常见问题

1. **登录失败**
   - 检查账号密码是否正确
   - 确认网络可以访问 TraceParts

2. **验证码识别失败**
   - 检查 GPT-4o API 配置
   - 查看 `results/captcha_debug/` 目录下的调试图片

3. **下载失败**
   - 确认产品 URL 有效
   - 检查 `results/downloads/` 目录权限

4. **浏览器检测**
   - 脚本已集成高级反检测，如仍被检测可查看 legacy 脚本调优

### 调试模式

编辑 `test/10-test_product_cad_download.py`，设置：
```python
solver = CaptchaSolver(debug=True, ocr_method="gpt4o")
```

## 开发历程

本项目经历了从基础爬虫到终极自动化的完整演进：

- **阶段 1**：基础 API 测试和网页爬取（01-09）
- **阶段 2**：登录与隐身浏览技术（11 系列）
- **阶段 3**：验证码识别与处理（12-13 系列）  
- **阶段 4**：GPT-4o 集成与完整自动化（k 系列）
- **阶段 5**：最终整合与优化（test/10）

详细演进过程见 `test/legacy/README.md`。

## 许可证

MIT License 