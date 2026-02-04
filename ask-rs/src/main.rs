use clap::Parser;
use serde::{Deserialize, Serialize};
use std::env;
use std::fs;
use std::io::{self, Read};

#[derive(Parser, Debug)]
#[command(name = "ask")]
#[command(about = "Fast CLI for Ollama - query local LLMs", long_about = None)]
struct Args {
    /// The prompt to send to the model
    #[arg(trailing_var_arg = true)]
    prompt: Vec<String>,

    /// Model to use
    #[arg(short, long, default_value = "gpt-oss:latest")]
    model: String,

    /// System prompt
    #[arg(short, long)]
    system: Option<String>,

    /// Output JSON format
    #[arg(long)]
    json: bool,

    /// Write output to file
    #[arg(short, long)]
    output: Option<String>,

    /// List available models
    #[arg(long)]
    list_models: bool,

    /// Show version
    #[arg(short = 'V', long)]
    version: bool,
}

#[derive(Serialize)]
struct ChatRequest {
    model: String,
    messages: Vec<Message>,
    stream: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    format: Option<String>,
}

#[derive(Serialize, Deserialize, Clone)]
struct Message {
    role: String,
    content: String,
}

#[derive(Deserialize)]
struct ChatResponse {
    message: Message,
}

#[derive(Deserialize)]
struct ModelsResponse {
    models: Vec<ModelInfo>,
}

#[derive(Deserialize)]
struct ModelInfo {
    name: String,
    size: Option<u64>,
}

fn get_ollama_host() -> String {
    env::var("OLLAMA_HOST").unwrap_or_else(|_| "http://localhost:11434".to_string())
}

fn get_default_model() -> String {
    env::var("ASK_MODEL").unwrap_or_else(|_| "gpt-oss:latest".to_string())
}

fn list_models(host: &str) -> Result<(), Box<dyn std::error::Error>> {
    let url = format!("{}/api/tags", host);
    let resp: ModelsResponse = ureq::get(&url).call()?.into_json()?;
    
    println!("Available models:\n");
    let mut models = resp.models;
    models.sort_by(|a, b| a.name.cmp(&b.name));
    
    for m in models {
        let size_gb = m.size.unwrap_or(0) as f64 / (1024.0 * 1024.0 * 1024.0);
        println!("  {:<35} {:>5.1}GB", m.name, size_gb);
    }
    Ok(())
}

fn ask(
    host: &str,
    model: &str,
    prompt: &str,
    system: Option<&str>,
    json_mode: bool,
) -> Result<String, Box<dyn std::error::Error>> {
    let url = format!("{}/api/chat", host);
    
    let mut messages = Vec::new();
    if let Some(sys) = system {
        messages.push(Message {
            role: "system".to_string(),
            content: sys.to_string(),
        });
    }
    messages.push(Message {
        role: "user".to_string(),
        content: prompt.to_string(),
    });

    let request = ChatRequest {
        model: model.to_string(),
        messages,
        stream: false,
        format: if json_mode { Some("json".to_string()) } else { None },
    };

    let resp: ChatResponse = ureq::post(&url)
        .set("Content-Type", "application/json")
        .send_json(&request)?
        .into_json()?;

    Ok(resp.message.content)
}

fn is_stdin_piped() -> bool {
    #[cfg(unix)]
    {
        use std::os::unix::io::AsRawFd;
        unsafe { libc::isatty(io::stdin().as_raw_fd()) == 0 }
    }
    #[cfg(windows)]
    {
        use std::os::windows::io::AsRawHandle;
        use windows_sys::Win32::System::Console::GetConsoleMode;
        let handle = io::stdin().as_raw_handle();
        let mut mode = 0;
        unsafe { GetConsoleMode(handle as _, &mut mode) == 0 }
    }
    #[cfg(not(any(unix, windows)))]
    {
        false
    }
}

fn read_stdin() -> Option<String> {
    if !is_stdin_piped() {
        return None;
    }
    let mut buffer = String::new();
    io::stdin().read_to_string(&mut buffer).ok()?;
    let trimmed = buffer.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.to_string())
    }
}

fn main() {
    let args = Args::parse();
    
    if args.version {
        println!("ask v1.0.0 (Rust)");
        println!("Host: {}", get_ollama_host());
        println!("Default model: {}", get_default_model());
        return;
    }

    let host = get_ollama_host();
    let model = if args.model == "gpt-oss:latest" {
        get_default_model()
    } else {
        args.model
    };

    if args.list_models {
        if let Err(e) = list_models(&host) {
            eprintln!("Error listing models: {}", e);
            std::process::exit(1);
        }
        return;
    }

    // Build prompt from args and stdin
    let mut prompt = args.prompt.join(" ");
    if let Some(stdin_content) = read_stdin() {
        if prompt.is_empty() {
            prompt = stdin_content;
        } else {
            prompt = format!("{}\n\nContext:\n{}", prompt, stdin_content);
        }
    }

    if prompt.is_empty() {
        eprintln!("Error: No prompt provided");
        eprintln!("Usage: ask [OPTIONS] <PROMPT>...");
        std::process::exit(1);
    }

    match ask(&host, &model, &prompt, args.system.as_deref(), args.json) {
        Ok(response) => {
            if let Some(output_file) = args.output {
                if let Err(e) = fs::write(&output_file, &response) {
                    eprintln!("Error writing to {}: {}", output_file, e);
                    std::process::exit(1);
                }
                println!("Written to {}", output_file);
            } else {
                println!("{}", response);
            }
        }
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
    }
}
