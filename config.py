import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.discord_token = self._get_env('DISCORD_TOKEN')
        self.full_log = os.getenv('FULL_LOG', 'false').lower() == 'true'
        self.model_path = self._validate_path(os.getenv('MODEL_PATH'))
        self.system_prompt = os.getenv('SYSTEM_PROMPT', 'You are a helpful assistant')
        self.history_limit = int(os.getenv('HISTORY_LIMIT', 6))
        self.stream_mode = os.getenv('STREAM_MODE', 'false').lower() == 'true'
        
        self.model_params = {
            'n_ctx': int(os.getenv('MODEL_N_CTX', 512)),
            'n_gpu_layers': int(os.getenv('GPU_LAYERS', 0)),
            'max_tokens': int(os.getenv('MAX_TOKENS', 128)),
            'temperature': float(os.getenv('TEMPERATURE', 0.7)),
            'top_k': int(os.getenv('TOP_K', 40)),
            'top_p': float(os.getenv('TOP_P', 0.95)),
            'repeat_penalty': float(os.getenv('REPEAT_PENALTY', 1.1))
        }
        
        self.bot_config = {
            'only_dm': os.getenv('ONLY_DM', 'true').lower() == 'true',
            'command_prefix': os.getenv('COMMAND_PREFIX', '!')
        }

    def _get_env(self, name):
        value = os.getenv(name)
        if not value:
            raise ValueError(f"Missing required env var: {name}")
        return value

    def _validate_path(self, path):
        if not Path(path).exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        return path