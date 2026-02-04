#!/usr/bin/env python3
"""
Ollama CLI (ask) - A powerful command-line interface for Ollama
Supports piping, interactive chat, JSON output, and conversation history.
"""
import sys
import json
import argparse
import urllib.request
import urllib.error
import os
import re
import io
from pathlib import Path
from datetime import datetime

# Agent mode: strip emoji/unicode for clean piped output
AGENT_MODE = os.getenv("ASK_AGENT_MODE", "").lower() in ("1", "true", "yes") or not sys.stdout.isatty()

# Fix Windows console encoding for emoji/unicode
if sys.platform == 'win32':
    # Force UTF-8 with replace for piped output on Windows
    try:
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', newline='')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', newline='')
    except Exception:
        pass  # Fallback to default encoding

def safe_print(text, end='\n', flush=False):
    """Print with encoding safety for agents/piped output"""
    if AGENT_MODE:
        # Strip emoji and problematic unicode for agent consumption
        text = text.encode('ascii', errors='ignore').decode('ascii')
    try:
        print(text, end=end, flush=flush)
    except UnicodeEncodeError:
        # Last resort: strip to ASCII
        print(text.encode('ascii', errors='ignore').decode('ascii'), end=end, flush=flush)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Try readline for better input (Unix) or pyreadline3 (Windows)
try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline
    except ImportError:
        readline = None  # Graceful degradation

# Configuration
DEFAULT_MODEL = os.getenv("ASK_MODEL", "qwen3-coder-next")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
HISTORY_DIR = Path.home() / ".ask_history"
MAX_HISTORY_SESSIONS = 50

# ANSI colors (disabled on Windows without colorama or if NO_COLOR set)
COLORS_ENABLED = sys.stdout.isatty() and not os.getenv("NO_COLOR")
class Colors:
    CYAN = "\033[96m" if COLORS_ENABLED else ""
    GREEN = "\033[92m" if COLORS_ENABLED else ""
    YELLOW = "\033[93m" if COLORS_ENABLED else ""
    RED = "\033[91m" if COLORS_ENABLED else ""
    DIM = "\033[2m" if COLORS_ENABLED else ""
    BOLD = "\033[1m" if COLORS_ENABLED else ""
    RESET = "\033[0m" if COLORS_ENABLED else ""


