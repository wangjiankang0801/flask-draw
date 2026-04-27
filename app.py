# app.py
import time
import os
import base64
import re
import json
import requests
from flask import Flask, request, render_template_string, jsonify
from werkzeug.utils import secure_filename
from html_template import HTML_PAGE

app = Flask(__name__)

# 配置常量（从环境变量读取）
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

# 辅助函数：Catbox 上传
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

# 图像生成后的输出处理
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

# 核心图像生成逻辑（文生图 / 图生图）
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

# 大模型调用函数（智能优化用户输入）
def call_llm_for_optimization(user_prompt: str, mode: str):
    """
    调用大模型，返回优化后的参数。
    返回格式：{"optimized_prompt": str, "style": str, "size": int, "steps": int, "num": int}
    """
    if not ENABLE_LLM_OPT:
        return {"optimized_prompt": user_prompt, "style": "realistic", "size": 512, "steps": 30, "num": 1}
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

# Flask 路由
@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)

@app.route("/optimize", methods=["POST"])
def optimize():
    """接收原始提示词，返回大模型优化后的参数"""
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

@app.route("/generate", methods=["POST"])
def generate():
    """接收表单参数，调用绘图API并返回结果页面"""
    mode = request.form.get("mode")
    prompt = request.form.get("prompt")
    size = request.form.get("size")
    style = request.form.get("style")
    num = int(request.form.get("num", 1))
    steps = int(request.form.get("steps", 50))
    image_files = request.files.getlist("image_files") if mode == "image2image" else []

    if not prompt:
        return render_template_string(HTML_PAGE, error="提示词不能为空")
    try:
        results = generate_images(mode, prompt, int(size), num, style, steps, image_files)
        return render_template_string(HTML_PAGE, image_results=results)
    except Exception as e:
        return render_template_string(HTML_PAGE, error=f"生成失败: {e}")

# 启动应用
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)