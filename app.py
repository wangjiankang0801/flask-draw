import time
import os
import base64
from flask import Flask, request, render_template_string
import requests

app = Flask(__name__)

# ===== GPTs API 设置（从环境变量读取 Key） =====
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise RuntimeError("请设置环境变量 API_KEY")

TEXT2IMAGE_URL = "https://api.gptsapi.net/api/v3/openai/gpt-image-2-plus/text-to-image"
IMAGE_EDIT_URL = "https://api.gptsapi.net/api/v3/openai/gpt-image-2-plus/image-edit"
# =================================================

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
// 初始化默认显示
toggleMode();
</script>

</body>
</html>
"""

def generate_images(mode, prompt, size, num, image_files):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    if mode == "text2image":
        # 文生图逻辑
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

                # 轮询
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
                        raise Exception("生成失败")
                    time.sleep(2)
            except Exception as e:
                print(f"文生图第 {i+1} 张出错: {e}")
                raise
        return image_urls

    else:  # image2image
        # 图生图逻辑
        url = IMAGE_EDIT_URL
        # 上传图片转 base64
        images_base64 = []
        for f in image_files:
            content = f.read()
            images_base64.append("data:image/png;base64," + base64.b64encode(content).decode("utf-8"))
            f.seek(0)  # 后续可能再用

        payload = {
            "prompt": prompt,
            "images": images_base64,
            "output_format": "png",
            "size": size,
            "num_outputs": num
        }
        print(f"发起图生图请求，prompt: {prompt}, images: {len(images_base64)}张")
        response = requests.post(url, json=payload, headers=headers, timeout=60)
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
                outputs = j["data"]["outputs"]
                image_urls = []
                for image_url in outputs:
                    if image_url and not image_url.startswith("data:") and not image_url.startswith("http"):
                        image_url = "data:image/png;base64," + image_url
                        print("已补全 base64 前缀")
                    image_urls.append(image_url)
                return image_urls
            elif status == "failed":
                raise Exception("生成失败")
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
            # 预览上传的参考图
            for f in image_files:
                content = f.read()
                uploaded_images.append("data:image/png;base64," + base64.b64encode(content).decode("utf-8"))
                f.seek(0)  # 重置指针，供生成时再读

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
