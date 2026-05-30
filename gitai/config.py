import os
import threading
import time
import sys
import subprocess
from pathlib import Path


MODEL_DIR      = Path(os.environ.get("LOCALAPPDATA", ".")) / "gitai" / "models"
MODEL_FILENAME = "Qwen2.5.1-Coder-7B-Instruct-Q4_K_M.gguf"
MODEL_PATH     = MODEL_DIR / MODEL_FILENAME
MODEL_URL      = "https://huggingface.co/bartowski/Qwen2.5.1-Coder-7B-Instruct-GGUF/resolve/main/Qwen2.5.1-Coder-7B-Instruct-Q4_K_M.gguf?download=true"
PORT           = 8089

def get_secure_env():
    env = os.environ.copy()
    env["LC_ALL"] = "C.UTF-8"
    env["LANG"] = "C.UTF-8"
    return env

def model_exists():
    return MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 100_000_000

def download_model(on_progress, on_done, on_error):
    import httpx
    def run():
        try:
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            tmp_path = MODEL_PATH.with_suffix(".tmp")

            with httpx.stream("GET", MODEL_URL, follow_redirects=True, timeout=None) as r:
                r.raise_for_status()
                total      = int(r.headers.get("content-length", 0))
                downloaded = 0

                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=1024 * 256):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct  = downloaded / total
                            d_gb = downloaded / 1_073_741_824
                            t_gb = total      / 1_073_741_824
                            on_progress(pct, d_gb, t_gb)

            tmp_path.rename(MODEL_PATH)
            on_done()

        except Exception as e:
            on_error(str(e))

    threading.Thread(target=run, daemon=True).start()

def ensure_model():
    if model_exists():
        return

    print("┌─────────────────────────────────────────────┐")
    print("│  gitai - First run: downloading AI model    │")
    print("│  AI Model Setup - one time only             │")
    print("└─────────────────────────────────────────────┘\n")

    done_flag = {"done": False, "error": None}

    def on_progress(pct, d_gb, t_gb):
        bar_len = 30
        filled  = int(bar_len * pct)
        bar     = "█" * filled + "░" * (bar_len - filled)
        print(f"\r  [{bar}] {pct*100:.1f}%  {d_gb:.2f}/{t_gb:.2f} GB", end="", flush=True)

    def on_done():
        done_flag["done"] = True

    def on_error(e):
        done_flag["error"] = e

    download_model(on_progress, on_done, on_error)

    while not done_flag["done"] and not done_flag["error"]:
        time.sleep(0.5)

    if done_flag["error"]:
        print(f"\n\n✗ Error downloading model: {done_flag['error']}")
        sys.exit(1)

    print("\n\n✓ Model downloaded successfully.\n")

def get_repo_language(force_ask=False):
    """
    Checks if the language configuration exists for this repository.
    If it doesn't exist or force_ask is True, it asks the user and saves it.
    """
    if not force_ask:
        result = subprocess.run(
            ["git", "config", "--get", "gitai.lang"],
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            env=get_secure_env()
        )
        stored_lang = result.stdout.strip().lower()
        if stored_lang in ["es", "en"]:
            return stored_lang

    print("\n  [gitai] Language configuration for this repository:")
    while True:
        choice = input("  [s] Spanish  [e] English  → ").strip().lower()
        if choice == "s":
            lang = "es"
            break
        elif choice == "e":
            lang = "en"
            break
        else:
            print("✗ Invalid option. Please select 's' or 'e'.")

    subprocess.run(
        ["git", "config", "gitai.lang", lang],
        encoding="utf-8",
        check=False,
        env=get_secure_env()
    )
    print(f"✓ Language saved as '{lang}' in the Git configuration of this project.\n")
    return lang