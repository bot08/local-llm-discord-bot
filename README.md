# Local LLM Discord Bot Interface

A lightweight Discord bot interface for interacting with locally-hosted language models. Supports conversation history, streaming responses, and custom configurations.

---

## Core Features

- **DM-Only Interactions**: Restrict bot usage to private messages
- **Context-Aware Chat**: Maintains limited conversation history per user
- **Message Chunking**: Automatically splits long responses (>2000 chars)
- **GPU Acceleration**: Configure offloading layers for performance
- **Streaming Mode**: Real-time token delivery with typing simulation
- **Custom Prompts**: Modify system behavior via `SYSTEM_PROMPT`
- **Thread Safety**: Prevents race conditions with user-level locks

---

## Setup Guide

1. **Install Requirements**:
    ```bash
    pip install discord.py llama-cpp-python python-dotenv
    ```

2. **Create `.env`**:
    ```env
    DISCORD_TOKEN=TOKEN
    MODEL_PATH=Llama-3.1-8B-Q4_K_L.gguf
    # Required parameters above. Optional below:
    COMMAND_PREFIX=!
    FULL_LOG=FALSE
    MODEL_N_CTX=512
    MAX_TOKENS=128
    TOP_K=40
    TOP_P=0.95
    TEMPERATURE=0.7
    REPEAT_PENALTY=1.1
    GPU_LAYERS=7
    ONLY_DM=TRUE
    HISTORY_LIMIT=3
    STREAM_MODE=FALSE
    SYSTEM_PROMPT=You are a helpful assistant. Answer as concisely as possible.
    ```

3. **Run Bot**:
    ```bash
    python main.py
    ```

---

## Full .env Configuration

| Parameter             | Type     | Description                                      | Default               |
|-----------------------|----------|--------------------------------------------------|-----------------------|
| `DISCORD_TOKEN`       | String   | **Required** Discord bot token                  | -                     |
| `COMMAND_PREFIX`      | String   | Bot command prefix                              | `!`                   |
| `FULL_LOG`            | Boolean  | Enable verbose logging                          | `FALSE`               |
| `MODEL_PATH`          | String   | **Required** Path to GGUF model file            | -                     |
| `MODEL_N_CTX`         | Integer  | Context window size                             | `1024`                |
| `MAX_TOKENS`          | Integer  | Maximum tokens per response                     | `256`                 |
| `TOP_K`               | Integer  | Top-k sampling                                  | `40`                  |
| `TOP_P`               | Float    | Top-p sampling                                  | `0.95`                |
| `TEMPERATURE`         | Float    | Response randomness (0.1-2.0)                   | `0.7`                 |
| `REPEAT_PENALTY`      | Float    | Penalize repeated phrases                       | `1.1`                 |
| `GPU_LAYERS`          | Integer  | GPU offloading layers (0=CPU-only)              | `0`                   |
| `ONLY_DM`             | Boolean  | Bot responds only in DMs                        | `TRUE`                |
| `HISTORY_LIMIT`       | Integer  | Max stored message pairs (user+assistant)       | `3`                   |
| `STREAM_MODE`         | Boolean  | Enable real-time token streaming                | `FALSE`               |
| `SYSTEM_PROMPT`       | String   | Initial assistant behavior prompt               | `You are a helpful...`|

---

## TODO

- **Stream fix**:
  - Fix generation interruption caused by Discord API rate limits
  - Implement adaptive delay between token sends
- **History System**:
  - Add `!clearhistory` command to reset conversations