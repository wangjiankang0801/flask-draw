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
    """
    if not ENABLE_LLM_OPT:
        return {"optimized_prompt": user_prompt, "style": "realistic", "aspect_ratio": "1:1", "steps": 50, "num": 1}

    system_prompt = f"""你是一个专业的AI绘画提示词优化助手。
用户输入一句描述，你需要将它转换成适合AI图像生成的高质量参数。
当前模式：{mode}（text2image=文生图 或 image2image=图生图）。

【重要规则】
1. 你的回复必须且只能是一个JSON对象，不要有任何其他文字、解释或markdown标记
2. 如果是图生图模式，提示词必须强调：保持原图人物/主体的面部特征、外貌、姿态不变，仅优化背景、光影和画质
3. 图生图描述人物时必须包含：保持原始人物面部特征和外貌一致性

JSON格式：
{{"optimized_prompt":"优化后的提示词","style":"风格","aspect_ratio":"宽高比","steps":步数,"num":数量}}

可选值：
- style: realistic, anime, digital-painting, oil-painting, pixel-art
- aspect_ratio: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3
- steps: 30, 50, 100
- num: 1, 2, 3

示例1 - 文生图：
用户：一只可爱的猫
输出：{{"optimized_prompt":"一只可爱的猫，毛茸茸的，大眼睛，好奇的表情，柔和的自然光，高细节，4K","style":"realistic","aspect_ratio":"1:1","steps":50,"num":1}}

示例2 - 图生图（有人脸）：
用户：帮我优化这张照片
输出：{{"optimized_prompt":"保持原图人物面部特征和外貌不变，增强画质和细节，优化光影效果，自然柔和的光线，高分辨率，4K画质","style":"realistic","aspect_ratio":"1:1","steps":50,"num":1}}"""

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
        "temperature": 0.1,
        "max_tokens": 500
    }
    try:
        resp = requests.post(LLM_BASE_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"]

        # 提取JSON - 先尝试找```json...```包裹的，再找普通{}
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
            else:
                print(f"大模型返回未包含JSON: {content[:200]}")
                return _fallback(user_prompt, mode)

        params = json.loads(json_str)
        # 校验并修正值
        allowed_styles = ["realistic", "anime", "digital-painting", "oil-painting", "pixel-art"]
        if params.get("style") not in allowed_styles:
            params["style"] = "realistic"
        allowed_ratios = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"]
        if params.get("aspect_ratio") not in allowed_ratios:
            params["aspect_ratio"] = "1:1"
        if params.get("steps") not in [30, 50, 100]:
            params["steps"] = 50
        if params.get("num") not in [1, 2, 3]:
            params["num"] = 1
        if not params.get("optimized_prompt"):
            params["optimized_prompt"] = user_prompt
        return params

    except Exception as e:
        print(f"调用大模型失败：{e}，使用原始参数")
        return _fallback(user_prompt, mode)


def _fallback(user_prompt, mode):
    """优化失败时的兜底处理"""
    if mode == "image2image":
        return {
            "optimized_prompt": f"保持原图人物面部特征和外貌不变，{user_prompt}，增强画质和细节，优化光影效果，高分辨率，4K画质",
            "style": "realistic",
            "aspect_ratio": "1:1",
            "steps": 50,
            "num": 1
        }
    return {
        "optimized_prompt": user_prompt,
        "style": "realistic",
        "aspect_ratio": "1:1",
        "steps": 50,
        "num": 1
    }
