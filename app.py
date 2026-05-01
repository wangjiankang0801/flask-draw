import os
import time
from flask import Flask, request, render_template_string, jsonify
from html_template import HTML_PAGE
from config import ENABLE_LLM_OPT
from image2 import generate_images
from deepseek import call_llm_for_optimization
from history_manager import save_history_entry

app = Flask(__name__)

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
            "size": str(opt["size"]),
            "steps": opt["steps"],
            "num": opt["num"]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
        return jsonify({"success": False, "error": "提示词不能为空"}), 400
    try:
        results = generate_images(mode, prompt, int(size), num, style, steps, image_files)
        for item in results:
            catbox_url = item.get("catbox_url")
            if catbox_url:
                entry = {
                    "timestamp": time.time(),
                    "prompt": prompt,
                    "mode": mode,
                    "style": style,
                    "size": size,
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