class ChatSession:
    def __init__(self, model, system_prompt=None, num_ctx=None, temperature=None):
        self.model = model
        self.messages = []
        self.num_ctx = num_ctx
        self.temperature = temperature
        self.total_tokens = 0
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def add_user_message(self, content):
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content):
        self.messages.append({"role": "assistant", "content": content})

    def chat(self, stream=True, json_mode=False, thinking=False):
        url = f"{OLLAMA_HOST}/api/chat"
        data = {
            "model": self.model,
            "messages": self.messages,
            "stream": stream
        }
        
        if json_mode:
            data["format"] = "json"
        
        options = {}
        if self.num_ctx:
            options["num_ctx"] = self.num_ctx
        if self.temperature is not None:
            options["temperature"] = self.temperature
        if options:
            data["options"] = options
        
        # Note: Ollama API doesn't standardly support 'think' param in body yet for most models,
        # but some custom reasoning models might use prompt tokens. 
        # DeepSeek-R1 style models put thinking in <think> tags naturally.

        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )

        full_response = ""
        thinking_content = ""
        in_thinking = False
        
        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                if stream:
                    for line in response:
                        if line:
                            try:
                                body = json.loads(line.decode('utf-8'))
                            except json.JSONDecodeError:
                                continue
                                
                            if "message" in body:
                                content = body["message"].get("content", "")
                                
                                # Handle thinking blocks (<think>...</think>)
                                # We need to handle split tags across chunks too, but simple approach first
                                
                                # Check for start tag
                                if "<think>" in content:
                                    in_thinking = True
                                    parts = content.split("<think>")
                                    pre_think = parts[0]
                                    post_think = parts[1]
                                    
                                    if pre_think:
                                        safe_print(pre_think, end="", flush=True)
                                        full_response += pre_think
                                    
                                    if COLORS_ENABLED and not AGENT_MODE:
                                        safe_print(f"{Colors.DIM}[thinking] ", end="", flush=True)
                                    
                                    content = post_think # Process remainder as thinking

                                # Check for end tag
                                if "</think>" in content:
                                    in_thinking = False
                                    parts = content.split("</think>")
                                    think_part = parts[0]
                                    rest_part = parts[1] if len(parts) > 1 else ""
                                    
                                    thinking_content += think_part
                                    if COLORS_ENABLED and not AGENT_MODE:
                                        safe_print(f"{think_part}{Colors.RESET}\n", end="", flush=True)
                                    
                                    content = rest_part # Process remainder as normal content
                                
                                if in_thinking:
                                    thinking_content += content
                                    if COLORS_ENABLED and not AGENT_MODE:
                                        safe_print(content, end="", flush=True)
                                else:
                                    safe_print(content, end="", flush=True)
                                    full_response += content
                                    
                            if body.get("done", False):
                                # Capture token stats
                                if "eval_count" in body:
                                    self.total_tokens += body.get("eval_count", 0)
                                break
                    safe_print("")  # Newline at end
                else:
                    body = json.loads(response.read().decode('utf-8'))
                    full_response = body["message"]["content"]
                    safe_print(full_response)
            
            self.add_assistant_message(full_response)
            return full_response
                
        except urllib.error.URLError as e:
            safe_print(f"\nError: Could not connect to Ollama at {OLLAMA_HOST}")
            safe_print(f"Details: {e}")
            safe_print(f"\nTip: Is Ollama running? Try: ollama serve")
            return None
        except TimeoutError:
            safe_print(f"\nError: Request timed out")
            return None
        except KeyboardInterrupt:
            safe_print(f"\n(Request cancelled)")
            return None


def list_models():
    """List available Ollama models"""
    url = f"{OLLAMA_HOST}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            models = data.get("models", [])
            if not models:
                safe_print("No models found. Pull one with: ollama pull <model>")
                return
            
            if not AGENT_MODE:
                safe_print(f"{Colors.CYAN}Available models:{Colors.RESET}\n")
            else:
                safe_print("Available models:\n")
            # Sort models by name
            models.sort(key=lambda x: x['name'])
            
            for m in models:
                name = m["name"]
                size_gb = m.get("size", 0) / (1024**3)
                modified = m.get("modified_at", "")[:10]
                
                # Check if it matches default
                is_default = name == DEFAULT_MODEL or name.split(":")[0] == DEFAULT_MODEL.split(":")[0]
                
                if AGENT_MODE:
                    # Plain output for agents
                    marker = " (default)" if is_default else ""
                    safe_print(f"  {name:<30} {size_gb:>5.1f}GB  {modified}{marker}")
                else:
                    marker = f" {Colors.YELLOW}(default){Colors.RESET}" if is_default else ""
                    # Colorize size
                    size_color = Colors.DIM
                    if size_gb > 10: size_color = Colors.RED
                    elif size_gb > 5: size_color = Colors.YELLOW
                    elif size_gb < 1: size_color = Colors.GREEN
                    safe_print(f"  {Colors.BOLD}{name:<30}{Colors.RESET} {size_color}{size_gb:>5.1f}GB{Colors.RESET}  {Colors.DIM}{modified}{Colors.RESET}{marker}")
    except Exception as e:
        safe_print(f"Error listing models: {e}")


