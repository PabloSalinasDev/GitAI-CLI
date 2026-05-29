import subprocess
import sys
from gitai.config import model_exists, ensure_model, get_repo_language, get_secure_env
from gitai.llm_client import start_daemon, stop_daemon, generate_commit_message


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
                content = f.read(3000)
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
        print("Error: this directory is not a git repository.")
        print("Run 'git init' first.")
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
        print("\n✓ Commit done successfully.")
        print(result.stdout.strip())
    else:
        print("\n✗ Commit failed.")
        print(result.stderr.strip())

def main():
    args = sys.argv[1:]
    
    # 1. GLOBAL SETTINGS: gitai init (Physical download only)
    if args and args[0] == "init":
        ensure_model()
        print("✓ GitAI global setup finished. Run 'gitai start' inside your repository to start working.")
        return

    # 2. START LOGICAL DAY: gitai start (Check local language and raise the model)
    if args and args[0] == "start":
        if not model_exists():
            print("✗ Model file not found. Run 'gitai init' first to download it.")
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
        print("✗ GitAI is not initialized. Please run: gitai init")
        return

    # Silently read local Git configuration without asking questions in terminal
    lang = get_repo_language(force_ask=False)

    initial = is_initial_commit()
    if initial:
        context = get_initial_context()
    else:
        context = get_staged_diff()

    if not context:
        print("✗ Nothing staged. Run 'git add' before using gitai.")
        sys.exit(0)

    print("Analyzing changes...\n")
    
    try:
        message = generate_commit_message(context, initial_commit=initial, lang=lang)
    except Exception as e:
        print(f"\n{e}")
        sys.exit(1)

    print("┌─────────────────────────────────────────────┐")
    print("│  Suggested commit message:                  │")
    print("└─────────────────────────────────────────────┘")
    print(f"\n  {message}\n")

    while True:
        choice = input("  [c] Confirm  [e] Edit  [x] Cancel  → ").strip().lower()

        if choice == "c":
            run_commit(message)
            break
        elif choice == "e":
            edited = input("  Enter your message: ").strip()
            if edited:
                run_commit(edited)
            else:
                print("  Empty message. Cancelled.")
            break
        elif choice == "x":
            print("  Cancelled.")
            break
        else:
            print("  Invalid option. Use c, e or x.")

if __name__ == "__main__":
    main()