# Enigmatrix - The Ultimate Encryption Tool  

## Overview  
Enigmatrix is a high-performance encryption tool designed to provide secure and efficient file encryption. It features a custom encryption algorithm based on **1024×1024 key matrices, PRNG-driven transformations, and modular arithmetic operations**. The tool supports both **GUI and terminal-based** usage, ensuring flexibility for different user preferences.  

## Features  
- **Custom Encryption Algorithm** – Uses advanced key expansion, XOR operations, and modular arithmetic for strong encryption.  
- **Multi-Threaded Processing** – Leverages parallel execution to optimize encryption and decryption speed.  
- **Built-in Terminal** – A CLI-like interface within the application for executing commands.  
- **RSA Key Support** – Allows encryption keys to be secured using RSA public-key cryptography.  
- **Benchmarking & Performance Estimation** – Measures system performance and estimates encryption time before execution.  
- **Progress Tracking** – Live progress bars for encryption, decryption, and benchmarking.  
- **Flexible UI Modes** – Switch between GUI and terminal-based interaction as needed.  

## Installation  

### Requirements  
- Python 3.1x
- PyQt6  
- NumPy  
- Cryptography libraries (`pycryptodome` for RSA)
- psutil

### Setup  
1. Clone the repository:  
   `git clone https://github.com/Usama1k99/Enigmatrix.git` 
2. Navigate into the directory:  
   `cd Enigmatrix`  
3. Install dependencies:  
   `pip install -r requirements.txt`  
4. Run the application:  
   `python main.py`  

## How It Works  

### Encryption Process  
1. **Key Expansion** – The user-provided key undergoes multi-stage deterministic expansion, generating **1024×1024 subkey matrices** using SHA-256, BLAKE2b, and PRNG-derived transformations.  
2. **Block-Based Processing** – Files are processed in blocks, allowing parallel encryption for high efficiency.  
3. **Cryptographic Transformations** – Each block undergoes **XOR operations, PRNG-driven swaps, and modular arithmetic transformations** to ensure strong encryption.  
4. **Parallel Execution** – Encryption tasks are **distributed across multiple CPU cores** using threading.  
5. **RSA Integration (Optional)** – If an RSA public key is provided, the encryption key is further encrypted for additional security.  

### Decryption Process  
The decryption process follows the **exact reverse of encryption**, using the same **PRNG sequences** and **transformation order** to restore the original file.  

## Configuration  
Enigmatrix automatically adjusts settings to optimize performance. Configuration values are stored in `config.json`:  
- **Benchmark Time** – The encryption speed is measured and stored during the first launch.  
- **Default Core Usage** – The tool dynamically selects the optimal number of CPU cores.  
- **UI Mode Selection** – Users can switch between terminal and GUI-based interactions.  

## Contributing  
Contributions are welcome! Feel free to open issues or submit pull requests to improve the project.  

## License  
This project is licensed under the [MIT License](LICENSE).  

---

This README provides a **clean overview** while keeping details concise. Let me know if you need any changes!