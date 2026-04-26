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

# 默认负面提示词
DEFAULT_NEGATIVE_PROMPT = (
    "low quality, blurry, distorted, deformed, bad anatomy, "
    "mutated hands, extra fingers, missing fingers, bad proportions, "
    "text, watermark, signature, logo"
)
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
    input[type=button], input[type=submit] { padding: 8px 16px; font-size: 16px; margin-top: 4px; }
    
    img.thumb { width: 160px; height: 160px; object-fit: cover; margin: 8px; cursor: pointer; border: 1px solid #ccc; border-radius: 4px; }
    img.result-thumb { width: 300px; height: 300px; object-fit: cover; margin: 8px; cursor: pointer; border: 1px solid #ccc; border-radius: 4px; }
    
    .container { display: flex; flex-wrap: wrap; gap: 15px; margin-top: 12px; }
    .error { color: red; margin-top: 10px; }
    .loading { color: blue; margin-top: 10px; }
    
    .preview-item { position: relative; display: inline-block; }
    .preview-item .delete-btn {
      position: absolute; top: 0; right: 0;
      background: rgba(255,0,0,0.7); color: white; border: none; border-radius: 50%;
      width: 22px; height: 22px; font-size: 14px; line-height: 22px; text-align: center; cursor: pointer;
    }
    
    .modal { display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.8); justify-content:center; align-items:center; overflow: hidden; }
    .modal img { max-width: 95vw; max-height: 95vh; transform-origin: center center; transition: transform 0.1s ease; user-select: none; }
    
    #preview_section { margin: 12px 0; }
    #preview_container { display: flex; flex-wrap: wrap; gap: 15px; margin-top: 8px; }
    #upload_section { display:none; margin: 8px 0; }
    #size_section, #num_section, #style_section, #steps_section { display: inline-block; margin-right: 12px; margin-top: 8px; }
    
    .confirm-dialog {
      display: none; position: fixed; z-index: 2000; left: 0; top: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.5); justify-content: center; align-items: center;
    }
    .confirm-box {
      background: white; padding: 20px; border-radius: 10px; text-align: center; max-width: 300px;
    }
    .confirm-box button { margin: 10px 5px; padding: 8px 20px; font-size: 16px; }
    .btn-generate { background: #007bff; color: white; border: none; }
    .btn-cancel { background: #ccc; border: none; }
    
    .catbox-link { font-size: 12px; word-break: break-all; display: block; margin-top: 4px; color: #666; }
  </style>
</head>
<body>
<h2>GPTs AI 画图（文生图 / 图生图）</h2>

<form id="main-form" method="post" action="/" enctype="multipart/form-data">
  <label>
    <input type="radio" name="mode" value="text2image" checked onchange="toggleMode()"> 文生图
  </label>
  <label style="margin-left: 12px;">
    <input type="radio" name="mode" value="image2image" onchange="toggleMode()"> 图生图
  </label>
  <br><br>
  Prompt: <br>
  <textarea name="prompt" id="prompt" rows="5" maxlength="200" placeholder="输入你的创意提示" required></textarea>
  <br>
  <div id="size_section">
    尺寸: 
    <select name="size" id="size">
      <option value="256">256x256</option>
      <option value="512" selected>512x512</option>
      <option value="1024">1024x1024</option>
    </select>
  </div>
  <div id="num_section">
    数量: 
    <select name="num" id="num">
      <option value="1" selected>1</option>
      <option value="2">2</option>
      <option value="3">3</option>
    </select>
  </div>
  <div id="style_section">
    风格: 
    <select name="style" id="style">
      <option value="realistic" selected>写实 (Realistic)</option>
      <option value="anime">二次元 (Anime)</option>
      <option value="digital-painting">数字绘画 (Digital Painting)</option>
      <option value="oil-painting">油画 (Oil Painting)</option>
      <option value="pixel-art">像素风 (Pixel Art)</option>
    </select>
  </div>
  <div id="steps_section">
    细节步数: 
    <select name="steps" id="steps">
      <option value="30" selected>30 - 快速生成</option>
      <option value="50">50 - 标准细节</option>
      <option value="100">100 - 高细节</option>
    </select>
  </div>
  <br>
  <div id="upload_section">
    上传参考图片（可多张）: <input type="file" name="image_files" id="image_input" accept="image/*" multiple><br>
    <div id="preview_section">
      <div id="preview_container"></div>
    </div>
  </div>
  <br>
  <input type="button" id="submit-btn" value="生成图片">
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

{% if image_results %}
  <h3>生成结果:</h3>
  <div class="container">
  {% for item in image_results %}
    <div class="result-item">
      <img class="result-thumb" src="{{ item.display_url }}" onclick="showModal(this.src)">
      {% if item.catbox_url %}
        <a class="catbox-link" href="{{ item.catbox_url }}" target="_blank">🔗 永久链接</a>
      {% endif %}
    </div>
  {% endfor %}
  </div>
{% endif %}

{% if error %}
  <div class="error">{{ error }}</div>
{% endif %}

<div class="modal" id="modal" onclick="hideModal()">
  <img id="modalImg" src="">
</div>

<div class="confirm-dialog" id="confirm-dialog">
  <div class="confirm-box">
    <p>确认生成图片？<br>这将消耗一次额度</p>
    <button class="btn-generate" id="confirm-yes">确认生成</button>
    <button class="btn-cancel" id="confirm-no">取消</button>
  </div>
</div>

<script>
let currentScale = 1;
let currentX = 0;
let currentY = 0;
let startX = 0;
let startY = 0;
let isDragging = false;
const modal = document.getElementById('modal');
const modalImg = document.getElementById('modalImg');
let selectedFiles = [];

function toggleMode() {
    var mode = document.querySelector('input[name="mode"]:checked').value;
    document.getElementById('upload_section').style.display = (mode === 'image2image') ? 'block' : 'none';
}

function renderPreview() {
    const container = document.getElementById('preview_container');
    container.innerHTML = '';
    if (selectedFiles.length === 0) return;
    selectedFiles.forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = function(e) {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'preview-item';
            const img = document.createElement('img');
            img.className = 'thumb';
            img.src = e.target.result;
            img.onclick = function() { showModal(this.src); };
            const delBtn = document.createElement('span');
            delBtn.className = 'delete-btn';
            delBtn.innerHTML = '✕';
            delBtn.title = '删除此图片';
            delBtn.onclick = function(ev) {
                ev.stopPropagation();
                selectedFiles.splice(index, 1);
                renderPreview();
                updateFileInput();
            };
            itemDiv.appendChild(img);
            itemDiv.appendChild(delBtn);
            container.appendChild(itemDiv);
        };
        reader.readAsDataURL(file);
    });
}

function updateFileInput() {
    const dt = new DataTransfer();
    selectedFiles.forEach(f => dt.items.add(f));
    document.getElementById('image_input').files = dt.files;
}

document.getElementById('image_input').addEventListener('change', function(e) {
    const newFiles = Array.from(e.target.files);
    newFiles.forEach(file => {
        const exists = selectedFiles.some(f => f.name === file.name && f.size === file.size);
        if (!exists) selectedFiles.push(file);
    });
    renderPreview();
    updateFileInput();
});

function showModal(src){
    modalImg.src = src;
    modal.style.display = 'flex';
    currentScale = 1;
    currentX = 0;
    currentY = 0;
    updateTransform();
}
function hideModal(){ modal.style.display = 'none'; }
function updateTransform() {
    modalImg.style.transform = `translate(${currentX}px, ${currentY}px) scale(${currentScale})`;
}

modalImg.addEventListener('wheel', function(e) {
    e.preventDefault();
    const scaleStep = 0.1;
    if (e.deltaY < 0) { currentScale = Math.min(currentScale + scaleStep, 10); }
    else { currentScale = Math.max(currentScale - scaleStep, 0.5); }
    updateTransform();
});

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
document.addEventListener('mouseup', function() { isDragging = false; });

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
document.addEventListener('touchend', function() { isDragging = false; });

modal.addEventListener('click', function(e) {
    if (e.target === modal) { hideModal(); }
});

// 确认弹窗
document.getElementById('submit-btn').addEventListener('click', function() {
    var mode = document.querySelector('input[name="mode"]:checked').value;
    if (mode === 'image2image') {
        if (selectedFiles.length === 0) {
            alert("请先上传参考图片再生成");
            return;
        }
    }
    document.getElementById('confirm-dialog').style.display = 'flex';
});

document.getElementById('confirm-yes').addEventListener('click', function() {
    document.getElementById('confirm-dialog').style.display = 'none';
    var btn = document.getElementById('submit-btn');
    btn.value = '生成中…';
    btn.disabled = true;
    var form = document.getElementById('main-form');
    var formData = new FormData(form);
    formData.delete('image_files');
    selectedFiles.forEach(file => { formData.append('image_files', file); });
    fetch(form.action, { method: 'POST', body: formData })
    .then(response => response.text())
    .then(html => { document.open(); document.write(html); document.close(); })
    .catch(err => { console.error(err); btn.value = '生成图片'; btn.disabled = false; alert('提交失败，请重试'); });
});

document.getElementById('confirm-no').addEventListener('click', function() {
    document.getElementById('confirm-dialog').style.display = 'none';
});

toggleMode();
</script>

</body>
</html>
"""


def upload_bytes_to_catbox(img_bytes, filename="generated.png"):
    """将图片字节上传到 catbox.moe，返回直链"""
    files = {"fileToUpload": (filename, img_bytes, "image/png")}
    data = {"reqtype": "fileupload"}
    try:
        resp = requests.post(CATBOX_UPLOAD_URL, files=files, data=data, timeout=60)
        if resp.status_code != 200:
            print(f"catbox 备份上传失败: {resp.text}")
            return None
        url = resp.text.strip()
        if url.startswith("http"):
            print(f"图片已备份到 catbox: {url}")
            return url
        else:
            print(f"catbox 返回异常: {url}")
            return None
    except Exception as e:
        print(f"备份上传异常: {e}")
        return None


def upload_to_catbox(file):
    """上传参考图片到 catbox.moe，返回直链"""
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


def process_generated_output(raw_output):
    """处理生成的单个输出，返回 {'display_url': ..., 'catbox_url': ...}"""
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
        # 文生图不需要 images 字段
        results = []
        for i in range(num):
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


@app.route("/", methods=["GET", "POST"])
def index():
    uploaded_images = []
    image_results = None
    error_msg = None
    loading = False
    if request.method == "POST":
        mode = request.form.get("mode", "text2image")
        prompt = request.form["prompt"]
        size = request.form.get("size", "512")
        num = int(request.form.get("num", "1"))
        style = request.form.get("style", "realistic")
        steps = int(request.form.get("steps", "30"))
        image_files = []
        loading = True
        print(f"收到请求: mode={mode}, prompt={prompt}, size={size}, num={num}, style={style}, steps={steps}")

        if mode == "image2image":
            image_files = request.files.getlist("image_files")
            for f in image_files:
                f.seek(0)
                content = f.read()
                uploaded_images.append("data:image/png;base64," + base64.b64encode(content).decode("utf-8"))
                f.seek(0)

        try:
            image_results = generate_images(mode, prompt, size, num, style, steps, image_files)
        except Exception as e:
            error_msg = f"生成失败: {e}"
            print(f"最终错误: {error_msg}")

    return render_template_string(HTML_PAGE,
                                  image_results=image_results,
                                  error=error_msg,
                                  loading=loading,
                                  uploaded_images=uploaded_images)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
    
