import httpx
import sys
import os
import time
import re
import subprocess
import psutil
import threading
from colorama import init, Fore, Style

from gitai.config import MODEL_PATH, PORT

init(autoreset=True)


_daemon_process = None
_inference_done = False

try:
    _physical_cores = psutil.cpu_count(logical=False) or psutil.cpu_count() or 4
    _logical_cores  = psutil.cpu_count(logical=True) or 4
except ImportError:
    _logical_cores  = os.cpu_count() or 4
    _physical_cores = max(1, _logical_cores // 2)

_n_threads_optimized = max(1, _physical_cores)
_n_threads_batch_optimized = max(1, _logical_cores)

def clean_git_diff(raw_diff, max_estimated=2500, debug=True):
    """
    Preprocesses, cleans, and filters the git diff to optimize processing speed on CPU.
    Includes a debug mode to visualize the filtered string and check character economy.
    """
    initial_char_count = len(raw_diff)
    lines = raw_diff.splitlines()
    clean_lines = []
    
    # List of binary or lockfile patterns that shouldn't waste CPU cycles
    ignored_extensions = ('.png', '.jpg', '.jpeg', '.ico', '.pdf', '.lock')
    
    for line in lines:
        # 1. Skip native git metadata that provides zero semantic value to the LLM
        if line.startswith("index ") or line.startswith("similarity index") or line.startswith("rename from") or line.startswith("rename to"):
            continue
            
        # 2. Skip binary file notifications or tracking modifications
        if "Binary files differ" in line or any(ext in line for ext in ignored_extensions):
            continue

        # 3. Skip pure code comments (Python, JS, C++, etc.)
        if re.match(r'^[+-]\s*(#|//|\*|/\*)', line):
            continue
            
        # 4. Skip lines that contain only structural syntax/punctuation (brackets, commas, semicolons)
        if re.match(r'^[+-]\s*[{{}}();,.\s]*\s*$', line):
            continue
            
        # 5. Skip pure white-space adjustments or empty lines inside the diff
        if not line.strip() or line in ("+", "-"):
            continue

        clean_lines.append(line)
        
    filtered_diff = "\n".join(clean_lines)
    
    # EMERGENCY STRUCTURAL TRUNCATION (If it's still a monster after filtering)
    if len(filtered_diff) > max_estimated:
        critical_lines = [l for l in clean_lines if l.startswith("---") or l.startswith("+++") or l.startswith("@@")]
        if critical_lines:
            filtered_diff = "\n".join(critical_lines[:70]) + "\n... [Diff truncated structural view due to large size] ..."

    if debug:
        final_char_count = len(filtered_diff)
        saved_chars = initial_char_count - final_char_count
        
        if final_char_count <= 49:
            pass
        else:
            print(Fore.CYAN + "═"*55)
            print(Fore.CYAN + "      [GITAI OPTIMIZER] TRAFFIC ANALYSIS")
            print(Fore.CYAN + "═"*55)
            print(f" • Raw Diff Volume:   {initial_char_count} chars")
            print(f" • Clean Data Sent:   {final_char_count} chars")
            print(" • Efficiency Bonus:   " + Fore.GREEN + f"{saved_chars} chars saved")
            print(Fore.CYAN + "═"*55, "\n")

    global _inference_done
    _inference_done = False

    def progress_bar():
        global _inference_done
        
        bar_length = 30
        total_steps = 350

        for step in range(total_steps + 1):
            if _inference_done:
                break

            percent = (step / total_steps) * 100
            if percent > 95: 
                percent = 95

            filled_length = int(bar_length * percent // 100)
            bar = Fore.YELLOW + '█' * filled_length + Style.DIM + '-' * (bar_length - filled_length)

            sys.stdout.write(Fore.YELLOW + f'\r Crunching diff: [{bar}' + Style.RESET_ALL + Fore.YELLOW + f'] {percent:.0f}%')
            sys.stdout.flush()
            time.sleep(0.2)

        bar_final = '█' * bar_length
        sys.stdout.write(Fore.YELLOW + f'\r Crunching diff: [{bar_final}' + Fore.YELLOW + '] 100%\n\n')
        sys.stdout.flush()

    loading_thread = threading.Thread(target=progress_bar)
    loading_thread.start()

    return filtered_diff

def start_daemon(lang="en"):
    """Starts the llama_cpp server as a silent background process using your optimized parameters."""
    global _daemon_process
    try:
        res = httpx.get(f"http://localhost:{PORT}/v1/models")
        if res.status_code == 200:
            print(Fore.CYAN + " GitAI server daemon is already running in the background.")
            return
    except httpx.RequestError:
        pass

    print(Fore.CYAN + " Loading model into RAM... (Starting work session)")
    
    cmd = [
        sys.executable, "-m", "llama_cpp.server",
        "--model", str(MODEL_PATH),
        "--port", str(PORT),
        "--host", "localhost",
        "--n_ctx", "2048",
        "--n_batch", "512",
        "--n_ubatch", "512",
        "--n_threads", str(_n_threads_optimized),
        "--n_threads_batch", str(_n_threads_batch_optimized),
        "--use_mmap", "True",
        "--cache", "True"
    ]
    
    # WINDOWS CRITICAL FLAG: CREATE_NO_WINDOW (0x08000000)
    # This tells Windows: "Run this in the background 100% invisible, 
    # without opening extra CMD windows, but keeping the pipx virtual environment intact".
    creation_flags = 0x08000000
    
    # Use close_fds=True to completely unbind file descriptors from the current terminal
    _daemon_process=subprocess.Popen(
        cmd, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL, 
        creationflags=creation_flags,
        close_fds=True
    )
    
    server_ready = False
    for _ in range(60):
        try:
            time.sleep(1)
            if httpx.get(f"http://localhost:{PORT}/v1/models").status_code == 200:
                server_ready = True
                break
        except httpx.RequestError:
            continue
            
    if not server_ready:
        print(Fore.RED + " Error: Server daemon took too long to load into RAM.")
        return

    # The prompt is forced to load at startup (Warm-up)
    print(Fore.CYAN + " Priming prompt cache and optimizing engine layers...\n")
    try:
        # Minimum Plain Text Diff Dummy
        dummy_diff = "--- a/init.txt\n+++ b/init.txt\n@@ -0,0 +1 @@\n+init"
        
        # The original function is executed in the background. 
        # This will take a few seconds to load in here, absorbing all the initial wait.
        generate_commit_message(diff=dummy_diff, initial_commit=False, lang=lang)
        
        print(Fore.GREEN + " Work session initialized. GitAI is hot and ready in the background!")
    except Exception:
        # If for some reason the warm-up fails, do not abort the server boot
        print(Fore.GREEN + " Work session initialized. GitAI is running (cache priming skipped).")

def stop_daemon():
    """Finds the background server process and terminates it to free memory."""
    global _daemon_process
    
    if _daemon_process:
        try:
            _daemon_process.terminate()
            _daemon_process.wait(timeout=3)
            _daemon_process = None
            return
        except Exception:
            pass
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['cmdline'] and "llama_cpp.server" in " ".join(proc.info['cmdline']):
                proc.terminate()
                print(Fore.GREEN + " Session closed successfully. RAM cleared.")
                return
        print(Fore.CYAN + " No active GitAI session was found running.")
    except ImportError:
        print(Fore.CYAN + " The 'psutil' library is required to terminate the session. Please install it with: pip install psutil")

def generate_commit_message(diff, initial_commit=False, lang="en"):
    """Generates the commit message by communicating via HTTP with the background daemon."""
    
    # Adaptive cleanup and pruning
    diff = clean_git_diff(diff, max_estimated=2500, debug=True)
    
    if lang == "es":
        user_instruction = "Genera un mensaje de commit corto basándote en el siguiente git diff:"
    else:
        user_instruction = "Generate a short commit message based on the following git diff:"

    if initial_commit:
        has_readme = "README.md" in diff or "README.md content" in diff
        if lang == "es":
            if has_readme:
                user_instruction = (
                    "Este es el COMMIT INICIAL del repositorio. "
                    "Analiza el contenido del README.md y los archivos creados para entender el proyecto. "
                    "Genera un mensaje corto que describa la creación del proyecto. NO uses la frase 'initial commit'.\n"
                    "Ejemplo: feat: estructura inicial del [nombre del proyecto]"
                )
            else:
                user_instruction = (
                    "Este es el COMMIT INICIAL del repositorio. "
                    "Basándote únicamente en la lista de archivos creados, genera un mensaje corto "
                    "que describa qué tipo de proyecto se está iniciando. NO uses la frase 'initial commit'.\n"
                    "Ejemplo: chore: estructura base del [nombre del proyecto]"
                )
        else:
            if has_readme:
                user_instruction = (
                    "This is the INITIAL COMMIT of the repository. "
                    "Analyze the README.md content and the created files to understand the project's purpose. "
                    "Generate a short message describing the project creation. Do NOT use 'initial commit'.\n"
                    "Example: feat: initial structure for [project name]"
                )
            else:
                user_instruction = (
                    "This is the INITIAL COMMIT of the repository. "
                    "Based solely on the list of created files, generate a short one-line message "
                    "describing what kind of project is being initiated. Do NOT use 'initial commit'.\n"
                    "Example: chore: base repository [project name] structure"
                )

    if lang == "es":
        prompt = (
            f"<|im_start|>system\n"
            f"Eres un bot experto en Git que escribe EXCLUSIVAMENTE en idioma ESPAÑOL.\n"
            f"Tu tarea es generar un mensaje de commit usando el estándar de Conventional Commits basándote en el diff provisto.\n\n"
            f"<|im_end|>\n"
            f"<|im_start|>user\n"
            f"ORDEN CRÍTICA (REGLAS DE ORO):\n"
            f"Guía de TIPO de commit (Aplica el primero que corresponda de arriba a abajo):\n"
            f"- 'feat': Si añade código nuevo o nuevas funciones. (Ej: feat(auth): agregar login con google)\n"
            f"- 'fix': Si corrige un error lógico, bug, crash o mal funcionamiento. (Ej: fix(api): corregir timeout en peticion)\n"
            f"- 'refactor': Si limpia, optimiza, renombra o mueve código sin cambiar su comportamiento. (Ej: refactor(llm): optimizar bucle de carga)\n"
            f"- 'style': Si modifica diseño visual, interfaz (UI), colores, fuentes, iconos o tamaños. (Ej: style(ui): cambiar color de boton)\n"
            f"- 'docs': Si el cambio ocurre en README.md, archivos .txt, comentarios o docstrings. (Ej: docs(readme): actualizar guia de instalacion)\n"
            f"- 'chore': Si ocurre SOLO en configuración, dependencias o entornos. (Ej: chore: actualizar paquetes en toml)\n"
            f"- 'test': Añadir, corregir o modificar pruebas unitarias o de integración. (Ej: test(db): agregar prueba de conexion)\n"
            f"- 'perf': Cambios de código destinados específicamente a mejorar la velocidad. (Ej: perf(core): reducir uso de memoria ram)\n"
            f"- 'ci': Modificaciones en scripts de integración o despliegue continuo. (Ej: ci(actions): corregir ruta en workflow de github)\n"
            f"- 'build': Cambios que afectan el empaquetado o herramientas de construcción externa. (Ej: build: empaquetar binario para distribucion)\n"
            f"- Si el diff muestra principalmente líneas eliminadas (-), interpreta si es una limpieza de código muerto (refactor) o una quita de configuración (chore).\n\n"
            f"REGLAS DE FORMATO:\n"
            f"- Formato: tipo: descripción O tipo(scope): descripción (Usa un scope corto entre paréntesis solo si el diff identifica un módulo claro).\n"
            f"- El scope va SIEMPRE entre paréntesis y es UNA SOLA palabra corta. NUNCA uses comas ni extensiones de archivos dentro del scope.\n"
            f"- Todo en minúsculas, sin punto final.\n"
            f"- Devuelve SOLO la línea del commit. No agregues texto introductorio, explicaciones, markdown, bloques de código ni comillas.\n"
            f"- Escribe la respuesta 100% en ESPAÑOL (aunque el código o las variables del diff estén en inglés).\n"
            f"- Máximo 3 a 7 palabras en la descripción. Prohibido pasarte de 7 palabras. Sé directo, descriptivo y mantén el total bajo 72 caracteres.\n\n"
            f"INSTRUCCIÓN ESPECÍFICA PARA ESTE CAMBIO:\n"
            f"{user_instruction}\n\n"
            f"[GIT DIFF TO ANALYZE]:\n{diff}\n"
            f"<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
    else:
        prompt = (
            f"<|im_start|>system\n"
            f"You are an expert Git bot that writes EXCLUSIVELY in ENGLISH.\n"
            f"Your task is to generate a commit message using the Conventional Commits standard based on the provided diff.\n\n"
            f"<|im_end|>\n"
            f"<|im_start|>user\n"
            f"CRITICAL REMINDER (GOLDEN RULES):\n"
            f"Strict guide to determine the commit TYPE (Apply the first one that matches from top to bottom):\n"
            f"- 'feat': If introduces new executable code or features. (e.g., feat(auth): add google login option)\n"
            f"- 'fix': If fixes logical errors, bugs, crashes, or broken behavior. (e.g., fix(api): fix timeout on endpoint request)\n"
            f"- 'refactor': If cleans, optimizes, renames, or moves code without changing behavior. (e.g., refactor(llm): optimize loading loop structure)\n"
            f"- 'style': If modifies visual presentation, UI, colors, fonts, spacing, icons, or sizing. (e.g., style(ui): change primary button color)\n"
            f"- 'docs': If occurs in README.md, .txt files, comments, or docstrings. (e.g., docs(readme): update setup instructions)\n"
            f"- 'chore': If occurs ONLY in configuration files, dependencies, or setups. (e.g., chore: update packages in toml file)\n"
            f"- 'test': Adding, fixing, or modifying unit/integration tests. (e.g., test(db): add database connection unit test)\n"
            f"- 'perf': Code changes specifically aimed at improving speed. (e.g., perf(core): reduce ram memory usage)\n"
            f"- 'ci': Modifications to continuous integration or delivery scripts. (e.g., ci(actions): fix pathway in github workflow file)\n"
            f"- 'build': Changes affecting the packaging system or external build tools. (e.g., build: package binary executable for distribution)\n"
            f"- If the diff shows mainly deleted lines (-), interpret whether it is a cleanup of dead code (refactor) or a removal of configuration (chore).\n\n"
            f"FORMATTING RULES:\n"
            f"- Format: type: description OR type(scope): description (Use a short scope in parentheses only if the diff clearly identifies a specific module).\n"
            f"- The scope goes ALWAYS in parentheses and is ONE single short word. NEVER use commas or file extensions inside the scope.\n"
            f"- All lowercase, no period at the end.\n"
            f"- Output ONLY the commit message line. No introductions, no explanations, no markdown, no code blocks, no quotes.\n\n"
            f"- Output the final message 100% in ENGLISH (even if the code or variables in the diff are in Spanish).\n"
            f"- Maximum 3 to 7 words in the description. Do NOT exceed 7 words. Be direct, descriptive, and keep the total under 72 characters.\n\n"
            f"SPECIFIC INSTRUCTION FOR THIS CHANGE:\n"
            f"{user_instruction}\n\n"
            f"[GIT DIFF TO ANALYZE]:\n{diff}\n"
            f"<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    payload = {
        "prompt": prompt,
        "temperature": 0.0,
        "max_tokens": 100,
        "stop": ["<|im_end|>", "\n"],
        "cache_prompt": True
    }

    try:
        start_time = time.perf_counter()
        response = httpx.post(f"http://localhost:{PORT}/v1/completions", json=payload, timeout=120.0)
        response.raise_for_status()

        global _inference_done
        _inference_done = True
        time.sleep(0.25)

        elapsed_time = time.perf_counter() - start_time

        commit_message = response.json()["choices"][0]["text"].strip()

        # Cleaning external quotes around the final message
        if commit_message.startswith('"') and commit_message.endswith('"'):
            commit_message = commit_message[1:-1].strip()
        if commit_message.startswith("'") and commit_message.endswith("'"):
            commit_message = commit_message[1:-1].strip()

        print("           Inference completed on " + Fore.GREEN + f"{elapsed_time:.2f}s")

        return commit_message

    except httpx.RequestError as exc:
        # DIAGNOSIS: The actual technical error that HTTPX is experiencing is printed
        print(Fore.RED + f"\n [DEBUG CLIENT] Technical connection error: {exc}")
        raise RuntimeError(Fore.RED + " GitAI daemon is not running. Please start your session by running: gitai start") from exc
    except Exception as e:
        print(Fore.RED + f"\n [DEBUG CLIENT] Another error: {e}")
        raise e