# Changelog

---

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/).

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