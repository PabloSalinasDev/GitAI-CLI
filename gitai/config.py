import os
import sys
import subprocess
from pathlib import Path
from colorama import init, Fore, Style

init(autoreset=True)


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

def ensure_model():
    """Ensures the model is downloaded synchronously, hiding the cursor and cleaning up on Ctrl+C."""
    if model_exists():
        return

    import httpx

    print(Fore.CYAN + "┌─────────────────────────────────────────────┐")
    print(Fore.CYAN + "│   GitAI - First run: downloading AI model   │")
    print(Fore.CYAN + "│      AI Model Setup - one time only         │")
    print(Fore.CYAN + "│                                             │")
    print(Fore.CYAN + "│ Developed by PyBloSoft © 2026 - Ver. 1.3.0  │")
    print(Fore.CYAN + "└─────────────────────────────────────────────┘\n")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = MODEL_PATH.with_suffix(".tmp")

    if tmp_path.exists():
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    def print_progress(pct, d_gb, t_gb):
        bar_len = 30
        filled  = int(bar_len * pct)
        bar     = Fore.YELLOW + "█" * filled + Style.DIM + "░" * (bar_len - filled)
        print(Fore.YELLOW + f"\r[{bar}" + Style.RESET_ALL + Fore.YELLOW + f"] {pct*100:.1f}%  {d_gb:.2f}/{t_gb:.2f} GB", end="", flush=True)

    f = None
    try:
        with open(tmp_path, "wb") as f:
            with httpx.stream("GET", MODEL_URL, follow_redirects=True, timeout=None) as r:
                r.raise_for_status()
                total      = int(r.headers.get("content-length", 0))
                downloaded = 0

                for chunk in r.iter_bytes(chunk_size=1024 * 256):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct  = downloaded / total
                        d_gb = downloaded / 1_073_741_824
                        t_gb = total      / 1_073_741_824
                        print_progress(pct, d_gb, t_gb)

        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        
        tmp_path.rename(MODEL_PATH)
        print(Fore.GREEN + "\n\n Model downloaded successfully.\n")

    except KeyboardInterrupt:

        if f and not f.closed:
            try:
                f.close()
            except Exception:
                pass
        
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        
        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        print(Fore.YELLOW + "\n [INFO] Download aborted by user. Temporary file purged successfully.")
        os._exit(1)

    except Exception as e:

        if f and not f.closed:
            try:
                f.close()
            except Exception:
                pass
                
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        print(Fore.RED + f"\n\n Error downloading model: {e}")
        sys.exit(1)

def get_repo_language(force_ask=False):
    """
    Checks if the language configuration exists for this repository.
    If it doesn't exist or force_ask is True, it asks the user safely and saves it.
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

    print(Fore.CYAN + "\n  [gitai] Language configuration for this repository:")

    try:
        while True:
            choice = input(Fore.CYAN + "   [s] Spanish   [e] English  → ").strip().lower()
            if choice == "s":
                lang = "es"
                break
            elif choice == "e":
                lang = "en"
                break
            else:
                print(Fore.RED + "   Invalid option. Please select 's' or 'e'.")
    except KeyboardInterrupt:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        print(Fore.YELLOW + "\n [INFO] Language selection cancelled. Exiting.")
        sys.exit(0)

    subprocess.run(
        ["git", "config", "gitai.lang", lang],
        encoding="utf-8",
        check=False,
        env=get_secure_env()
    )
    print(Fore.GREEN + f" Language saved as '{lang}' in the Git configuration of this project.\n")
    return lang