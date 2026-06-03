# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-06-03

### Added
- Implemented a native integrated help menu command (`gitai help`, `--help`, `-h`) featuring clear terminal usage documentation.
- Integrated direct interactive hyperlinks to the official GitHub documentation and issue tracker within the help console footprint.
- Added a robust command-line validation filter to block invalid positional arguments and guide users toward the help menu.

### Fixed
- Fixed an asynchronous race condition in `llm_client.py` where the prompt would collide with the progress bar completion string, causing a stray character artifact on initial runs.

---

## [1.0.4] - 2026-06-03

### Added
- Implemented a "Fail-Fast" mechanism in the HTTP client connection layer to verify daemon availability before processing any data payloads.
- Added graceful program termination (`sys.exit(0)`) when the CLI tool is invoked without an active background server session running.

### Changed
- Shifted the user-facing `"Analyzing changes..."` terminal print to execute before the LLM inference initialization to improve perceived performance and visual feedback.
- Optimized the main orchestration workflow to capture and reuse the inference output string in a single variable instead of triggering redundant, duplicate HTTP requests to the local server.

### Fixed
- Fixed a major control flow bug in `main.py` that caused a double invocation of `generate_commit_message()`, cutting execution latencies in half and removing duplicated console output.
- Fixed an interface rendering bug where the interactive commit confirmation prompt (`[c] Confirm [e] Edit [x] Cancel`) and an empty markdown block would render on screen even if the connection to the daemon failed.

---

## [1.0.3] - 2026-06-03

### Changed
- Refactored the core background daemon warm-up routine by reducing the processing overhead of the initial mock payload.
- Replaced the structural mock git-diff text with an ultra-short baseline string to optimize execution speed on consumer-grade CPUs.

### Fixed
- Fixed an interface bug in `clean_git_diff` where the detailed `[GITAI OPTIMIZER] TRAFFIC ANALYSIS` console box would accidentally trigger and display inaccurate character economy metrics during the hidden initialization phase.

---

## [1.0.2] - 2026-06-03

### Added
- Added custom branding footer print (`Developed by PyBloSoft © 2026 - Ver. 1.0.2`) upon successful completion of the global system installation command (`gitai init`).

### Fixed
- Fixed an asynchronous rendering bug where the initial loading progress bar (`Crunching diff`) would lock or visually freeze on screen while the heavy model layers were being read into local RAM for the first time.

---

## [1.0.1] - 2026-06-03

### Changed
- Updated documentation across package distribution modules to explicitly define installation procedures via `pipx` for isolated global execution environments.

### Fixed
- Fixed a critical packaging error where `setuptools` omitted secondary source files (such as `llm_client.py`), causing runtime `ImportError` exceptions after a global installation.
- Fixed absolute media asset routes in `README.md` using explicit raw user content parameters to ensure proper image and benchmark graphic rendering on the official PyPI project profile hub.

---

## [1.0.0] - 2026-06-03

### Added
- Initial official release of GitAI CLI.
- Automated git-diff pre-processing, filtering, and structural code token optimization.
- Local inference pipeline integration via offline background HTTP daemon.
- Interactive terminal prompt interface natively supporting Conventional Commits styling structures.