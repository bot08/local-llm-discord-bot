import threading
from llama_cpp import Llama
from typing import Dict, List
from pathlib import Path
import importlib.util

class LLMService:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.functions = []
        self.function_handlers = {}
        self._load_plugins()
        self.conversations: Dict[str, List[dict]] = {}
        self.lock = threading.Lock()
        print(self.functions)
        print(self.function_handlers)
        
    def _load_plugins(self):
        plugins_dir = Path(__file__).parent.parent / Path(self.config.plugins_dir)
        for plugin_file in plugins_dir.glob('*.py'):
            spec = importlib.util.spec_from_file_location(plugin_file.stem, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'get_functions'):
                self.functions.extend(module.get_functions())
            
            if hasattr(module, 'handle_function_call'):
                self.function_handlers.update({
                    func['function']['name']: module.handle_function_call
                    for func in module.get_functions()
                })

    def initialize_model(self):
        with self.lock:
            if not self.model:
                self.model = Llama(
                    model_path=self.config.model_path,
                    chat_format=self.config.chat_format,
                    n_ctx=self.config.model_params.get('n_ctx', 1024),
                    n_gpu_layers=self.config.model_params.get('n_gpu_layers', 0),
                    verbose=self.config.full_log
                )
                print("LLM model initialized")

    def get_response(self, user_id, message, username=None):
        with self.lock:
            try:
                history = self.conversations.get(user_id, [])
                
                messages = [
                    {"role": "system", "content": self.config.system_prompt.replace("[user]", username or "user")},
                    *history[-self.config.history_limit:],
                    {"role": "user", "content": message}
                ]

                print(f"Model config: {self.config.model_params}") if self.config.full_log else None
                print(f"History: {messages}") if self.config.full_log else None

                completion_params = {
                    'messages': messages,
                    'tools': self.functions,
                    'tool_choice': "auto",
                    'stream': self.config.stream_mode,
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
                
                # Update history
                new_history = history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": full_response}
                ]
                self.conversations[user_id] = new_history[-self.config.history_limit * 2 :]
                
                return response_chunks
                
            except Exception as e:
                self.conversations.pop(user_id, None)
                return [f"⚠️ Error: {str(e)}"]
            
    def clear_history(self, user_id):
        with self.lock:
            if user_id in self.conversations:
                del self.conversations[user_id]
                return True
            return False