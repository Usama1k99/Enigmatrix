# Changelog

---

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/).


---
## [2.6.1] - 2025-08-02

### Fixed

* **GUI Crash on Encryption/Decryption Operations**

  * Fixed a fatal bug where encryption and decryption via GUI buttons would crash due to mismatched `ParallelWorker` function signatures. The new worker threading model now correctly routes `signals` to wrapped functions using lambdas.
* **RSA Key Generation Stability**

  * Updated RSA key generation thread logic to align with the updated `ParallelWorker` interface, ensuring consistent behavior across GUI-triggered operations.

---
## [2.6.0] - 2025-05-01

### Added
- **Overflow and Size Limit Detection in Evaluator**
  - The terminal now gracefully handles math expressions that exceed integer size limits, displaying clear error messages for both `OverflowError` and system string conversion limits.
- **New `test` Command for Developers**
  - A built-in command that dumps received arguments and keyword arguments in formatted JSON—handy for debugging and inspecting command input.
- **Internal `_pvt_empty_cmd` Command**
  - Adds a silent, no-output command that can be triggered for UI refreshes or scripted flows requiring a terminal prompt reset.
- **Simulated Keypress and Scroll Enforcement**
  - The terminal now forces scroll-to-bottom more reliably using a simulated backspace keypress and cursor movement.

### Improvements
- **Better Handling of `--` Argument Parsing**
  - Throws an error when invalid flags like `--` (without a key) are passed, improving user feedback and command input validation.
- **Quote Handling in User Input**
  - Detects unclosed quotes (e.g. `echo "Hello`) and returns a helpful error instead of failing silently—prevents malformed commands from breaking execution flow.
- **Stricter Eval Protection**
  - Reworked the `safe_eval` flow to filter out unsafe or malformed expressions more reliably, reducing edge-case crashes.

### Changed
- **Unified Terminal Update Signal**
  - Refactored terminal signals: `update_terminal` now sends plain text, while `update_terminal_full` supports `(text, add_prompt)` format—improves flexibility across different command contexts.
- **RSA Directory Detection Logic**
  - Now uses a centralized function (`get_rsa_directory`) to check validity and existence of the RSA folder, removing redundant config access patterns.
- **Parallel Worker Confirmation Handling**
  - Workers invoked from the terminal emit a `confirmed(True)` signal after finishing, even if a prompt was not directly expected—improves consistency in UI workflows.

### Fixed
- **Terminal No Longer Leaves Cursor Mid-Text**
  - Cursor forcefully returns to the start after updates, preventing awkward scroll lock or misplaced focus.
- **Crash Fix for Empty or Corrupt RSA Config**
  - Resolved issue where an unset or invalid `rsa_directory` key could cause a silent crash on app startup.
- **Safer Command Parsing**
  - Command parser now explicitly checks for malformed `--` flags and unterminated quotes, preventing misinterpretation or incorrect keyword arguments.

---
## [2.5.0] - 2025-03-22
### Added
- **Massive Memory Optimization for Encryption/Decryption** 
  - Now uses a memory-efficient streaming approach, keeping RAM usage minimal regardless of file size.
- **Improved Thread Management** 
  - Threads dynamically load and process blocks without unnecessary memory buildup.
- **Configuration Display in Terminal (`info --config`)**  
  - Users can now view the stored configuration settings in a readable JSON format.

### Improvements
- Displayed (Admin) in the title bar when Enigmatrix is launched with administrative privileges.
- **Added Block Processing Count** 
  - Users can now see the number of processed blocks alongside the progress bar for better real-time feedback.
- **Enhanced Help Fallback Handling**  
  - Provides clearer guidance when a command is used incorrectly. 
  
### Changed
- **Actual Progress Tracking for Encryption & Decryption** 
  - The progress bar now updates based on real-time block processing instead of estimated time.
- **Refactored `set-preference` Command**  
  - Now supports setting core count (`--cores <num>`), with validation against system limits.  
- **Help Text Updates**  
  - Updated help descriptions to reflect new features and improvements. 
  
### Fixed
- **Improved Help Command Formatting** 
  - Enhanced text layout for better readability.  
- **Enhanced Help Fallback Handling**
  - Provides clearer guidance when a command is used incorrectly.  
- **Better Parameter Handling in `encrypt` and `decrypt` Commands** – Prevents crashes when users provide `--parameter` without a value.
  - **Crash Fix for Missing or Invalid Paths in Terminal Commands** – Ensures `os.path` does not receive `None` or `bool` values.

---
## [2.0] - 2025-03-16
### Added
- **ParallelWorker for GUI & Terminal Commands** – All heavy operations now run in background threads.
- **Progress Bar for GUI & Terminal** – Real-time progress tracking for encryption, decryption, and benchmarks.
- **Auto Benchmark on First Launch** – Runs `benchmark` automatically to estimate encryption time.
- **Estimated Time Calculation** – Encryption/decryption commands now display estimated time before execution.
- **Aliases Command** – Displays all aliases for a given command.

### Changed
- **GUI Responsiveness Improved** – GUI no longer freezes during encryption, decryption, or benchmarking.
- **Tree Command Enhancement** – Added custom depth limit for better control.
- **Echo Command Improvement** – Now safely evaluates expressions if provided.
- **Help Command Improved** – Better formatting and clarity in command descriptions.

### Fixed
- **Admin Mode in Bundled `.exe`** – Now properly launches with admin privileges.
- **Minor Bug Fixes** – Various small fixes for stability.

---
## [1.10] - 2025-03-11
### Added
- Implemented **benchmark command** (`benchmark`), allowing users to test encryption speed.
- **Terminal interaction improvements**:
  - Users can now move the cursor within their input.
  - Users cannot delete past terminal output.
- Added **info command** (`info`):
  - Displays Enigmatrix version and CPU cores used.
- Added help commands for `echo` command and `#` comment

### Changed
- Improved `help` command output formatting for better readability.
- Optimized terminal rendering performance.

### Fixed
- **"cd" command now properly handles paths**:
  - Previously changed the system working directory (`os.chdir`), causing path issues.
  - Now correctly **stores** the current directory without affecting OS paths.

---

## **[1.00] - 2025-03-04** *(Initial Release)*  

### **Added**  
- **Encryption & Decryption** functionality for secure file protection.  
- **Terminal Command System** to perform operations via command-line interface.  
- **RSA Key Management**:  
  - Generate RSA key pairs.  
  - Select and set an RSA directory.  
  - Use RSA encryption for key security.  
- **Graphical User Interface (GUI)** with:  
  - File selection and encryption/decryption controls.  
  - Retro-style terminal for command execution.  
  - RSA key selection panel with dynamically listed keys.  
- **Configurable Preferences**:  
  - Set UI mode (`terminal` or `gui`).  
  - Change window size (`fullscreen`, `maximize`, `normal`, `small`).  
- **Tree Command** to display directory structure in the terminal.  
- **Command History Navigation** using `Up` and `Down` arrow keys.  
- **Help System** for listing available commands and their usage.  

---