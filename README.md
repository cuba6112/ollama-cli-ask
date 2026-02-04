# Ollama CLI (ask)

A powerful command-line interface for Ollama that supports piping, interactive chat, and JSON output.

## Installation

1. Copy `ask.sh` to your bin path:
```bash
cp ask.sh /usr/local/bin/ask
chmod +x /usr/local/bin/ask
```

## Usage

```bash
# One-shot question
ask "How do I parse JSON in bash?"

# Interactive chat mode
ask

# Use a specific model
ask -m llama3 "Explain quantum physics"

# JSON output (useful for scripts)
ask --json "List 5 fruits"
```

## Features
- **Smart Context:** Remembers conversation history in interactive mode
- **Piping Support:** `cat file.txt | ask "Summarize this"`
- **Model Selection:** Switch models on the fly with `-m`
- **JSON Mode:** Returns raw JSON for programmatic use
