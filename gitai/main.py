import subprocess
import sys
from colorama import init, Fore, Style

from gitai.config import model_exists, ensure_model, get_repo_language, get_secure_env
from gitai.llm_client import start_daemon, stop_daemon, generate_commit_message

init(autoreset=True)

def is_git_repo():
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        env=get_secure_env()
    )
    return result.returncode == 0

def is_initial_commit():
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        env=get_secure_env()
    )
    return result.returncode != 0

def get_initial_context():
    context = ""
    for name in ["README.md", "readme.md", "README.txt"]:
        try:
            with open(name, "r", encoding="utf-8", errors="replace") as f:
                head_lines = [f.readline() for _ in range(10)]
                content = "".join(head_lines).strip()
                
                if content:
                    context += f"README.md content:\n{content}\n\n"
                break
        except FileNotFoundError:
            pass

    result = subprocess.run(
        ["git", "diff", "--staged", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        env=get_secure_env()
    )
    if result.stdout.strip():
        context += f"Files included in this commit:\n{result.stdout.strip()}"
        
    return context

def get_staged_diff():
    result = subprocess.run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        env=get_secure_env()
    )
    if result.returncode != 0:
        print(Fore.RED + " Error: this directory is not a git repository.")
        print(Fore.CYAN + " Run 'git init' first.")
        sys.exit(1)
    return result.stdout.strip()

def run_commit(message):
    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        env=get_secure_env()
    )
    if result.returncode == 0:
        print(Fore.GREEN + "\n Commit done successfully.")
        print(result.stdout.strip())
    else:
        print(Fore.RED + "\n Commit failed.")
        print(result.stderr.strip())

def print_help():
    """Print the user manual integrated directly into the terminal with web access."""
    print("\n")
    print(Fore.CYAN + "═"*86)
    print(Fore.CYAN + "                 GitAI CLI - Offline Privacy-First Commit Generator")
    print(Fore.CYAN + "                     Developed by PyBloSoft © 2026 - Ver. 1.3.1")
    print(Fore.CYAN + "═"*86)
    print("Usage:")
    print(f"  gitai         {Style.DIM}Analyze staged changes and generate a conventional commit.{Style.RESET_ALL}")
    print(f"  gitai init    {Style.DIM}Download and configure the local LLM engine weights.{Style.RESET_ALL}")
    print(f"  gitai start   {Style.DIM}Launch the background daemon and prime the prompt cache.{Style.RESET_ALL}")
    print(f"  gitai out     {Style.DIM}Stop the background daemon session and free system RAM.{Style.RESET_ALL}")
    print(f"  gitai help    {Style.DIM}Show this user manual screen.{Style.RESET_ALL}")
    print(Fore.CYAN + "─"*86)
    print("Privacy & Security Guarantees:")
    print(f"  • {Fore.GREEN}100% Local Inference:{Style.RESET_ALL} Runs entirely on your CPU/RAM using local GGUF weights.")
    print(f"  • {Fore.GREEN}Zero Telemetry:{Style.RESET_ALL} No internet connection required, no tracking, no data collection.")
    print(f"  • {Fore.GREEN}Air-Gapped Ready:{Style.RESET_ALL} Your source code and diffs never leave this machine.")
    print(Fore.CYAN + "─"*86)
    print("Links & Support:")
    print(f"  • Documentation:  {Fore.BLUE}https://github.com/PabloSalinasDev/GitAI-CLI#readme{Style.RESET_ALL}")
    print(f"  • Report an Issue: {Fore.BLUE}https://github.com/PabloSalinasDev/GitAI-CLI/issues{Style.RESET_ALL}")
    print(Fore.CYAN + "═"*86 + "\n")

def main():
    args = sys.argv[1:]
    
    # 1. GLOBAL SETTINGS: gitai init (Physical download only)
    if args and args[0] == "init":
        ensure_model()
        print(Fore.CYAN + " GitAI global setup finished. Run 'gitai start' inside your repository to start working.")
        return

    # 2. START LOGICAL DAY: gitai start (Check local language and raise the model)
    if args and args[0] == "start":
        if not is_git_repo():
            print(Fore.RED + " Error: this directory is not a git repository.")
            print(Fore.CYAN + " Run 'git init' first.")
            return
        if not model_exists():
            print(Fore.CYAN + " Model file not found. Run 'gitai init' first to download it.")
            return
        # Smart check: if the language is not set in this repo, it asks for it.
        # On subsequent executions of the command it passes by silently.
        lang = get_repo_language(force_ask=False)
        start_daemon(lang=lang)
        return

    # 3. CLOSE WORK SESSION: gitai out
    if args and args[0] == "out":
        stop_daemon()
        return

    # 4. DEFAULT GLOBAL FLOW: gitai (Instant Daily Use)
    if not model_exists():
        print(Fore.CYAN + " GitAI is not initialized. Please run: gitai init")
        return

    if args and args[0] in ["help", "-h", "--help"]:
        print_help()
        return

    if args:
        print(Fore.RED + f"\n Error: Unknown command '{args[0]}'.")
        print(Fore.CYAN + " Run 'gitai help' to see the list of available commands.\n")
        sys.exit(1)

    # Silently read local Git configuration without asking questions in terminal
    lang = get_repo_language(force_ask=False)

    initial = is_initial_commit()
    if initial:
        context = get_initial_context()
    else:
        context = get_staged_diff()

    if not context:
        print(Fore.CYAN + " Nothing staged. Run 'git add' before using gitai.")
        sys.exit(0)

    try:
        message = generate_commit_message(
            context, 
            initial_commit=initial, 
            lang=lang, 
            warmup=False
        )
    except RuntimeError as run_err:
        print(Fore.RED + f"\n{run_err}")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        print(Fore.YELLOW + "\n [INFO] Operation cancelled by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        print(Fore.RED + f"\n [ERROR]: {e}")
        sys.exit(1)

    if message is None:
        sys.exit(0)

    print(Fore.CYAN + "┌─────────────────────────────────────────────┐")
    print(Fore.CYAN + "│         Suggested commit message:           │")
    print(Fore.CYAN + "└─────────────────────────────────────────────┘")
    print(Fore.GREEN + f"\n {message}\n")

    try:
        while True:
            choice = input(Fore.CYAN + " [c] Confirm  [e] Edit  [x] Cancel  → ").strip().lower()

            if choice == "c":
                run_commit(message)
                break
            elif choice == "e":
                edited = input(Fore.CYAN + " Enter your message: ").strip()
                if edited:
                    run_commit(edited)
                else:
                    print(" Empty message. Cancelled.")
                break
            elif choice == "x":
                print(" Cancelled.")
                break
            else:
                print(Fore.RED + "\n Invalid option. Use c, e or x.\n")
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n Operation cancelled by user. Exiting.")
        sys.exit(0)

if __name__ == "__main__":
    main()