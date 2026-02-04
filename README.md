# Ollama CLI (ask)

A powerful command-line interface for Ollama that supports piping, interactive chat, session history, and JSON output.

## Quick Start

**For Agents/Scripts:** Use `ask_simple.py` - minimal, encoding-safe, works in piped environments.

**For Humans:** Use `ask.py` - full-featured with colors, streaming, and interactive mode.

## Installation

### Unix/macOS
```bash
cp ask.py /usr/local/bin/ask
chmod +x /usr/local/bin/ask

# For agent use:
cp ask_simple.py /usr/local/bin/ask-simple
chmod +x /usr/local/bin/ask-simple
```

### Windows
```powershell
# Add to PATH or create alias
Copy-Item ask.py C:\Tools\ask.py
Copy-Item ask_simple.py C:\Tools\ask_simple.py
# Add C:\Tools to PATH, or use:
Set-Alias ask "python C:\Tools\ask.py"
Set-Alias ask-simple "python C:\Tools\ask_simple.py"
```

## Usage

### One-shot queries
```bash
# Human version (with colors, streaming)
ask "How do I parse JSON in bash?"

# Agent version (clean output, no colors)
python ask_simple.py "How do I parse JSON in bash?"
```

### Agent/Script Usage (ask_simple.py)
```bash
# Simple query
python ask_simple.py "What is 2+2?"

# Specific model
python ask_simple.py -m gpt-oss:latest "Explain this code"

# With system prompt
python ask_simple.py -s "You are a code reviewer" "Review: def foo(): pass"

# JSON output
python ask_simple.py --json "List 5 fruits as JSON array"

# Output to file
python ask_simple.py "Generate a Python script" -o script.py

# Piped input
cat code.py | python ask_simple.py "Explain this"
```

### Human Usage (ask.py)
```bash
# Interactive chat mode
ask

# Enable thinking/reasoning mode
ask -t "Think step by step about this problem"

# With temperature
ask --temp 0.7 "Be creative and write a poem"

# List available models
ask --list-models
```

## Features

### ask_simple.py (for agents)
- ✅ Clean ASCII output (no encoding issues)
- ✅ Non-streaming (waits for full response)
- ✅ File output with `-o`
- ✅ Works in piped/subprocess environments
- ✅ Minimal dependencies

### ask.py (for humans)
- 🎨 Color output (respects `NO_COLOR`)
- 📺 Streaming responses
- 💬 Interactive chat mode
- 💾 Session save/load
- 🧠 Thinking mode visualization
- 🌡️ Temperature control

## Interactive Mode Commands (ask.py)

| Command | Description |
|---------|-------------|
| `exit`, `quit`, `q` | Exit the chat |
| `clear` | Clear conversation history |
| `save [name]` | Save session to file |
| `load <name>` | Load a previous session |
| `models` | List available models |
| `help` | Show help |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ASK_MODEL` | `gpt-oss:latest` | Default model |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `NO_COLOR` | (unset) | Disable colored output |

## Examples

### Code Review
```bash
git diff | python ask_simple.py "Review these changes"
```

### Explain Code
```bash
cat complex_function.py | python ask_simple.py "Explain what this does"
```

### Generate Tests
```bash
cat mymodule.py | python ask_simple.py --json "Generate pytest test cases as JSON"
```

## Requirements

- Python 3.8+
- Ollama running locally (or accessible via `OLLAMA_HOST`)
- Optional: `pyreadline3` for better Windows input handling (ask.py only)
