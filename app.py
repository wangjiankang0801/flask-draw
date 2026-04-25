import time
import os
import base64
import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

# ===== API 设置 =====
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise RuntimeError("请设置环境变量 API_KEY")

TEXT2IMAGE_URL = "https://api.gptsapi.net/api/v3/openai/gpt-image-2-plus/text-to-image"
IMAGE_EDIT_URL = "https://api.gptsapi.net/api/v3/openai/gpt-image-2-plus/image-edit"
CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"
# =====================

HTML_PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>GPTs AI 画图</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" href="data:,">
  <style>
    body { font-family: Arial; margin: 20px; }
    input[type=text], select, input[type=file] { padding: 8px; font-size: 16px; margin: 4px 0; width: 70%; }
    input[type=submit] { padding: 8px 16px; font-size: 16px; margin-top: 4px; }
    img.thumb { width: 120px; height: 120px; object-fit: cover; margin: 4px; cursor: pointer; border: 1px solid #ccc; }
    .container { display: flex; flex-wrap: wrap; gap: 10px; }
    .error { color: red; margin-top: 10px; }
    .loading { color: blue; margin-top: 10px; }
    .modal { display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.8); justify-content:center; align-items:center; }
    .modal img { max-width:90%; max-height:90%; }
    #upload_section { display:none; }
  </style>
</head>
<body>
<h2>GPTs AI 画图（文生图 / 图生图）</h2>

<form method="post" action="/" enctype="multipart/form-data">
  <label>
    <input type="radio" name="mode" value="text2image" checked onchange="toggleMode()"> 文生图
  </label>
  <label>
    <input type="radio" name="mode" value="image2image" onchange="toggleMode()"> 图生图
  </label>
  <br>
  Prompt: <input type="text" name="prompt" maxlength="200" placeholder="输入你的创意提示" required><br>
  <div id="size_section">
    尺寸: 
    <select name="size">
      <option value="256">256x256</option>
      <option value="512" selected>512x512</option>
      <option value="1024">1024x1024</option>
    </select>
  </div>
  数量: 
  <select name="num">
    <option value="1" selected>1</option>
    <option value="2">2</option>
    <option value="3">3</option>
  </select><br>
  <div id="upload_section">
    上传参考图片（可多张）: <input type="file" name="image_files" accept="image/*" multiple><br>
  </div>
  <input type="submit" value="生成图片">
</form>

{% if loading %}
  <div class="loading">正在生成，请稍候…</div>
{% endif %}

{% if uploaded_images %}
  <h3>参考图片:</h3>
  <div class="container">
  {% for url in uploaded_images %}
    <img class="thumb" src="{{ url }}" onclick="showModal(this.src)">
  {% endfor %}
  </div>
{% endif %}

{% if image_urls %}
  <h3>生成结果:</h3>
  <div class="container">
  {% for url in image_urls %}
    <img class="thumb" src="{{ url }}" onclick="showModal(this.src)">
  {% endfor %}
  </div>
{% endif %}

{% if error %}
  <div class="error">{{ error }}</div>
{% endif %}

<div class="modal" id="modal" onclick="hideModal()">
  <img id="modalImg" src="">
</div>

<script>
function toggleMode() {
    var mode = document.querySelector('input[name="mode"]:checked').value;
    document.getElementById('upload_section').style.display = (mode === 'image2image') ? 'block' : 'none';
    document.getElementById('size_section').style.display = (mode === 'text2image') ? 'block' : 'none';
}
function showModal(src){
    document.getElementById('modalImg').src = src;
    document.getElementById('modal').style.display='flex';
}
function hideModal(){
    document.getElementById('modal').style.display='none';
}
toggleMode();
</script>

