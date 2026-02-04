---
name: ollama-cli-ask
description: Use the local 'ask' CLI to interact with Ollama models. Supports one-shot queries, interactive chat, piping context, and JSON output.
purpose: Fast, local LLM inference without cloud costs or latency.
usage: |
  # One-shot
  ask "Question"
  
  # Pipe context
  cat file.txt | ask "Summarize this"
  
  # Interactive
  ask
  
  # Specific model
  ask -m qwen3-coder-next "Code me a snake game"
  
  # Reasoning/Thinking mode
  ask -t "Think step by step"
parameters:
  - prompt: The prompt to send (optional, enters interactive mode if empty)
  - model: (Optional) Model to use (default: qwen3-coder-next)
  - system: (Optional) System prompt
  - think: (Optional) Enable thinking/reasoning mode
  - json: (Optional) Force JSON output
dependencies:
  - ollama (running)
  - ~/bin/ask (installed CLI)
created: 2026-02-04
---

# Ollama CLI (ask) Skill 🦑

This skill leverages the `ask` CLI tool to interact with local Ollama models. It's faster and more flexible than raw curl requests.

## Features
- **Context-aware:** Remembers conversation history in interactive mode.
- **Piping:** Can ingest file content or command output via stdin.
- **Thinking:** Supports `<think>` tag parsing for reasoning models (DeepSeek, etc).
- **JSON:** reliable JSON output for tool use.

## Installation (if missing)
```bash
cp ~/clawd/tools/ollama-cli/ask.sh ~/bin/ask
chmod +x ~/bin/ask
```

## Recommended Models
- **Coding:** `qwen3-coder-next` (Smartest local coder)
- **General:** `llama3.1:8b` (Fast, good generalist)
- **Reasoning:** `deepseek-r1` (if available, use `-t` flag)

## Examples

**Summarize a file:**
```bash
cat MEMORY.md | ask "Extract the key user preferences"
```

**Generate JSON data:**
```bash
ask --json "List 5 sci-fi book titles and authors"
```

**Complex Reasoning:**
```bash
ask -t "Solve this logic puzzle: Three gods A, B, and C are called..."
```