def save_session(session, name=None):
    """Save conversation to history"""
    HISTORY_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize name
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', name) if name else timestamp
    filename = f"{safe_name}.json"
    
    with open(HISTORY_DIR / filename, "w") as f:
        json.dump({
            "model": session.model,
            "messages": session.messages,
            "saved_at": datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"{Colors.DIM}Session saved to {filename}{Colors.RESET}")
    
    # Cleanup old sessions
    sessions = sorted(HISTORY_DIR.glob("*.json"), key=os.path.getmtime)
    if len(sessions) > MAX_HISTORY_SESSIONS:
        for old in sessions[:-MAX_HISTORY_SESSIONS]:
            old.unlink()


def load_session(name):
    """Load a previous conversation"""
    path = HISTORY_DIR / f"{name}.json"
    if not path.exists():
        # Try partial match (most recent first)
        matches = sorted(HISTORY_DIR.glob(f"*{name}*.json"), key=os.path.getmtime, reverse=True)
        if matches:
            path = matches[0]
        else:
            print(f"{Colors.RED}Session '{name}' not found{Colors.RESET}")
            return None
    
    with open(path) as f:
        data = json.load(f)
    
    session = ChatSession(data["model"])
    session.messages = data["messages"]
    print(f"{Colors.GREEN}Loaded session from {path.name} ({len(session.messages)} messages){Colors.RESET}")
    
    # Replay last few messages context
    print(f"{Colors.DIM}Last context:{Colors.RESET}")
    for msg in session.messages[-2:]:
        role = msg["role"]
        content = msg["content"][:100].replace("\n", " ") + "..."
        print(f"  {Colors.BOLD}{role}:{Colors.RESET} {content}")
    print("-" * 50)
        
    return session


def interactive_mode(model, system_prompt, json_mode, thinking=False, load_from=None):
    # Banner
    print(f"{Colors.CYAN}🤖 Interactive Chat with {Colors.BOLD}{model}{Colors.RESET}")
    print(f"{Colors.DIM}Type 'help' for commands, 'quit' to exit.{Colors.RESET}")
    
    if json_mode:
        print(f"{Colors.YELLOW}📋 JSON mode enabled{Colors.RESET}")
    if thinking:
        print(f"{Colors.YELLOW}💭 Thinking mode enabled{Colors.RESET}")
    print("-" * 50)

    session = None
    if load_from:
        session = load_session(load_from)
    
    if not session:
        session = ChatSession(model, system_prompt)

    while True:
        try:
            # Fancy prompt
            prompt_str = f"{Colors.GREEN}>>> {Colors.RESET}"
            if load_from:
                prompt_str = f"{Colors.GREEN}[{load_from}] >>> {Colors.RESET}"
                
            user_input = input(prompt_str)
            cmd = user_input.lower().strip()
            
            if cmd in ('exit', 'quit', 'q'):
                break
            if cmd == 'clear':
                session = ChatSession(model, system_prompt)
                print(f"{Colors.YELLOW}🧹 History cleared.{Colors.RESET}")
                continue
            if cmd.startswith('save'):
                parts = cmd.split(maxsplit=1)
                name = parts[1] if len(parts) > 1 else None
                save_session(session, name)
                if name: load_from = name # Switch context to saved name
                continue
            if cmd.startswith('load '):
                name = cmd.split(maxsplit=1)[1]
                loaded = load_session(name)
                if loaded:
                    session = loaded
                    load_from = name
                continue
            if cmd == 'models':
                list_models()
                continue
            if cmd.startswith('model '):
                new_model = cmd.split(maxsplit=1)[1]
                session.model = new_model
                model = new_model
                print(f"{Colors.YELLOW}Switched to model: {model}{Colors.RESET}")
                continue
            if cmd == 'history':
                print(f"{Colors.CYAN}Saved sessions:{Colors.RESET}")
                sessions = sorted(HISTORY_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
                for s in sessions[:10]:
                    print(f"  {s.stem} ({datetime.fromtimestamp(s.stat().st_mtime).strftime('%Y-%m-%d %H:%M')})")
                continue
                
            if cmd == 'help':
                print(f"""
{Colors.CYAN}Commands:{Colors.RESET}
  exit, quit, q     Exit the chat
  clear             Clear conversation history
  save [name]       Save session to file
  load <name>       Load a previous session
  history           List recent saved sessions
  models            List available models
  model <name>      Switch model
  help              Show this help

{Colors.CYAN}Tips:{Colors.RESET}
  - Use Ctrl+C to cancel a response
  - Pipe input: cat file.txt | ask "summarize"
  - Set default model: export ASK_MODEL=llama3
""")
                continue
            
            if not user_input.strip():
                continue
            
            # Allow multiline input if ends with \
            while user_input.strip().endswith('\\'):
                user_input = user_input.rstrip('\\') + "\n" + input(f"{Colors.GREEN}... {Colors.RESET}")

            session.add_user_message(user_input)
            session.chat(stream=True, json_mode=json_mode, thinking=thinking)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}(interrupted){Colors.RESET}")
            continue
        except EOFError:
            print("\nExiting...")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Ask Ollama anything via CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ask "How do I parse JSON in bash?"
  ask -m llama3 "Explain quantum physics"
  cat file.txt | ask "Summarize this"
  ask --json "List 5 fruits as JSON array"
  ask -t "Think step by step about this problem"
  ask  # Enter interactive mode
"""
    )
    parser.add_argument("prompt", nargs="*", help="The prompt to send (if empty, enters interactive mode)")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"Model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("-s", "--system", help="System prompt")
    parser.add_argument("-t", "--think", action="store_true", help="Enable thinking/reasoning mode (DeepSeek style)")
    parser.add_argument("--no-stream", action="store_false", dest="stream", help="Disable streaming output")
    parser.add_argument("--json", action="store_true", help="Force JSON output format")
    parser.add_argument("--ctx", type=int, help="Context window size (num_ctx)")
    parser.add_argument("--temp", type=float, help="Temperature (0.0-2.0, default varies by model)")
    parser.add_argument("--load", metavar="NAME", help="Load a previous session")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    parser.add_argument("-o", "--output", metavar="FILE", help="Write output to file (bypasses stdout encoding)")
    parser.add_argument("-v", "--version", action="store_true", help="Show version info")
    parser.add_argument("--debug", action="store_true", help="Show debug info on errors")
    
    args = parser.parse_args()

    # Handle --version
    if args.version:
        print(f"ask v1.1.0 - Ollama CLI")
        print(f"Host: {OLLAMA_HOST}")
        print(f"Default model: {DEFAULT_MODEL}")
        sys.exit(0)

    # Handle --list-models
    if args.list_models:
        list_models()
        sys.exit(0)

    # Handle piped input
    stdin_input = ""
    if not sys.stdin.isatty():
        try:
            stdin_input = sys.stdin.read().strip()
        except Exception:
            pass

    # Determine mode
    prompt_text = " ".join(args.prompt)
    
    # If no prompt and no piped input -> Interactive Mode
    if not prompt_text and not stdin_input:
        interactive_mode(args.model, args.system, args.json, args.think, args.load)
        sys.exit(0)

    # One-shot mode
    final_content = ""
    if prompt_text:
        final_content += prompt_text
    if stdin_input:
        if final_content:
            final_content += "\n\nContext:\n"
        final_content += stdin_input

    session = ChatSession(args.model, args.system, args.ctx, args.temp)
    session.add_user_message(final_content)
    
    # If output file specified, capture result and write to file
    if args.output:
        # Use non-streaming for file output
        result = session.chat(stream=False, json_mode=args.json, thinking=args.think)
        if result:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            safe_print(f"Output written to {args.output}")
    else:
        result = session.chat(stream=args.stream, json_mode=args.json, thinking=args.think)
    
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Catch-all for encoding errors and other issues
        sys.stderr.write(f"Error: {str(e).encode('ascii', errors='replace').decode('ascii')}\n")
        sys.exit(1)
