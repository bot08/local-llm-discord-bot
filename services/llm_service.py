import threading
from llama_cpp import Llama
from typing import Dict, List

class LLMService:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.conversations: Dict[str, List[dict]] = {}
        self.lock = threading.Lock()
        
    def initialize_model(self):
        with self.lock:
            if not self.model:
                self.model = Llama(
                    model_path=self.config.model_path,
                    n_ctx=self.config.model_params.get('n_ctx', 512),
                    n_gpu_layers=self.config.model_params.get('n_gpu_layers', 0),
                    verbose=self.config.full_log
                )
                print("LLM model initialized")

    def get_response(self, user_id, message):
        with self.lock:
            try:
                history = self.conversations.get(user_id, [])
                
                messages = [
                    {"role": "system", "content": self.config.system_prompt},
                    *history[-self.config.history_limit:],
                    {"role": "user", "content": message}
                ]

                print(f"Model config: {self.config.model_params}") if self.config.full_log else None

                completion_params = {
                    'messages': messages,
                    'stream': True,
                    'max_tokens': self.config.model_params.get('max_tokens'),
                    'temperature': self.config.model_params.get('temperature'),
                    'top_k': self.config.model_params.get('top_k'),
                    'top_p': self.config.model_params.get('top_p'),
                    'repeat_penalty': self.config.model_params.get('repeat_penalty')
                }

                stream = self.model.create_chat_completion(**completion_params)

                response_chunks = []
                for part in stream:
                    delta = part["choices"][0]["delta"]
                    if "content" in delta:
                        response_chunks.append(delta["content"])
                
                full_response = "".join(response_chunks)
                
                # Upd history
                new_history = history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": full_response}
                ]
                self.conversations[user_id] = new_history[-self.config.history_limit * 2 :]
                
                return response_chunks
                
            except Exception as e:
                self.conversations.pop(user_id, None)
                return [f"⚠️ Error: {str(e)}"]