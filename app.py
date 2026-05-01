import os
import time
from flask import Flask, request, render_template_string, jsonify, send_from_directory
from html_template import HTML_PAGE
from config import ENABLE_LLM_OPT
from image2 import generate_images, TEMP_DIR
from deepseek import call_llm_for_optimization
from history_manager import save_history_entry

app = Flask(__name__)

@app.route("/temp/<filename>")
def serve_temp_image(filename):
    """托管临时上传的图片，供图片生成API访问"""
    return send_from_directory(TEMP_DIR, filename)

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)

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
            "aspect_ratio": opt["aspect_ratio"],
            "steps": opt["steps"],
            "num": opt["num"]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/generate", methods=["POST"])
def generate():
    mode = request.form.get("mode")
    prompt = request.form.get("prompt")
    aspect_ratio = request.form.get("aspect_ratio", "1:1")
    style = request.form.get("style")
    num = int(request.form.get("num", 1))
    steps = int(request.form.get("steps", 50))
    image_files = request.files.getlist("image_files") if mode == "image2image" else []

    if not prompt:
        return jsonify({"success": False, "error": "提示词不能为空"}), 400
    try:
        host_url = request.host_url.rstrip("/")
        results = generate_images(mode, prompt, aspect_ratio, num, style, steps, image_files, host_url)
        for item in results:
            catbox_url = item.get("catbox_url")
            if catbox_url:
                entry = {
                    "timestamp": time.time(),
                    "prompt": prompt,
                    "mode": mode,
                    "style": style,
                    "aspect_ratio": aspect_ratio,
                    "catbox_url": catbox_url
                }
                save_history_entry(entry)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/history", methods=["GET"])
def api_history():
    from history_manager import load_history
    history = load_history()
    history.reverse()
    return jsonify(history)

@app.route("/api/history/delete", methods=["POST"])
def api_delete_history():
    """删除历史记录（支持批量删除）"""
    data = request.get_json()
    indices = data.get("indices", [])
    if not indices:
        return jsonify({"success": False, "error": "未选择要删除的记录"}), 400
    from history_manager import delete_history_entries
    delete_history_entries(indices)
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
