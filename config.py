import os

# 图像生成 API 配置
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise RuntimeError("请设置环境变量 API_KEY")

TEXT2IMAGE_URL = "https://api.gptsapi.net/api/v3/openai/gpt-image-2-plus/text-to-image"
IMAGE_EDIT_URL = "https://api.gptsapi.net/api/v3/openai/gpt-image-2-plus/image-edit"
CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"

# 大模型优化配置（DeepSeek）
LLM_API_KEY = os.environ.get("LLM_API_KEY", "sk-bd36e809d93440d2ad5393b3d328c8b7")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-flash")
ENABLE_LLM_OPT = bool(LLM_API_KEY)

# 默认负面提示词
DEFAULT_NEGATIVE_PROMPT = (
    "low quality, blurry, distorted, deformed, bad anatomy, "
    "mutated hands, extra fingers, missing fingers, bad proportions, "
    "text, watermark, signature, logo"
)

# 历史记录存储文件
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")
