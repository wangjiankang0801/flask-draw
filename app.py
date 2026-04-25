import time
import os
from flask import Flask, request, render_template_string
import requests

app = Flask(__name__)

# ===== GPTs API 设置（从环境变量读取 Key） =====
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise RuntimeError("请设置环境变量 API_KEY")
TEXT2IMAGE_URL = "https://api.gptsapi.net/api/v3/openai/gpt-image-2-plus/text-to-image"
# =================================================

HTML_PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>GPTs API 手机画图</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" href="data:,">
  <style>
    body { font-family: Arial; margin: 20px; }
    input[type=text], select { padding: 8px; font-size: 16px; margin: 4px 0; width: 70%; }
    input[type=submit] { padding: 8px 16px; font-size: 16px; margin-top: 4px; }
    img { margin-top: 20px; max-width: 100%; height: auto; border: 1px solid #ccc; }
    .error { color: red; margin-top: 10px; }
    .loading { color: blue; margin-top: 10px; }
  </style>
</head>
<body>
<h2>GPTs API 手机画图</h2>

<form method="post" action="/">
  Prompt: <input type="text" name="prompt" maxlength="200" placeholder="输入你的创意提示" required><br>
  尺寸: 
  <select name="size">
    <option value="256">256x256</option>
    <option value="512" selected>512x512</option>
    <option value="1024">1024x1024</option>
  </select><br>
  数量: 
  <select name="num">
    <option value="1" selected>1</option>
    <option value="2">2</option>
    <option value="3">3</option>
  </select><br>
  <input type="submit" value="生成图片">
</form>

{% if loading %}
  <div class="loading">正在生成，请稍候…</div>
{% endif %}

{% if image_urls %}
  <h3>生成结果:</h3>
  {% for url in image_urls %}
    {% if url.startswith('data:') %}
      <!-- 直接显示 base64 图片 -->
      <img src="{{ url }}"><br>
    {% else %}
      <!-- 走代理加载普通 URL -->
      <img src="/proxy-image?url={{ url }}"><br>
    {% endif %}
  {% endfor %}
{% endif %}

{% if error %}
  <div class="error">{{ error }}</div>
{% endif %}
</body>
</html>
"""

def generate_images(prompt, size, num):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    image_urls = []
    for i in range(num):
        payload = {
            "prompt": prompt,
            "aspect_ratio": "1:1",
            "output_format": "png"
        }
        print(f"尝试生成第 {i+1} 张图片，prompt: {prompt}")
        try:
            response = requests.post(TEXT2IMAGE_URL, json=payload, headers=headers, timeout=30)
            print(f"POST 响应状态码: {response.status_code}")
            response.raise_for_status()
            data = response.json()["data"]
            get_url = data["urls"]["get"]
            print(f"获取到查询URL: {get_url}")

            # 轮询直到生成完成
            while True:
                r = requests.get(get_url, headers=headers)
                r.raise_for_status()
                j = r.json()
                status = j["data"]["status"]
                print("轮询状态:", status)
                if status == "completed":
                    image_url = j["data"]["outputs"][0]
                    print(f"图片URL前100字符: {str(image_url)[:100]}")
                    image_urls.append(image_url)
                    break
                elif status == "failed":
                    print("API 返回生成失败")
                    raise Exception("生成失败")
                time.sleep(2)
        except Exception as e:
            print(f"生成第 {i+1} 张时出错: {e}")
            raise  # 重新抛出，让上层捕获后显示在页面
    return image_urls

@app.route('/proxy-image')
def proxy_image():
    url = request.args.get('url')
    if not url:
        return "缺少url", 400
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        return resp.content, 200, {'Content-Type': 'image/png'}
    except Exception as e:
        print(f"代理图片失败: {e}")
        return f"图片加载失败: {e}", 500

@app.route("/", methods=["GET", "POST"])
def index():
    image_urls = None
    error_msg = None
    loading = False
    if request.method == "POST":
        prompt = request.form["prompt"]
        size = request.form.get("size", "512")
        num = int(request.form.get("num", "1"))
        loading = True
        print(f"收到生成请求: prompt={prompt}, size={size}, num={num}")
        try:
            image_urls = generate_images(prompt, size, num)
        except Exception as e:
            error_msg = f"生成失败: {e}"
            print(f"最终错误信息: {error_msg}")
    return render_template_string(HTML_PAGE, image_urls=image_urls, error=error_msg, loading=loading)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
