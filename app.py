import time
import os
import base64
import re
import json
import requests
from flask import Flask, request, render_template_string, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ===================================================================
# 配置常量（从环境变量读取）
# ===================================================================
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise RuntimeError("请设置环境变量 API_KEY")

TEXT2IMAGE_URL = "https://api.gptsapi.net/api/v3/openai/gpt-image-2-plus/text-to-image"
IMAGE_EDIT_URL = "https://api.gptsapi.net/api/v3/openai/gpt-image-2-plus/image-edit"
CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"

# 大模型 API 配置
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://qianfan.baidubce.com/v2/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-v3.1-250821")
ENABLE_LLM_OPT = bool(LLM_API_KEY)

DEFAULT_NEGATIVE_PROMPT = (
    "low quality, blurry, distorted, deformed, bad anatomy, "
    "mutated hands, extra fingers, missing fingers, bad proportions, "
    "text, watermark, signature, logo"
)

# ===================================================================
# 辅助函数：Catbox 上传
# ===================================================================
def upload_bytes_to_catbox(img_bytes, filename="generated.png"):
    files = {"fileToUpload": (filename, img_bytes, "image/png")}
    data = {"reqtype": "fileupload"}
    try:
        resp = requests.post(CATBOX_UPLOAD_URL, files=files, data=data, timeout=60)
        if resp.status_code != 200:
            print(f"catbox 备份上传失败: {resp.text}")
            return None
        url = resp.text.strip()
        if url.startswith("http"):
            return url
        else:
            print(f"catbox 返回异常: {url}")
            return None
    except Exception as e:
        print(f"备份上传异常: {e}")
        return None

def upload_to_catbox(file):
    content = file.read()
    file.seek(0)
    original_size = len(content)
    if original_size > 1 * 1024 * 1024:
        try:
            from PIL import Image
            from io import BytesIO
            img = Image.open(BytesIO(content))
            img.thumbnail((1024, 1024))
            buf = BytesIO()
            img.save(buf, format='PNG' if img.mode == 'RGBA' else 'JPEG', quality=85)
            content = buf.getvalue()
            file.filename = file.filename.rsplit('.', 1)[0] + '.jpg'
            print(f"图片已压缩，{original_size/1024:.1f}KB -> {len(content)/1024:.1f}KB")
        except ImportError:
            print("PIL 未安装，上传原图")
    files = {"fileToUpload": (file.filename, content, file.content_type)}
    data = {"reqtype": "fileupload"}
    try:
        resp = requests.post(CATBOX_UPLOAD_URL, files=files, data=data, timeout=60)
        resp.raise_for_status()
        url = resp.text.strip()
        if url.startswith("http"):
            return url
        else:
            raise Exception(f"返回格式异常: {url}")
    except Exception as e:
        print(f"catbox 上传异常: {e}")
        raise

# ===================================================================
# 图像生成后的输出处理
# ===================================================================
def process_generated_output(raw_output):
    display_url = raw_output
    if display_url and not display_url.startswith('data:') and not display_url.startswith('http'):
        display_url = "data:image/png;base64," + display_url
    img_bytes = None
    if raw_output.startswith('data:image/png;base64,'):
        b64_data = raw_output[len('data:image/png;base64,'):]
        img_bytes = base64.b64decode(b64_data)
    elif not raw_output.startswith('http'):
        img_bytes = base64.b64decode(raw_output)
    else:
        try:
            resp = requests.get(raw_output, timeout=30)
            resp.raise_for_status()
            img_bytes = resp.content
        except Exception as e:
            print(f"下载生成图片失败: {e}")
    catbox_url = None
    if img_bytes:
        catbox_url = upload_bytes_to_catbox(img_bytes, f"generated_{int(time.time())}.png")
    return {"display_url": display_url, "catbox_url": catbox_url}

