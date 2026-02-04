#!/usr/bin/env python3
import sys
import json
import argparse
import urllib.request
import os
import readline  # For better input handling (history, arrow keys)

# Default model
DEFAULT_MODEL = "qwen3-coder-next"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

class ChatSession:
    def __init__(self, model, system_prompt=None):
        self.model = model
        self.messages = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def add_user_message(self, content):
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content):
        self.messages.append({"role": "assistant", "content": content})

    def chat(self, stream=True, json_mode=False):
        url = f"{OLLAMA_HOST}/api/chat"
        data = {
            "model": self.model,
            "messages": self.messages,
            "stream": stream
        }
        
        if json_mode:
            data["format"] = "json"

        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )

        full_response = ""
        try:
            with urllib.request.urlopen(req) as response:
                if stream:
                    for line in response:
                        if line:
                            body = json.loads(line.decode('utf-8'))
                            if "message" in body:
                                content = body["message"].get("content", "")
                                print(content, end="", flush=True)
                                full_response += content
                            if body.get("done", False):
                                break
                    print() # Newline at end
                else:
                    body = json.loads(response.read().decode('utf-8'))
                    full_response = body["message"]["content"]
                    print(full_response)
            
            self.add_assistant_message(full_response)
            return full_response
                
        except urllib.error.URLError as e:
            print(f"\nError: Could not connect to Ollama at {url}")
            print(f"Details: {e}")
            return None

def interactive_mode(model, system_prompt, json_mode):
    print(f"🤖 Interactive Chat with {model}")
    print("Type 'exit', 'quit', or Ctrl+D to end. Type 'clear' to clear history.")
    if json_mode:
        print("📋 JSON mode enabled")
    print("-" * 40)

    session = ChatSession(model, system_prompt)

    while True:
        try:
            user_input = input(">>> ")
            if user_input.lower() in ('exit', 'quit'):
                break
            if user_input.lower() == 'clear':
                session = ChatSession(model, system_prompt)
                print("🧹 History cleared.")
                continue
            
            if not user_input.strip():
                continue

            session.add_user_message(user_input)
            session.chat(stream=True, json_mode=json_mode)

        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

def main():
    parser = argparse.ArgumentParser(description="Ask Ollama anything via CLI")
    parser.add_argument("prompt", nargs="*", help="The prompt to send (if empty, enters interactive mode)")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"Model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("-s", "--system", help="System prompt")
    parser.add_argument("--no-stream", action="store_false", dest="stream", help="Disable streaming output")
    parser.add_argument("--json", action="store_true", help="Force JSON output format")
    parser.add_argument("--ctx", type=int, help="Context window size (num_ctx)")
    
    args = parser.parse_args()

    # Handle piped input
    stdin_input = ""
    if not sys.stdin.isatty():
        stdin_input = sys.stdin.read().strip()

    # Determine mode
    prompt_text = " ".join(args.prompt)
    
    # If no prompt and no piped input -> Interactive Mode
    if not prompt_text and not stdin_input:
        interactive_mode(args.model, args.system, args.json)
        sys.exit(0)

    # One-shot mode
    final_content = ""
    if prompt_text:
        final_content += prompt_text
    if stdin_input:
        if final_content:
            final_content += "\n\nContext:\n"
        final_content += stdin_input

    session = ChatSession(args.model, args.system)
    session.add_user_message(final_content)
    session.chat(stream=args.stream, json_mode=args.json)

if __name__ == "__main__":
    main()
