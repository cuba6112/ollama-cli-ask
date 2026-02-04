# Ollama CLI (ask)

A powerful command-line interface for Ollama that supports piping, interactive chat, session history, and JSON output.

## Installation

### Unix/macOS
```bash
cp ask.py /usr/local/bin/ask
chmod +x /usr/local/bin/ask
```

### Windows
```powershell
# Add to PATH or create alias
Copy-Item ask.py C:\Tools\ask.py
# Add C:\Tools to PATH, or use:
Set-Alias ask "python C:\Tools\ask.py"
```

## Usage

```bash
# One-shot question
ask "How do I parse JSON in bash?"

# Interactive chat mode
ask

# Use a specific model
ask -m llama3 "Explain quantum physics"

# Enable thinking/reasoning mode
ask -t "Think step by step about this problem"

# JSON output (useful for scripts)
ask --json "List 5 fruits as JSON array"

# Pipe content
cat file.txt | ask "Summarize this"
echo "def foo(): pass" | ask "Review this code"

# List available models
ask --list-models

# With system prompt
ask -s "You are a Python expert" "How do I use asyncio?"
```

## Features

- **Smart Context:** Remembers conversation history in interactive mode
- **Piping Support:** `cat file.txt | ask "Summarize this"`
- **Model Selection:** Switch models on the fly with `-m`
- **JSON Mode:** Returns structured JSON for programmatic use
- **Thinking Mode:** Enable reasoning with `-t` for complex problems
- **Session Save/Load:** Persist conversations across sessions
- **Color Output:** Pretty terminal output (respects `NO_COLOR`)
- **Cross-Platform:** Works on Unix, macOS, and Windows

## Interactive Mode Commands

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
| `ASK_MODEL` | `qwen3-coder-next` | Default model to use |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `NO_COLOR` | (unset) | Disable colored output |

## Session History

Sessions are saved to `~/.ask_history/` as JSON files. The last 50 sessions are kept automatically.

```bash
# Save current session
>>> save my-project

# Later, load it back
ask --load my-project
# or in interactive mode:
>>> load my-project
```

## Examples

### Code Review
```bash
git diff | ask "Review these changes"
```

### Explain Code
```bash
cat complex_function.py | ask "Explain what this does"
```

### Generate Tests
```bash
cat mymodule.py | ask --json "Generate pytest test cases as JSON"
```

### Thinking Mode for Complex Problems
```bash
ask -t "Design a distributed cache system with these requirements: ..."
```

## Requirements

- Python 3.8+
- Ollama running locally (or accessible via `OLLAMA_HOST`)
- Optional: `pyreadline3` for better Windows input handling
