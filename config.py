import os

# 鍥惧儚鐢熸垚 API 閰嶇疆
API_KEY = os.environ.get("API_KEY", "sk-LRV7cc12e796a5652f70783b1337cf9e6f8aece3e23ayFSs")

TEXT2IMAGE_URL = "https://api.gptsapi.net/api/v3/openai/gpt-image-2/text-to-image"
IMAGE_EDIT_URL = "https://api.gptsapi.net/api/v3/openai/gpt-image-2/image-edit"
# 澶фā鍨嬩紭鍖栭厤缃紙DeepSeek锛?
LLM_API_KEY = os.environ.get("LLM_API_KEY", "sk-b5dfb9c6552244aabfd92765c51acffe")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-flash")
ENABLE_LLM_OPT = bool(LLM_API_KEY)

# 榛樿璐熼潰鎻愮ず璇?
DEFAULT_NEGATIVE_PROMPT = (
    "low quality, blurry, distorted, deformed, bad anatomy, "
    "mutated hands, extra fingers, missing fingers, bad proportions, "
    "text, watermark, signature, logo"
)

# 鍘嗗彶璁板綍瀛樺偍鏂囦欢
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")
