from llama_cpp import Llama
from dotenv import load_dotenv
import os

load_dotenv()

model = None
conversation_history = []

SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT')
max_tokens = int(os.getenv('MAX_TOKENS', 128))
top_k = int(os.getenv('TOP_K', 40))
top_p = int(os.getenv('TOP_K', 90))
temperature = float(os.getenv('TEMPERATURE', 0.7))
repeat_penalty = float(os.getenv('REPEAT_PENALTY', 1.1))

def load_model():
    global model
    model_path = os.getenv('MODEL_PATH')
    n_gpu_layers = int(os.getenv('GPU_LAYERS', 0))
    n_ctx = int(os.getenv('MODEL_N_CTX', 512))

    if model is None:
        model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            n_parts=1,
            verbose=True,
        )
        print("Model loaded successfully")


def get_chat_response(msg, max_tokens=max_tokens, top_k=top_k, top_p=top_p, temperature=temperature, repeat_penalty=repeat_penalty):
    global model, conversation_history

    #print(max_tokens, top_k, top_p, temperature, repeat_penalty)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(conversation_history[-4:])
    messages.append({"role": "user", "content": msg})

    try:
        response_text = ""
        for part in model.create_chat_completion(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
            stream=True,
        ):
            delta = part["choices"][0]["delta"]
            if "content" in delta:
                response_text += delta["content"]

        conversation_history.append({"role": "user", "content": msg})
        conversation_history.append({"role": "assistant", "content": response_text})
        conversation_history = conversation_history[-4:]

        print(f"Message from Bot: {response_text}")
        return response_text

    except Exception as e:
        conversation_history = []
        return f"Error: {str(e)}"