# ===================================================================
# 核心图像生成逻辑（文生图 / 图生图）
# ===================================================================
def generate_images(mode, prompt, size, num, style, steps, image_files):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload_base = {
        "output_format": "png",
        "size": f"{size}x{size}",
        "num_outputs": num,
        "style": style,
        "steps": steps,
        "negative_prompt": DEFAULT_NEGATIVE_PROMPT
    }
    if mode == "text2image":
        url = TEXT2IMAGE_URL
        payload = {"prompt": prompt, **payload_base}
        results = []
        for i in range(num):
            print(f"尝试生成第 {i+1} 张图片（文生图），prompt: {prompt}")
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()["data"]
                get_url = data["urls"]["get"]
                while True:
                    r = requests.get(get_url, headers=headers)
                    r.raise_for_status()
                    j = r.json()
                    status = j["data"]["status"]
                    if status == "completed":
                        output = j["data"]["outputs"][0]
                        result_item = process_generated_output(output)
                        results.append(result_item)
                        break
                    elif status == "failed":
                        error_detail = j.get("data", {}).get("error") or j.get("error") or "未知错误"
                        raise Exception(f"生成失败: {error_detail}")
                    time.sleep(2)
            except Exception as e:
                print(f"文生图第 {i+1} 张出错: {e}")
                raise
        return results
    else:  # image2image
        if not image_files:
            raise Exception("请上传至少一张参考图片")
        image_url_list = []
        for f in image_files:
            f.seek(0)
            img_url = upload_to_catbox(f)
            image_url_list.append(img_url)
        payload = {"prompt": prompt, "images": image_url_list, **payload_base}
        print(f"发起图生图请求，prompt: {prompt}, images: {image_url_list}")
        try:
            response = requests.post(IMAGE_EDIT_URL, json=payload, headers=headers, timeout=60)
        except Exception as e:
            print(f"图生图 POST 请求失败: {e}")
            raise
        if response.status_code != 200:
            print(f"错误响应: {response.text}")
            response.raise_for_status()
        data = response.json().get("data")
        if not data:
            raise Exception(f"响应中没有 data: {response.json()}")
        get_url = data["urls"]["get"]
        while True:
            r = requests.get(get_url, headers=headers)
            r.raise_for_status()
            j = r.json()
            status = j.get("data", {}).get("status")
            if status == "completed":
                outputs = j["data"]["outputs"]
                results = []
                for output in outputs:
                    result_item = process_generated_output(output)
                    results.append(result_item)
                return results
            elif status == "failed":
                error_detail = j.get("data", {}).get("error") or j.get("error") or "未知错误"
                raise Exception(f"生成失败: {error_detail}")
            time.sleep(2)

