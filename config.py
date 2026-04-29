"""Configuration management with priority: env vars > config.json > defaults."""
import json
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # 高德
    amap_api_key: str = ""
    amap_security_key: str = ""  # 高德安全密钥(jscode)
    amap_city: str = "北京"

    # 咖啡API
    coffee_api_mode: str = "mock"  # "mock" | "meituan"
    meituan_api_key: str = ""

    # LLM
    ollama_model: str = "gemma4:e2b"
    ollama_base_url: str = "http://localhost:11434/api/chat"
    ollama_timeout: float = 520.0

    def __post_init__(self):
        self._load_from_file()
        self._load_from_env()

    def _load_from_file(self):
        config_path = os.environ.get("CONFIG_FILE", "config.json")
        if not os.path.exists(config_path):
            return
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, value in data.items():
                if not hasattr(self, key):
                    continue
                # Check if env var is set (considering AMAP_KEY alias)
                env_key = key.upper()
                if key == "amap_api_key":
                    # amap_api_key can come from AMAP_API_KEY or AMAP_KEY env
                    if os.environ.get("AMAP_API_KEY") or os.environ.get("AMAP_KEY"):
                        continue
                elif os.environ.get(env_key):
                    continue
                setattr(self, key, value)
        except (json.JSONDecodeError, IOError):
            pass

    def _load_from_env(self):
        # 高德 key：优先使用 AMAP_API_KEY，没有则用 AMAP_KEY
        # 注意：只在当前值为空时设置（file已加载过的情况）
        amap_key = os.environ.get("AMAP_API_KEY") or os.environ.get("AMAP_KEY", "")
        if amap_key and not self.amap_api_key:
            self.amap_api_key = amap_key

        amap_security_key = os.environ.get("AMAP_SECURITY_KEY", "")
        if amap_security_key and not self.amap_security_key:
            self.amap_security_key = amap_security_key

        self.amap_city = os.environ.get("AMAP_CITY") or self.amap_city
        self.coffee_api_mode = os.environ.get("COFFEE_API_MODE") or self.coffee_api_mode
        self.meituan_api_key = os.environ.get("MEITUAN_API_KEY") or self.meituan_api_key
        self.ollama_model = os.environ.get("OLLAMA_MODEL") or self.ollama_model
        self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL") or self.ollama_base_url
        self.ollama_timeout = float(os.environ.get("OLLAMA_TIMEOUT") or self.ollama_timeout)

    def validate(self):
        if not self.amap_api_key:
            raise ValueError("amap_api_key is required. Set AMAP_API_KEY env var or add to config.json")
        if self.coffee_api_mode not in ("mock", "meituan"):
            raise ValueError(f"coffee_api_mode must be 'mock' or 'meituan', got '{self.coffee_api_mode}'")

    def get_missing_key_guidance(self) -> str:
        missing = []
        if not self.amap_api_key:
            missing.append(
                "高德API Key缺失，请前往 https://lbs.amap.com/ 注册并创建应用获取Web服务Key，"
                "然后设置环境变量 AMAP_API_KEY 或在 config.json 中添加 amap_api_key"
            )
        if not self.meituan_api_key and self.coffee_api_mode == "meituan":
            missing.append(
                "美团API Key缺失，请前往 https://open.meituan.com/ 申请，"
                "然后设置环境变量 MEITUAN_API_KEY 或在 config.json 中添加 meituan_api_key"
            )
        return "\n\n".join(missing)
