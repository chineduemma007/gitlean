import os
import yaml
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "paritok.yaml"

class Settings:
    def __init__(self):
        self.use_gpu_server = False
        self.gpu_api_key = ""
        self.upstream_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.upstream_model = "claude-3-5-sonnet-20241022"
        self.paritok_proxy_url = "http://127.0.0.1:8080" # local proxy url
        
        self.load_config()
        
    def load_config(self):
        # Override with environment variables first
        self.gpu_api_key = os.getenv("PARITOK_API_KEY", self.gpu_api_key)
        
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r") as f:
                    config = yaml.safe_load(f)
                    if config:
                        self.use_gpu_server = config.get("use_gpu_server", self.use_gpu_server)
                        gpu_config = config.get("gpu_server", {})
                        if isinstance(gpu_config, dict):
                            self.gpu_api_key = gpu_config.get("api_key", self.gpu_api_key)
            except Exception as e:
                print(f"Error loading paritok.yaml: {e}")

        # Ensure environment keys take final precedence
        self.gpu_api_key = os.getenv("PARITOK_API_KEY", self.gpu_api_key)
        self.upstream_api_key = os.getenv("ANTHROPIC_API_KEY", self.upstream_api_key)

    def save_config(self):
        config_data = {
            "use_gpu_server": self.use_gpu_server,
            "gpu_server": {
                "api_key": self.gpu_api_key
            }
        }
        try:
            with open(CONFIG_PATH, "w") as f:
                yaml.safe_dump(config_data, f)
        except Exception as e:
            print(f"Error saving paritok.yaml: {e}")

settings = Settings()