# ===================================================================
# 大模型调用函数（智能优化用户输入）
# ===================================================================
def call_llm_for_optimization(user_prompt: str, mode: str):
    """
    调用大模型，返回优化后的参数。
    返回格式：{"optimized_prompt": str, "style": str, "size": int, "steps": int, "num": int}
    """
    system_prompt = f"""你是一个专业的绘画提示词优化助手。
用户输入一句大白话，你需要将它转换成适合高质量图像生成的参数。
当前模式：{mode}（text2image 或 image2image）。

请严格按照以下JSON格式输出，不要有任何额外文字：
{{
    "optimized_prompt": "优化后的英文或中文绘画描述，需结构清晰、细节丰富",
    "style": "一种风格，可选值：realistic, anime, digital-painting, oil-painting, pixel-art",
    "size": 尺寸数字，仅允许 256, 512, 1024 中的一个，
    "steps": 步数，仅允许 30, 50, 100 中的一个，
    "num": 数量，仅允许 1, 2, 3 中的一个
}}

示例：
用户输入："一只可爱的猫"
输出：
{{
    "optimized_prompt": "一只可爱的猫，毛茸茸的，大眼睛，好奇的表情，柔和的自然光，高细节，4K",
    "style": "realistic",
    "size": 512,
    "steps": 50,
    "num": 1
}}

如果是图生图模式，优化后的提示词应强调保持参考图构图、增强细节。"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}"
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 400
    }
    try:
        resp = requests.post(LLM_BASE_URL, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"]
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            params = json.loads(json_match.group())
            # 校验并修正值
            allowed_styles = ["realistic", "anime", "digital-painting", "oil-painting", "pixel-art"]
            if params.get("style") not in allowed_styles:
                params["style"] = "realistic"
            if params.get("size") not in [256, 512, 1024]:
                params["size"] = 512
            if params.get("steps") not in [30, 50, 100]:
                params["steps"] = 50
            if params.get("num") not in [1, 2, 3]:
                params["num"] = 1
            return params
        else:
            print("大模型返回未包含JSON，使用原始prompt")
            return {"optimized_prompt": user_prompt, "style": "realistic", "size": 512, "steps": 30, "num": 1}
    except Exception as e:
        print(f"调用大模型失败：{e}，使用原始参数")
        return {"optimized_prompt": user_prompt, "style": "realistic", "size": 512, "steps": 30, "num": 1}

# ===================================================================
# 路由：前端页面（含完整交互逻辑）
# ===================================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>AI画图工坊 · 智能优化</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #f5f7fb;
            margin: 0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .card {
            max-width: 760px;
            width: 100%;
            background: white;
            border-radius: 40px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.08);
            padding: 28px 32px 36px;
        }
        h2 { font-size: 1.8rem; font-weight: 700; margin: 0 0 4px 0; color: #0f172a; }
        .sub { color: #5b6e8c; margin-bottom: 24px; font-size: 0.9rem; border-left: 3px solid #cbd5e1; padding-left: 12px; }
        .ai-placeholder { min-height: 64px; margin: 8px 0 12px 0; }
        .ai-note { background: #e6f7ec; padding: 12px 18px; border-radius: 24px; font-size: 0.85rem; color: #166534; border-left: 4px solid #22c55e; margin: 0; }
        .hidden { display: none; }
        .toggle-row {
            display: flex; align-items: center; justify-content: space-between;
            background: #f1f5f9; padding: 12px 20px; border-radius: 60px; margin-bottom: 28px;
        }
        .toggle-label { font-weight: 600; font-size: 1rem; color: #0f172a; }
        .toggle-switch { position: relative; display: inline-block; width: 52px; height: 28px; }
        .toggle-switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
            background-color: #cbd5e1; transition: 0.2s; border-radius: 28px;
        }
        .slider:before {
            position: absolute; content: ""; height: 24px; width: 24px; left: 2px; bottom: 2px;
            background-color: white; transition: 0.2s; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }
        input:checked + .slider { background-color: #86efac; }
        input:checked + .slider:before { transform: translateX(24px); }
        .mode-buttons {
            display: flex; gap: 24px; margin-bottom: 24px;
            background: #f8fafc; padding: 8px 16px; border-radius: 60px; width: fit-content;
        }
        .mode-buttons label { display: flex; align-items: center; gap: 8px; font-weight: 500; cursor: pointer; }
        .params-panel { background: #f8fafc; border-radius: 32px; padding: 18px 24px; margin-bottom: 24px; }
        .param-row { display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 16px; }
        .param-group { flex: 1; min-width: 120px; }
        .param-group label { display: block; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; color: #475569; margin-bottom: 5px; }
        select, input { width: 100%; padding: 8px 12px; border-radius: 28px; border: 1px solid #cbd5e1; background: white; font-size: 0.9rem; }
        textarea { width: 100%; padding: 12px 16px; border-radius: 28px; border: 1px solid #cbd5e1; font-family: inherit; font-size: 0.95rem; resize: vertical; margin-bottom: 18px; }
        .upload-section { background: #fef9e3; border-radius: 28px; padding: 16px 20px; margin-bottom: 18px; display: none; }
        .upload-section.active { display: block; }
        .preview-container { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; }
        .preview-img { width: 80px; height: 80px; object-fit: cover; border-radius: 16px; border: 1px solid #ddd; }
        .btn-generate { background: #3b82f6; width: 100%; padding: 14px; font-size: 1.1rem; font-weight: 600; border: none; border-radius: 44px; color: white; cursor: pointer; margin-top: 6px; }
        .btn-generate:hover { background: #2563eb; }
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4);
            backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center;
            z-index: 1000; visibility: hidden; opacity: 0; transition: 0.2s;
        }
        .modal-overlay.active { visibility: visible; opacity: 1; }
        .modal-card { background: white; max-width: 500px; width: 90%; border-radius: 48px; padding: 28px; box-shadow: 0 25px 40px rgba(0,0,0,0.2); }
        .modal-card h3 { margin-top: 0; font-size: 1.6rem; font-weight: 600; }
        .modal-params { background: #f1f5f9; border-radius: 28px; padding: 18px; margin: 20px 0; }
        .button-group { display: flex; gap: 12px; justify-content: flex-end; }
        .btn-confirm { background: #86efac; border: none; padding: 8px 24px; border-radius: 40px; font-weight: 600; cursor: pointer; }
        .btn-cancel { background: #cbd5e1; border: none; padding: 8px 24px; border-radius: 40px; font-weight: 600; cursor: pointer; }
        .footnote { font-size: 0.7rem; text-align: center; color: #94a3b8; margin-top: 24px; }
        .param-hidden { display: none; }
        .loading-indicator { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.7); color: white; padding: 12px 24px; border-radius: 40px; z-index: 2000; }
    </style>
</head>
<body>
<div class="card">
    <h2>🎨 AI画图工坊</h2>
    <div class="sub">自然语言绘图 · 智能增强</div>

    <div class="ai-placeholder">
        <div id="aiNote" class="ai-note hidden">✨ 已启用 DeepSeek-V3 智能优化：您的描述会被自动转换为高质量绘画参数（风格/尺寸/步数等将自动适配）。</div>
    </div>

    <div class="toggle-row">
        <span class="toggle-label">✨ 启用 DeepSeek-V3 优化</span>
        <label class="toggle-switch">
            <input type="checkbox" id="aiOptimizeToggle">
            <span class="slider"></span>
        </label>
    </div>

    <div class="mode-buttons">
        <label><input type="radio" name="mode" value="text2image" checked> 🔘 文生图</label>
        <label><input type="radio" name="mode" value="image2image"> 🔘 图生图</label>
    </div>

    <div id="paramsPanel" class="params-panel">
        <div class="param-row">
            <div class="param-group"><label>📐 尺寸</label><select id="sizeSelect"><option value="256">256x256</option><option value="512" selected>512x512</option><option value="1024">1024x1024</option></select></div>
            <div class="param-group"><label>🎨 风格</label><select id="styleSelect"><option value="realistic">写实</option><option value="anime">二次元</option><option value="digital-painting">数字绘画</option><option value="oil-painting">油画</option><option value="pixel-art">像素风</option></select></div>
        </div>
        <div class="param-row">
            <div class="param-group"><label>🔢 数量</label><select id="numSelect"><option value="1">1张</option><option value="2">2张</option><option value="3">3张</option></select></div>
            <div class="param-group"><label>⚙️ 细节步数</label><select id="stepsSelect"><option value="30">30 - 快速</option><option value="50" selected>50 - 标准</option><option value="100">100 - 高细节</option></select></div>
        </div>
    </div>

    <div id="uploadArea" class="upload-section">
        <div>📷 上传参考图片（可多张）</div>
        <input type="file" id="imageInput" accept="image/*" multiple>
        <div id="previewContainer" class="preview-container"></div>
    </div>

    <textarea id="promptInput" rows="4" placeholder="描述你想画的内容，例如：一只穿着宇航服的柴犬，在火星上，赛博朋克风格，电影光效"></textarea>

    <button id="generateBtn" class="btn-generate">✨ 生成图片</button>
    <div class="footnote">* 开启AI优化后，点击生成会展示优化后的参数确认框</div>
</div>

<div id="confirmModal" class="modal-overlay">
    <div class="modal-card">
        <h3>📝 是否生成以下内容？</h3>
        <div class="modal-params">
            <p><strong>✨ 优化后提示词：</strong><br><span id="optPromptText">—</span></p>
            <p><strong>📏 尺寸：</strong> <span id="optSize">512x512</span> &nbsp;|&nbsp;
               <strong>🎨 风格：</strong> <span id="optStyle">写实</span> &nbsp;|&nbsp;
               <strong>🔢 数量：</strong> <span id="optNum">1</span> &nbsp;|&nbsp;
               <strong>⚙️ 步数：</strong> <span id="optSteps">50</span>
            </p>
        </div>
        <div class="button-group">
            <button id="modalCancelBtn" class="btn-cancel">取消</button>
            <button id="modalConfirmBtn" class="btn-confirm">确认生成</button>
        </div>
    </div>
</div>
<div id="loadingIndicator" class="loading-indicator">⏳ 生成中，请稍候...</div>

<script>
    // DOM 元素
    const aiToggle = document.getElementById('aiOptimizeToggle');
    const aiNoteDiv = document.getElementById('aiNote');
    const paramsPanel = document.getElementById('paramsPanel');
    const modeRadios = document.querySelectorAll('input[name="mode"]');
    const uploadArea = document.getElementById('uploadArea');
    const imageInput = document.getElementById('imageInput');
    const previewContainer = document.getElementById('previewContainer');
    const generateBtn = document.getElementById('generateBtn');
    const modal = document.getElementById('confirmModal');
    const modalCancel = document.getElementById('modalCancelBtn');
    const modalConfirm = document.getElementById('modalConfirmBtn');
    const optPromptSpan = document.getElementById('optPromptText');
    const optSizeSpan = document.getElementById('optSize');
    const optStyleSpan = document.getElementById('optStyle');
    const optNumSpan = document.getElementById('optNum');
    const optStepsSpan = document.getElementById('optSteps');
    const loadingIndicator = document.getElementById('loadingIndicator');

    let selectedFiles = [];
    let currentOptimizedParams = null;  // 存储优化后的参数，用于确认生成

    // 预览相关
    function updatePreview() {
        previewContainer.innerHTML = '';
        selectedFiles.forEach((file, idx) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.className = 'preview-img';
                const delBtn = document.createElement('button');
                delBtn.innerText = '✕';
                delBtn.style.position = 'relative';
                delBtn.style.marginLeft = '-24px';
                delBtn.style.background = 'rgba(0,0,0,0.5)';
                delBtn.style.color = 'white';
                delBtn.style.border = 'none';
                delBtn.style.borderRadius = '20px';
                delBtn.style.cursor = 'pointer';
                delBtn.onclick = () => {
                    selectedFiles.splice(idx, 1);
                    updatePreview();
                    syncFileInput();
                };
                const wrapper = document.createElement('div');
                wrapper.style.position = 'relative';
                wrapper.appendChild(img);
                wrapper.appendChild(delBtn);
                previewContainer.appendChild(wrapper);
            };
            reader.readAsDataURL(file);
        });
    }
    function syncFileInput() {
        const dt = new DataTransfer();
        selectedFiles.forEach(f => dt.items.add(f));
        imageInput.files = dt.files;
    }
    imageInput.addEventListener('change', (e) => {
        const newFiles = Array.from(e.target.files);
        newFiles.forEach(file => {
            if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                selectedFiles.push(file);
            }
        });
        updatePreview();
        syncFileInput();
    });

    // 模式切换
    function toggleUploadArea() {
        const mode = document.querySelector('input[name="mode"]:checked').value;
        if (mode === 'image2image') uploadArea.classList.add('active');
        else uploadArea.classList.remove('active');
    }
    modeRadios.forEach(radio => radio.addEventListener('change', toggleUploadArea));
    toggleUploadArea();

    // AI 开关UI
    function updateAIUI() {
        const enabled = aiToggle.checked;
        if (enabled) {
            aiNoteDiv.classList.remove('hidden');
            paramsPanel.classList.add('param-hidden');
        } else {
            aiNoteDiv.classList.add('hidden');
            paramsPanel.classList.remove('param-hidden');
        }
    }
    aiToggle.addEventListener('change', updateAIUI);
    updateAIUI();

    // 通用获取表单数据（不含文件）
    function getFormData() {
        const mode = document.querySelector('input[name="mode"]:checked').value;
        const prompt = document.getElementById('promptInput').value.trim();
        if (!prompt) { alert("请输入提示词"); return null; }
        const size = document.getElementById('sizeSelect')?.value || "512";
        const style = document.getElementById('styleSelect')?.value || "realistic";
        const num = document.getElementById('numSelect')?.value || "1";
        const steps = document.getElementById('stepsSelect')?.value || "50";
        return { mode, prompt, size, style, num, steps };
    }

    // 显示加载动画
    function showLoading() { loadingIndicator.style.display = 'block'; }
    function hideLoading() { loadingIndicator.style.display = 'none'; }

    // 生成图片（最终提交）
    async function submitGenerate(params) {
        const formData = new FormData();
        formData.append('mode', params.mode);
        formData.append('prompt', params.prompt);
        formData.append('size', params.size);
        formData.append('style', params.style);
        formData.append('num', params.num);
        formData.append('steps', params.steps);
        for (let file of selectedFiles) {
            formData.append('image_files', file);
        }
        showLoading();
        try {
            const resp = await fetch('/generate', { method: 'POST', body: formData });
            const html = await resp.text();
            // 替换整个页面以显示结果
            document.open();
            document.write(html);
            document.close();
        } catch (err) {
            alert("生成失败：" + err);
            hideLoading();
        }
    }

    // 普通模式：直接生成
    async function normalGenerate() {
        const data = getFormData();
        if (!data) return;
        await submitGenerate(data);
    }

    // AI优化模式：先获取优化参数，弹窗确认后再生成
    async function aiOptimizeAndConfirm() {
        const data = getFormData();
        if (!data) return;
        showLoading();
        try {
            const resp = await fetch('/optimize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: data.prompt, mode: data.mode })
            });
            const opt = await resp.json();
            if (!opt.success) throw new Error(opt.error);
            currentOptimizedParams = {
                mode: data.mode,
                prompt: opt.optimized_prompt,
                size: opt.size,
                style: opt.style,
                num: opt.num,
                steps: opt.steps
            };
            // 填充弹窗
            optPromptSpan.innerText = currentOptimizedParams.prompt;
            optSizeSpan.innerText = currentOptimizedParams.size;
            const styleMap = { 'realistic':'写实', 'anime':'二次元', 'digital-painting':'数字绘画', 'oil-painting':'油画', 'pixel-art':'像素风' };
            optStyleSpan.innerText = styleMap[currentOptimizedParams.style] || currentOptimizedParams.style;
            optNumSpan.innerText = currentOptimizedParams.num;
            optStepsSpan.innerText = currentOptimizedParams.steps;
            modal.classList.add('active');
            hideLoading();
        } catch (err) {
            alert("优化失败：" + err);
            hideLoading();
        }
    }

    // 生成按钮点击处理
    generateBtn.addEventListener('click', () => {
        if (aiToggle.checked) {
            aiOptimizeAndConfirm();
        } else {
            normalGenerate();
        }
    });

    // 弹窗按钮
    modalCancel.addEventListener('click', () => { modal.classList.remove('active'); });
    modalConfirm.addEventListener('click', async () => {
        modal.classList.remove('active');
        if (currentOptimizedParams) {
            await submitGenerate(currentOptimizedParams);
        } else {
            alert("优化参数丢失，请重试");
        }
    });
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('active'); });
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)

# ===================================================================
# API 路由：优化参数
# ===================================================================
@app.route("/optimize", methods=["POST"])
def optimize():
    if not ENABLE_LLM_OPT:
        return jsonify({"success": False, "error": "大模型未配置"}), 400
    data = request.get_json()
    prompt = data.get("prompt", "").strip()
    mode = data.get("mode", "text2image")
    if not prompt:
        return jsonify({"success": False, "error": "提示词不能为空"}), 400
    try:
        opt = call_llm_for_optimization(prompt, mode)
        return jsonify({
            "success": True,
            "optimized_prompt": opt["optimized_prompt"],
            "style": opt["style"],
            "size": str(opt["size"]),
            "steps": opt["steps"],
            "num": opt["num"]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ===================================================================
# API 路由：生成图片（最终）
# ===================================================================
@app.route("/generate", methods=["POST"])
def generate():
    mode = request.form.get("mode")
    prompt = request.form.get("prompt")
    size = request.form.get("size")
    style = request.form.get("style")
    num = int(request.form.get("num", 1))
    steps = int(request.form.get("steps", 50))
    image_files = request.files.getlist("image_files") if mode == "image2image" else []

    if not prompt:
        return render_template_string(HTML_PAGE, error="提示词不能为空", enable_llm=ENABLE_LLM_OPT)
    try:
        results = generate_images(mode, prompt, int(size), num, style, steps, image_files)
        return render_template_string(HTML_PAGE, image_results=results, enable_llm=ENABLE_LLM_OPT)
    except Exception as e:
        return render_template_string(HTML_PAGE, error=f"生成失败: {e}", enable_llm=ENABLE_LLM_OPT)

# ===================================================================
# 启动 Flask 应用
# ===================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
