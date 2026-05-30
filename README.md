# GitAI

An offline, privacy-first CLI tool that automatically generates structured Git commit messages using a local LLM via `llama.cpp`. No API keys required, no data leaves your machine.

<p align="center">
  <a href="https://pypi.org/project/gitai-cli/">
    <img src="https://img.shields.io/badge/Install-PyPI-blue?style=for-the-badge&logo=pypi" alt="Install from PyPI">
  </a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://github.com/PabloSalinasDev/GitAI-CLI/issues">
    <img src="https://img.shields.io/badge/Report-Error-red?style=for-the-badge&logo=github" alt="Report Error">
  </a>
</p>

---

## Why GitAI? (Educational Purpose)

Starting out in software development requires absorbing dozens of industry best practices simultaneously. Adopting the **Conventional Commits** standard right from the beginning often causes friction and leads to wasted time staring at a blank terminal screen wondering how to phrase a change.

GitAI was built to act as an **invisible mentor inside your console**, specifically designed for developers looking to professionalize their daily workflow without losing focus on writing code.

The benefit of implementing this CLI is twofold:

* **Immediate Impact (Professionalism):** It resolves technical nomenclature in just a few seconds, ensuring a pristine, clean, and standardized Git history. This is ideal for making your portfolio stand out to recruiters reviewing your GitHub repositories.
* **Passive Learning (Long-term):** It works through imitation and consistency. By interactively auditing how the AI categorizes your syntax changes with precise tags (`feat`, `fix`, `refactor`), a developer's brain naturally absorbs the pattern over time, learning how to structure correct commits organically.

---

## Features

- **100% Local Ingestion**: Uses `llama-cpp-python` to run model inference completely offline via a background HTTP server on `localhost:8089`.
- **Conventional Commits**: Enforces the standard `type: description` format (e.g., `feat: add user authentication`).
- **Diff-Aware Context**: Inspects staged changes and file names to provide accurate context.
- **Initial Commit Detection**: Automatically detects the first commit of a repository and uses the README and file list as context instead of a diff.
- **Smart Language Memory**: Learns your language preference (English or Spanish) per repository using Git's native configuration system (`gitai.lang`), avoiding repetitive prompts.
- **Windows & UTF-8 Native**: Fully hardened against character encoding issues (`ñ`, acentos, `¿`) when generating or editing messages in Windows consoles.

## How it works

1. On first use, run `gitai init` to download the AI model (~4.7 GB).
2. At the start of each work session, run `gitai start` inside your repo. This loads the model into RAM as a background daemon and asks for your language preference if not already set.
3. After staging changes, run `gitai`. It feeds the diff (or initial commit context) into the model and proposes a commit message.
4. At the end of your session, run `gitai out` to stop the daemon and free RAM.

```bash
  ┌─────────────────────────────────────────────┐
  │  Suggested commit message:                  │
  └─────────────────────────────────────────────┘

  feat: implement google OAuth login flow

  [c] Confirm  [e] Edit  [x] Cancel  →
```

---

## Project structure

```
gitai/
├── gitai/
│   ├── __init__.py
│   ├── config.py        ← model path, download logic, language config
│   ├── main.py          ← CLI logic, user interaction
│   └── llm_client.py   ← daemon management and inference via HTTP
├── pyproject.toml       ← package definition and dependencies
└── README.md
```

## Installation (for Python developers)

First, install pipx if you don't have it:

```bash
pip install pipx
python -m pipx ensurepath
```

> After running `ensurepath`, restart your terminal.

Then install gitai globally:

```bash
python -m pipx install --pip-args="--prefer-binary" .\
```

## Setup (one time)

Download the AI model (~4.7 GB). This only needs to be done once:

```bash
gitai init
```

> The model (`Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf`) is stored in `%LOCALAPPDATA%\gitai\models`.

---

## Usage

### Start a work session

Run this once per session inside your repository. Loads the model into RAM and sets the language for the repo if not already configured:

```bash
gitai start
```

### Generate a commit message

```bash
git add .
gitai
```

### End a work session

Stops the background daemon and frees RAM:

```bash
gitai out
```

---

## Command reference

| Command | Description |
|---------|-------------|
| `gitai init` | Downloads the AI model (first time only) |
| `gitai start` | Loads the model into RAM, sets repo language |
| `gitai` | Generates and commits staged changes |
| `gitai out` | Stops the background daemon, frees RAM |

---

## Commit types used

| Type | When to use |
|------|-------------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation changes |
| style | Formatting, no logic change |
| refactor | Code refactor |
| test | Adding or fixing tests |
| chore | Build, dependencies, config |
| perf | Performance improvement |
| ci | CI/CD changes |
| build | Build system changes |

---

## Requirements

- Python 3.9+
- Git installed
- ~4.7 GB disk space for the model

## Performance

Commit message generation runs entirely on CPU. Generation time depends on your hardware:

| Hardware | Estimated time |
|----------|----------------|
| Modern desktop CPU (8+ cores) | ~5–9 seconds |
| Laptop / older CPU | ~9–16 seconds |
| CPU with few cores or low clock | 16+ seconds |

GPU acceleration is not supported in the default installation to keep setup simple (no CUDA or ROCm required).

## Dependencies

| Package | Purpose |
|---------|---------|
| llama-cpp-python | Run the local AI model as an HTTP server |
| httpx | Download the model and communicate with the daemon |
| psutil | Stop the background daemon (`gitai out`) |

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

*Developed by [Pablo Salinas](https://github.com/PabloSalinasDev)* - PyBloSoft © 2026