import threading
from llama_cpp import Llama
from typing import Dict, List, Generator

class LLMService:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.conversations: Dict[str, List[dict]] = {}
        self.lock = threading.Lock()
        
    def initialize_model(self):
        if not self.model:
            self.model = Llama(
                model_path=self.config.model_path,
                chat_format=self.config.chat_format,
                n_ctx=self.config.model_params.get('n_ctx', 1024),
                n_gpu_layers=self.config.model_params.get('n_gpu_layers', 0),
                verbose=self.config.full_log
            )
            print("LLM model initialized")

    def get_response(self, user_id: str, message: str, username: str = None) -> Generator[str, None, None]:
        with self.lock:
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
                'stream': True,
                'max_tokens': self.config.model_params.get('max_tokens'),
                'temperature': self.config.model_params.get('temperature'),
                'top_k': self.config.model_params.get('top_k'),
                'top_p': self.config.model_params.get('top_p'),
                'repeat_penalty': self.config.model_params.get('repeat_penalty')
            }

            # Store chunks temporarily to build the full response for history
            response_chunks_for_history = []
            try:
                stream = self.model.create_chat_completion(**completion_params)

                for part in stream:
                    delta = part["choices"][0].get("delta", {})
                    chunk = delta.get("content")
                    if chunk: 
                        response_chunks_for_history.append(chunk)
                        yield chunk # Yield chunk to the caller

                # ---- History Update ----
                # This part executes only after the generator has been fully iterated by the caller
                full_response = "".join(response_chunks_for_history)
                
                # Update history if generation was successful
                new_history = history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": full_response}
                ]
                # Apply history limit
                self.conversations[user_id] = new_history[-(self.config.history_limit * 2):]

            except Exception as e:
                self.conversations.pop(user_id, None)
                return [f"⚠️ Error: {str(e)}"]

    def clear_history(self, user_id):
        with self.lock:
            if user_id in self.conversations:
                del self.conversations[user_id]
                return True
            return False