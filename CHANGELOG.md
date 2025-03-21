# Changelog

---

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.5] - 2025-03-22
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