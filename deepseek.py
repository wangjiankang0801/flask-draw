import re
import json
import requests
from config import (
    ENABLE_LLM_OPT,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
)


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