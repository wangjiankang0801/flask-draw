import time
import base64
import requests
from config import (
    API_KEY,
    TEXT2IMAGE_URL,
    IMAGE_EDIT_URL,
    CATBOX_UPLOAD_URL,
    DEFAULT_NEGATIVE_PROMPT,
)


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