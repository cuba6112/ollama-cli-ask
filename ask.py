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
from pathlib import Path
from datetime import datetime

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
    RESET = "\033[0m" if COLORS_ENABLED else ""


class ChatSession:
    def __init__(self, model, system_prompt=None, num_ctx=None):
        self.model = model
        self.messages = []
        self.num_ctx = num_ctx
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
        
        if self.num_ctx:
            data["options"] = {"num_ctx": self.num_ctx}
        
        if thinking:
            data["think"] = True

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
                            body = json.loads(line.decode('utf-8'))
                            if "message" in body:
                                content = body["message"].get("content", "")
                                
                                # Handle thinking blocks
                                if "<think>" in content:
                                    in_thinking = True
                                    content = content.replace("<think>", "")
                                    if COLORS_ENABLED:
                                        print(f"{Colors.DIM}💭 ", end="", flush=True)
                                
                                if "</think>" in content:
                                    in_thinking = False
                                    parts = content.split("</think>")
                                    thinking_content += parts[0]
                                    if COLORS_ENABLED:
                                        print(f"{Colors.RESET}\n", end="", flush=True)
                                    content = parts[1] if len(parts) > 1 else ""
                                
                                if in_thinking:
                                    thinking_content += content
                                    if COLORS_ENABLED:
                                        print(f"{Colors.DIM}{content}{Colors.RESET}", end="", flush=True)
                                else:
                                    print(content, end="", flush=True)
                                    full_response += content
                                    
                            if body.get("done", False):
                                # Capture token stats
                                if "eval_count" in body:
                                    self.total_tokens += body.get("eval_count", 0)
                                break
                    print()  # Newline at end
                else:
                    body = json.loads(response.read().decode('utf-8'))
                    full_response = body["message"]["content"]
                    print(full_response)
            
            self.add_assistant_message(full_response)
            return full_response
                
        except urllib.error.URLError as e:
            print(f"\n{Colors.RED}Error: Could not connect to Ollama at {OLLAMA_HOST}{Colors.RESET}")
            print(f"Details: {e}")
            print(f"\n{Colors.YELLOW}Tip: Is Ollama running? Try: ollama serve{Colors.RESET}")
            return None
        except TimeoutError:
            print(f"\n{Colors.RED}Error: Request timed out{Colors.RESET}")
            return None


def list_models():
    """List available Ollama models"""
    url = f"{OLLAMA_HOST}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            models = data.get("models", [])
            if not models:
                print("No models found. Pull one with: ollama pull <model>")
                return
            
            print(f"{Colors.CYAN}Available models:{Colors.RESET}\n")
            for m in models:
                name = m["name"]
                size = m.get("size", 0) / (1024**3)  # Convert to GB
                modified = m.get("modified_at", "")[:10]
                marker = " (default)" if name.split(":")[0] == DEFAULT_MODEL.split(":")[0] else ""
                print(f"  {Colors.GREEN}{name}{Colors.RESET} ({size:.1f}GB, {modified}){Colors.YELLOW}{marker}{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}Error listing models: {e}{Colors.RESET}")


def save_session(session, name=None):
    """Save conversation to history"""
    HISTORY_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name or timestamp}.json"
    
    with open(HISTORY_DIR / filename, "w") as f:
        json.dump({
            "model": session.model,
            "messages": session.messages,
            "saved_at": datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"{Colors.DIM}Session saved to {filename}{Colors.RESET}")
    
    # Cleanup old sessions
    sessions = sorted(HISTORY_DIR.glob("*.json"))
    if len(sessions) > MAX_HISTORY_SESSIONS:
        for old in sessions[:-MAX_HISTORY_SESSIONS]:
            old.unlink()


def load_session(name):
    """Load a previous conversation"""
    path = HISTORY_DIR / f"{name}.json"
    if not path.exists():
        # Try partial match
        matches = list(HISTORY_DIR.glob(f"*{name}*.json"))
        if matches:
            path = matches[-1]  # Most recent match
        else:
            print(f"{Colors.RED}Session '{name}' not found{Colors.RESET}")
            return None
    
    with open(path) as f:
        data = json.load(f)
    
    session = ChatSession(data["model"])
    session.messages = data["messages"]
    print(f"{Colors.GREEN}Loaded session from {path.name} ({len(session.messages)} messages){Colors.RESET}")
    return session


def interactive_mode(model, system_prompt, json_mode, thinking=False, load_from=None):
    print(f"{Colors.CYAN}🤖 Interactive Chat with {model}{Colors.RESET}")
    print("Commands: exit/quit, clear, save [name], load <name>, models, help")
    if json_mode:
        print(f"{Colors.YELLOW}📋 JSON mode enabled{Colors.RESET}")
    if thinking:
        print(f"{Colors.YELLOW}💭 Thinking mode enabled{Colors.RESET}")
    print("-" * 50)

    if load_from:
        session = load_session(load_from)
        if not session:
            session = ChatSession(model, system_prompt)
    else:
        session = ChatSession(model, system_prompt)

    while True:
        try:
            user_input = input(f"{Colors.GREEN}>>> {Colors.RESET}")
            cmd = user_input.lower().strip()
            
            if cmd in ('exit', 'quit', 'q'):
                break
            if cmd == 'clear':
                session = ChatSession(model, system_prompt)
                print(f"{Colors.YELLOW}🧹 History cleared.{Colors.RESET}")
                continue
            if cmd.startswith('save'):
                parts = cmd.split(maxsplit=1)
                save_session(session, parts[1] if len(parts) > 1 else None)
                continue
            if cmd.startswith('load '):
                name = cmd.split(maxsplit=1)[1]
                loaded = load_session(name)
                if loaded:
                    session = loaded
                continue
            if cmd == 'models':
                list_models()
                continue
            if cmd == 'help':
                print(f"""
{Colors.CYAN}Commands:{Colors.RESET}
  exit, quit, q     Exit the chat
  clear             Clear conversation history
  save [name]       Save session to file
  load <name>       Load a previous session
  models            List available models
  help              Show this help

{Colors.CYAN}Tips:{Colors.RESET}
  - Use Ctrl+C to cancel a response
  - Pipe input: cat file.txt | ask "summarize"
  - Set default model: export ASK_MODEL=llama3
""")
                continue
            
            if not user_input.strip():
                continue

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
    parser.add_argument("-t", "--think", action="store_true", help="Enable thinking/reasoning mode")
    parser.add_argument("--no-stream", action="store_false", dest="stream", help="Disable streaming output")
    parser.add_argument("--json", action="store_true", help="Force JSON output format")
    parser.add_argument("--ctx", type=int, help="Context window size (num_ctx)")
    parser.add_argument("--load", metavar="NAME", help="Load a previous session")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    
    args = parser.parse_args()

    # Handle --list-models
    if args.list_models:
        list_models()
        sys.exit(0)

    # Handle piped input
    stdin_input = ""
    if not sys.stdin.isatty():
        stdin_input = sys.stdin.read().strip()

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

    session = ChatSession(args.model, args.system, args.ctx)
    session.add_user_message(final_content)
    result = session.chat(stream=args.stream, json_mode=args.json, thinking=args.think)
    
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
