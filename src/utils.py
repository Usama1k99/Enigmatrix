import numpy as np
import struct
from cfg import *
import os
import json
import io

CONFIG_FILE = "./config.json"

def load_config():
    """Load configuration from JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}  # Return empty dict if config file doesn't exist

def dump_config(obj):
    """Dump configuration to JSON file"""
    with open(CONFIG_FILE,"w") as f:
        json.dump(obj,f,indent=4)

def estimate_encryption_time(file_size, bm_time, overhead_factor=0.127):
    """Estimates encryption time with overhead adjustment."""
    file_size_mb = file_size / (1024 * 1024)
    estimated_time = (file_size_mb / 100) * bm_time * (1 + overhead_factor)
    return round(estimated_time, 3)

def normalize_kwargs(kwargs):
    """Converts all keys in the kwargs dictionary to lowercase."""
    return {key.lower(): value for key, value in kwargs.items()}

def save_rsa_directory(path):
    """Save the RSA key directory path to config.json."""
    config = load_config()
    config["rsa_directory"] = path  # Update path
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)  # Save in JSON format

def get_rsa_directory():
    config = load_config()
    return config.get("rsa_directory")

def get_rsa_files():
    """Retrieve all `.pem` key files from the stored RSA directory."""
    config = load_config()
    rsa_dir = config.get("rsa_directory")
    if not rsa_dir or not os.path.exists(rsa_dir):
        return []
    return [f for f in os.listdir(rsa_dir) if f.endswith(".pem")]

def get_default_core_count():
    """Determines the optimal number of threads for benchmarking."""
    total_cores = os.cpu_count() or 2
    default_cores = max(2, total_cores // 2)
    return default_cores

def load_command_history():
    """Loads command history from config.json."""
    config = load_config()
    return config.get("command_history", [])

def save_command(command):
    """Saves the command to config.json."""
    config = load_config()
    command_history = load_command_history()
    # Prevent appending duplicate consecutive commands
    if command_history and command_history[-1] == command:
        return
    command_history.append(command)
    if len(command_history) > CMD_HISTORY_LIMIT:
        command_history.pop(0)
    config["command_history"] = command_history
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def readable_size(size_in_bytes):
    """
    Converts a file size in bytes to a human-readable format (KB, MB, GB, etc.).
    """
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size_in_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"

def check_encrypted(file_path):
    """Checks if a file is encrypted by Enigmatrix based on the first byte."""
    try:
        with open(file_path, "rb") as file:
            first_byte = file.read(1)  # Read the first byte
            return first_byte in {b"\x00", b"\x01"}  # Enigmatrix header
    except: # Empty file, corrupted unreadable file
        return False

def estimate_encrypted_size(size_in_bytes):
    """
    Estimates the size of the encrypted file by rounding up to the next whole MB.

    :param size_in_bytes: Original file size in bytes
    :return: Estimated encrypted file size in bytes (rounded to the next MB)
    """
    MB = 1024 * 1024  # 1 MB in bytes
    remainder = size_in_bytes % MB  # Get remainder when divided by 1MB

    if remainder == 0:
        return size_in_bytes  # Already a whole MB
    else:
        return size_in_bytes + (MB - remainder)  # Round up to the next MB

def write_file_header(file_path,lcs,rsa_enc_key):
    """Writes the encryption header to the file, including LCS and optional RSA-encrypted key."""
    key_size = 0
    rsa_flag = False
    if rsa_enc_key:
        rsa_flag = True
        key_size = len(rsa_enc_key)
    with open(file_path,'w+b') as f:
        f.seek(0)
        f.write(struct.pack("B", rsa_flag))
        # If RSA is used, write key size (4 bytes) and encrypted key
        if rsa_flag:
            f.write(struct.pack("I", key_size))
            f.write(rsa_enc_key)
        # Write Last Chunk Size (8 bytes)
        f.write(struct.pack("Q", lcs))

def read_file_header(file_path):
    """Reads and parses the encryption header from the file."""
    with open(file_path, 'rb') as f:
        f.seek(0)
        rsa_flag = struct.unpack("B", f.read(1))[0]
        rsa_enc_key = None
        if rsa_flag:
            key_size = struct.unpack("I", f.read(4))[0]
            rsa_enc_key = f.read(key_size)
        lcs = struct.unpack("Q", f.read(8))[0]
    return rsa_flag, rsa_enc_key, lcs

def file_info(file_path):
    """Returns the file size, number of chunks, and last chunk size."""
    file_size = os.path.getsize(file_path)
    num_chunks = (file_size // CHUNK_SIZE) + (file_size % CHUNK_SIZE > 0)
    last_chunk_size = file_size % CHUNK_SIZE
    return file_size, num_chunks, last_chunk_size

def calculate_num_chunks(original_size, header_size):
    """Calculates the number of chunks after adjusting for header size."""
    adjusted_size = original_size - header_size
    return (adjusted_size // CHUNK_SIZE) + (adjusted_size % CHUNK_SIZE > 0)

def bytes_to_matrix(chunk):
    """Converts a 1MB byte chunk into a 1024×1024 matrix."""
    if len(chunk) != 1024 * 1024:
        raise ValueError("Chunk size must be exactly 1MB (1024*1024 bytes)")
    return np.frombuffer(chunk, dtype=np.uint8).reshape(1024, 1024)

def matrix_to_bytes(matrix):
    """Converts a 1024×1024 matrix back into a 1MB byte chunk."""
    if matrix.shape != (1024, 1024):
        raise ValueError("Matrix must be exactly 1024×1024 in shape")
    return matrix.astype(np.uint8).tobytes()

def truncate_chunk(chunk, original_size):
    """Trims a chunk back to its original size using LCS from the header."""
    return chunk[:original_size]

def pad_chunk(chunk):
    """Pads a chunk to ensure it is exactly 1MB by adding null bytes (0x00)."""
    padding_length = CHUNK_SIZE - len(chunk)
    return chunk + b'\x00' * padding_length

def read_file_in_chunks(file_path, pointer=0):
    """Reads a file in chunks and returns a generator with buffered reading."""
    with open(file_path, "rb") as file:
        file.seek(pointer)
        buffered_reader = io.BufferedReader(file)
        while chunk := buffered_reader.read(CHUNK_SIZE):
            yield chunk

def write_to_file(output_path, chunk):
    """Writes processed chunk to a file."""
    with open(output_path, "ab") as file:
        file.write(chunk)

def generate_tree(directory, prefix="", depth=3, current_level=0):
    """Recursively generates a tree structure for the given directory up to a depth limit."""
    if current_level >= depth:
        return [f"{prefix}└── (More items hidden...)"]
    try:
        entries = sorted(os.listdir(directory), key=str.lower)  # Case-insensitive sorting
    except PermissionError:
        return [f"{prefix}└── [Permission Denied]"]
    tree_lines = []
    entry_count = len(entries)
    for index, entry in enumerate(entries):
        full_path = os.path.join(directory, entry)
        is_last = (index == entry_count - 1)  # Check if this is the last item
        connector = "└── " if is_last else "├── "
        safe_entry = str(entry).strip()
        if os.path.isdir(full_path):
            tree_lines.append(f"{prefix}{connector}📂 {safe_entry}/")
            sub_prefix = "    " if is_last else "│   "
            tree_lines.extend(generate_tree(full_path, prefix + sub_prefix, depth, current_level + 1))
        else:
            tree_lines.append(f"{prefix}{connector}📄 {safe_entry}")
    return tree_lines

def del_file(fpath):
    try:
        os.remove(fpath)
    except FileNotFoundError:
        pass