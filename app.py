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
    input[type=text], textarea, select, input[type=file] { padding: 8px; font-size: 16px; margin: 4px 0; width: 70%; }
    input[type=file] { color: transparent; width: auto; }
    textarea { resize: vertical; line-height: 1.5; }
    input[type=submit] { padding: 8px 16px; font-size: 16px; margin-top: 4px; }
    /* 放大缩略图默认尺寸，可自行修改宽高数值调整大小 */
    img.thumb { width: 300px; height: 300px; object-fit: cover; margin: 8px; cursor: pointer; border: 1px solid #ccc; border-radius: 4px; }
    .container { display: flex; flex-wrap: wrap; gap: 15px; margin-top: 12px; }
    .error { color: red; margin-top: 10px; }
    .loading { color: blue; margin-top: 10px; }
    /* 弹窗缩放核心样式 */
    .modal { display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.8); justify-content:center; align-items:center; overflow: hidden; }
    .modal img { 
      max-width: 95vw; 
      max-height: 95vh; 
      transform-origin: center center;
      transition: transform 0.1s ease;
      user-select: none;
    }
    /* 选择文件即时预览区域样式 */
    #preview_section { margin: 12px 0; }
    #preview_container { display: flex; flex-wrap: wrap; gap: 15px; margin-top: 8px; }
    #upload_section { display:none; margin: 8px 0; }
    #size_section { display: inline-block; margin-right: 12px; }
  </style>
</head>
<body>
<h2>GPTs AI 画图（文生图 / 图生图）</h2>

<form method="post" action="/" enctype="multipart/form-data">
  <label>
    <input type="radio" name="mode" value="text2image" checked onchange="toggleMode()"> 文生图
  </label>
  <label style="margin-left: 12px;">
    <input type="radio" name="mode" value="image2image" onchange="toggleMode()"> 图生图
  </label>
  <br><br>
  Prompt: <br>
  <textarea name="prompt" rows="5" maxlength="200" placeholder="输入你的创意提示" required></textarea>
  <br>
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
    上传参考图片（可多张）: <input type="file" name="image_files" id="image_input" accept="image/*" multiple><br>
    <!-- 新增选择文件即时预览容器 -->
    <div id="preview_section">
      <div id="preview_container"></div>
    </div>
  </div>
  <br>
  <input type="submit" value="生成图片">
</form>

{% if loading %}
  <div class="loading">正在生成，请稍候…</div>
{% endif %}

<!-- 参考图片区域，使用与生成结果相同的 thumb 类 -->
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
// 缩放拖拽核心变量
let currentScale = 1;
let currentX = 0;
let currentY = 0;
let startX = 0;
let startY = 0;
let isDragging = false;
const modal = document.getElementById('modal');
const modalImg = document.getElementById('modalImg');

// 文生图/图生图模式切换
function toggleMode() {
    var mode = document.querySelector('input[name="mode"]:checked').value;
    document.getElementById('upload_section').style.display = (mode === 'image2image') ? 'block' : 'none';
}

// 选择文件后即时预览大图
document.getElementById('image_input').addEventListener('change', function(e) {
    const previewContainer = document.getElementById('preview_container');
    previewContainer.innerHTML = ''; // 清空历史预览
    const files = e.target.files;
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (!file.type.startsWith('image/')) continue;
        
        const reader = new FileReader();
        reader.onload = function(event) {
            // 生成和提交后一致尺寸的预览图
            const img = document.createElement('img');
            img.className = 'thumb';
            img.src = event.target.result;
            img.onclick = function() { showModal(this.src); };
            previewContainer.appendChild(img);
        };
        reader.readAsDataURL(file);
    }
});

// 打开弹窗并重置缩放状态
function showModal(src){
    modalImg.src = src;
    modal.style.display = 'flex';
    // 每次打开重置缩放和位移
    currentScale = 1;
    currentX = 0;
    currentY = 0;
    updateTransform();
}

// 关闭弹窗
function hideModal(){
    modal.style.display = 'none';
}

// 更新图片缩放/位移状态
function updateTransform() {
    modalImg.style.transform = `translate(${currentX}px, ${currentY}px) scale(${currentScale})`;
}

// 鼠标滚轮缩放（最大10倍，最小0.5倍）
modalImg.addEventListener('wheel', function(e) {
    e.preventDefault();
    const scaleStep = 0.1;
    if (e.deltaY < 0) {
        currentScale = Math.min(currentScale + scaleStep, 10);
    } else {
        currentScale = Math.max(currentScale - scaleStep, 0.5);
    }
    updateTransform();
});

// 鼠标拖拽移动图片
modalImg.addEventListener('mousedown', function(e) {
    e.preventDefault();
    isDragging = true;
    startX = e.clientX - currentX;
    startY = e.clientY - currentY;
});

document.addEventListener('mousemove', function(e) {
    if (!isDragging) return;
    e.preventDefault();
    currentX = e.clientX - startX;
    currentY = e.clientY - startY;
    updateTransform();
});

document.addEventListener('mouseup', function() {
    isDragging = false;
});

// 移动端触摸拖拽适配
modalImg.addEventListener('touchstart', function(e) {
    isDragging = true;
    startX = e.touches[0].clientX - currentX;
    startY = e.touches[0].clientY - currentY;
});

document.addEventListener('touchmove', function(e) {
    if (!isDragging) return;
    currentX = e.touches[0].clientX - startX;
    currentY = e.touches[0].clientY - startY;
    updateTransform();
});

document.addEventListener('touchend', function() {
    isDragging = false;
});

// 点击弹窗背景关闭
modal.addEventListener('click', function(e) {
    if (e.target === modal) {
        hideModal();
    }
});

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

                while True:
                    r = requests.get(get_url, headers=headers)
                    r.raise_for_status()
                    j = r.json()
                    status = j["data"]["status"]
                    if status == "completed":
                        image_url = j["data"]["outputs"][0]
                        if image_url and not image_url.startswith('data:') and not image_url.startswith('http'):
                            image_url = "data:image/png;base64," + image_url
                        image_urls.append(image_url)
                        break
                    elif status == "failed":
                        error_detail = j.get("data", {}).get("error") or j.get("error") or "未知错误"
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

        size = f"{size}x{size}"

        payload = {
            "prompt": prompt,
            "images": image_url_list,
            "output_format": "png",
            "size": size,
            "num_outputs": num
        }

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
                image_urls = []
                for image_url in outputs:
                    if image_url and not image_url.startswith("data:") and not image_url.startswith("http"):
                        image_url = "data:image/png;base64," + image_url
                    image_urls.append(image_url)
                return image_urls

            elif status == "failed":
                error_detail = j.get("data", {}).get("error") or j.get("error") or "未知错误"
                raise Exception(f"生成失败: {error_detail}")
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