</body>
</html>
"""


def upload_to_catbox(file):
    """上传图片到 catbox.moe，返回直链"""
    content = file.read()
    file.seek(0)
    original_size = len(content)

    # 如果 > 1MB 自动压缩（catbox 限制 200MB，但压缩可提速）
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
        print(f"catbox 响应状态码: {resp.status_code}")
        if resp.status_code != 200:
            print(f"catbox 错误响应: {resp.text}")
            resp.raise_for_status()
        url = resp.text.strip()
        if url.startswith("http"):
            print(f"上传成功: {url}")
            return url
        else:
            raise Exception(f"返回格式异常: {url}")
    except Exception as e:
        print(f"catbox 上传异常: {e}")
        raise


def generate_images(mode, prompt, size, num, image_files):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    if mode == "text2image":
        url = TEXT2IMAGE_URL
        image_urls = []
        for i in range(num):
            payload = {
                "prompt": prompt,
                "aspect_ratio": "1:1",
                "output_format": "png"
            }
            print(f"尝试生成第 {i+1} 张图片（文生图），prompt: {prompt}")
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()["data"]
                get_url = data["urls"]["get"]
                print(f"获取到查询URL: {get_url}")

                while True:
                    r = requests.get(get_url, headers=headers)
                    r.raise_for_status()
                    j = r.json()
                    status = j["data"]["status"]
                    print("轮询状态:", status)
                    if status == "completed":
                        image_url = j["data"]["outputs"][0]
                        print(f"图片URL前100字符: {str(image_url)[:100]}")
                        if image_url and not image_url.startswith('data:') and not image_url.startswith('http'):
                            image_url = "data:image/png;base64," + image_url
                            print("已补全 base64 前缀")
                        image_urls.append(image_url)
                        break
                    elif status == "failed":
                        error_detail = j.get("data", {}).get("error") or j.get("error") or "未知错误"
                        print(f"文生图失败，完整响应: {j}")
                        raise Exception(f"生成失败: {error_detail}")
                    time.sleep(2)
            except Exception as e:
                print(f"文生图第 {i+1} 张出错: {e}")
                raise
        return image_urls

    else:  # image2image
        if not image_files:
            raise Exception("请上传至少一张参考图片")

        image_url_list = []
        for f in image_files:
            f.seek(0)
            img_url = upload_to_catbox(f)
            image_url_list.append(img_url)

        print(f"catbox 上传完成，共 {len(image_url_list)} 个链接")

        payload = {
            "prompt": prompt,
            "images": image_url_list,
            "output_format": "png",
            "size": size,
            "num_outputs": num
        }

        print(f"发起图生图请求，prompt: {prompt}, images: {image_url_list}")
        try:
            response = requests.post(IMAGE_EDIT_URL, json=payload, headers=headers, timeout=60)
        except Exception as e:
            print(f"图生图 POST 请求失败: {e}")
            raise
        print(f"图生图 POST 响应状态码: {response.status_code}")
        if response.status_code != 200:
            print(f"错误响应: {response.text}")
            response.raise_for_status()

        data = response.json().get("data")
        if not data:
            raise Exception(f"响应中没有 data: {response.json()}")
        get_url = data["urls"]["get"]
        print(f"获取到查询URL: {get_url}")

        while True:
            r = requests.get(get_url, headers=headers)
            r.raise_for_status()
            j = r.json()
            status = j.get("data", {}).get("status")
            print("轮询状态:", status)

            if status == "completed":
                outputs = j["data"]["outputs"]
                image_urls = []
                for image_url in outputs:
                    if image_url and not image_url.startswith("data:") and not image_url.startswith("http"):
                        image_url = "data:image/png;base64," + image_url
                        print("已补全 base64 前缀")
                    image_urls.append(image_url)
                return image_urls

            elif status == "failed":
                print("图生图失败，完整响应:", j)
                error_detail = j.get("data", {}).get("error") or j.get("error") or "未知错误"
                raise Exception(f"生成失败: {error_detail}")
            else:
                pass
            time.sleep(2)


@app.route("/", methods=["GET", "POST"])
def index():
    uploaded_images = []
    image_urls = None
    error_msg = None
    loading = False
    if request.method == "POST":
        mode = request.form.get("mode", "text2image")
        prompt = request.form["prompt"]
        size = request.form.get("size", "512")
        num = int(request.form.get("num", "1"))
        image_files = []
        loading = True
        print(f"收到请求: mode={mode}, prompt={prompt}, size={size}, num={num}")

        if mode == "image2image":
            image_files = request.files.getlist("image_files")
            for f in image_files:
                f.seek(0)
                content = f.read()
                uploaded_images.append("data:image/png;base64," + base64.b64encode(content).decode("utf-8"))
                f.seek(0)

        try:
            image_urls = generate_images(mode, prompt, size, num, image_files)
        except Exception as e:
            error_msg = f"生成失败: {e}"
            print(f"最终错误: {error_msg}")

    return render_template_string(HTML_PAGE,
                                  image_urls=image_urls,
                                  error=error_msg,
                                  loading=loading,
                                  uploaded_images=uploaded_images)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
