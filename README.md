# 🎨 AI画图工坊

基于 Flask 的 AI 图像生成应用，支持文生图和图生图，集成小米 MiMo 大模型智能优化提示词。

## ✨ 功能特性

- **文生图**：输入文字描述，AI 生成创意图片
- **图生图**：上传参考图片，AI 基于参考图进行二次创作
- **AI 智能优化**：集成小米 MiMo 大模型，自动优化你的提示词
- **多种风格**：写实、二次元、数字绘画、油画、像素风
- **历史记录**：自动保存生成记录，最多保留 50 条
- **永久链接**：图片自动上传到 Catbox，生成永久访问链接
- **图片放大**：点击图片可全屏查看
- **响应式设计**：完美适配手机和桌面端

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 设置环境变量

```bash
# Windows
set API_KEY=你的图片生成API密钥
set LLM_API_KEY=你的MiMo API密钥

# Linux/Mac
export API_KEY=你的图片生成API密钥
export LLM_API_KEY=你的MiMo API密钥
```

### 3. 运行

```bash
python app.py
```

访问 http://localhost:8080 即可使用。

## 🔧 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `API_KEY` | 图片生成 API 密钥（必填） | - |
| `LLM_API_KEY` | 小米 MiMo API 密钥 | 内置默认值 |
| `LLM_BASE_URL` | 大模型 API 地址 | `https://token-plan-cn.xiaomimimo.com/v1/chat/completions` |
| `LLM_MODEL` | 大模型名称 | `mimo-v2.5-pro` |
| `PORT` | 服务端口 | `8080` |

## 📁 项目结构

```
flask-draw-new/
├── app.py              # Flask 路由和主程序
├── config.py           # 配置文件
├── deepseek.py         # 大模型调用（小米 MiMo）
├── image2.py           # 图像生成核心逻辑
├── history_manager.py  # 历史记录管理
├── html_template.py    # 前端页面模板
├── __init__.py         # Python 包标识
├── requirements.txt    # 依赖列表
├── Procfile            # 部署配置
├── .gitignore          # Git 忽略规则
└── README.md           # 项目说明
```

## 🌐 部署到 Heroku

```bash
heroku create your-app-name
heroku config:set API_KEY=你的密钥
heroku config:set LLM_API_KEY=你的密钥
git push heroku main
```

## 📄 License

MIT
