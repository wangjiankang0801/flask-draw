# image2.py
import time
import base64
import requests
from config import (
    API_KEY,
    TEXT2IMAGE_URL,
    IMAGE_EDIT_URL,
    DEFAULT_NEGATIVE_PROMPT,
)


import uuid
import os

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)


def upload_to_imgbb(file):
    """上传图片到 imgbb 免费图床，返回公网可访问的URL"""
    import base64

    content = file.read()
    file.seek(0)

    # 压缩大图
    if len(content) > 5 * 1024 * 1024:
        try:
            from PIL import Image
            from io import BytesIO
            img = Image.open(BytesIO(content))
            img.thumbnail((1024, 1024))
            buf = BytesIO()
            img.save(buf, format='PNG' if img.mode == 'RGBA' else 'JPEG', quality=85)
            content = buf.getvalue()
            print(f"图片已压缩到 {len(content)/1024:.1f}KB")
        except ImportError:
            print("PIL 未安装，使用原图")

    b64 = base64.b64encode(content).decode()

    # 尝试多个免费图床
    services = [
        ("https://freeimage.host/api/1/upload", {"key": "6d207e02198a847aa98d0a2a901485a5", "source": b64}),
        ("https://api.imgbb.com/1/upload", {"key": "7a010b39a04b53a2a6e0a14b5a19e767", "image": b64}),
    ]

    for url, data in services:
        try:
            print(f"尝试上传到 {url.split('/')[2]}...")
            resp = requests.post(url, data=data, timeout=30)
            result = resp.json()
            img_url = result.get("data", {}).get("url") or result.get("image", {}).get("url")
            if img_url:
                print(f"上传成功: {img_url}")
                return img_url
            else:
                print(f"返回异常: {str(result)[:200]}")
        except requests.exceptions.SSLError:
            print(f"{url.split('/')[2]} SSL错误")
            continue
        except Exception as e:
            print(f"{url.split('/')[2]} 上传失败: {e}")
            continue

    raise Exception("所有图床均不可用，请检查网络或开启代理")


def process_generated_output(raw_output):
    """处理 API 返回的原始输出，转成 base64 data URL 用于前端显示"""
    if not raw_output:
        return {"display_url": "", "catbox_url": None}

    img_bytes = None
    if raw_output.startswith('data:image/'):
        # 已经是 data URL，直接使用
        return {"display_url": raw_output, "catbox_url": raw_output}
    elif raw_output.startswith('http'):
        try:
            resp = requests.get(raw_output, timeout=30)
            resp.raise_for_status()
            img_bytes = resp.content
        except Exception as e:
            print(f"[ERROR] 下载图片失败: {e}")
    else:
        try:
            img_bytes = base64.b64decode(raw_output)
        except Exception as e:
            print(f"[ERROR] base64 解码失败: {e}")

    if not img_bytes:
        return {"display_url": "", "catbox_url": None}

    # 转成 data URL
    try:
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(img_bytes))
        buf = BytesIO()
        img.save(buf, format='PNG')
        b64_final = base64.b64encode(buf.getvalue()).decode()
        display_url = "data:image/png;base64," + b64_final
    except ImportError:
        if img_bytes[:3] == b'\xff\xd8\xff':
            display_url = "data:image/jpeg;base64," + base64.b64encode(img_bytes).decode()
        else:
            display_url = "data:image/png;base64," + base64.b64encode(img_bytes).decode()
    except Exception:
        display_url = "data:image/png;base64," + base64.b64encode(img_bytes).decode()

    return {"display_url": display_url, "catbox_url": display_url}


def generate_images(mode, prompt, aspect_ratio, num, style, steps, image_files, host_url="http://127.0.0.1:8080"):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload_base = {
        "output_format": "png",
        "aspect_ratio": aspect_ratio,
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

        # 上传图片到公网图床，获取可访问的HTTP URL
        image_url_list = []
        for f in image_files:
            f.seek(0)
            img_url = upload_to_imgbb(f)
            image_url_list.append(img_url)

        payload = {"prompt": prompt, "images": image_url_list, **payload_base}
        print(f"发起图生图请求，prompt: {prompt}")
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
