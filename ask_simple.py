#!/usr/bin/env python3
"""
ask_simple.py - Minimal Ollama CLI for agent use
Designed for piped/non-interactive environments
"""
import sys
import json
import argparse
import urllib.request
import urllib.error
import os

# Configuration
DEFAULT_MODEL = os.getenv("ASK_MODEL", "gpt-oss:latest")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def safe_output(text):
    """Output text safely, stripping problematic characters"""
    # Strip to ASCII for piped output compatibility
    clean = text.encode('ascii', errors='ignore').decode('ascii')
    sys.stdout.write(clean)
    sys.stdout.write('\n')
    sys.stdout.flush()

def ask(prompt, model=None, system=None, json_mode=False):
    """Send a prompt to Ollama and return the response"""
    model = model or DEFAULT_MODEL
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    if json_mode:
        data["format"] = "json"
    
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = json.loads(resp.read().decode('utf-8'))
            return body["message"]["content"]
    except urllib.error.URLError as e:
        sys.stderr.write(f"Error: {e}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        return None

def list_models():
    """List available models"""
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for m in sorted(data.get("models", []), key=lambda x: x['name']):
                name = m['name']
                size = m.get('size', 0) / (1024**3)
                safe_output(f"  {name:<35} {size:>5.1f}GB")
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")

def main():
    parser = argparse.ArgumentParser(description="Simple Ollama CLI for agents")
    parser.add_argument("prompt", nargs="*", help="Prompt to send")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"Model (default: {DEFAULT_MODEL})")
    parser.add_argument("-s", "--system", help="System prompt")
    parser.add_argument("--json", action="store_true", help="JSON output mode")
    parser.add_argument("--list-models", action="store_true", help="List models")
    parser.add_argument("-o", "--output", help="Write to file instead of stdout")
    
    args = parser.parse_args()
    
    if args.list_models:
        list_models()
        return
    
    # Get prompt from args or stdin
    prompt = " ".join(args.prompt)
    if not prompt and not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    
    if not prompt:
        sys.stderr.write("Error: No prompt provided\n")
        sys.exit(1)
    
    result = ask(prompt, args.model, args.system, args.json)
    
    if result is None:
        sys.exit(1)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        safe_output(f"Written to {args.output}")
    else:
        safe_output(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)
