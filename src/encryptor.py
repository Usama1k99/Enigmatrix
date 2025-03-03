import utils
import numpy as np
import key_utils
import random
import gc
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from cfg import *


OPERATIONS = ["permutation", "xor", "modular"]
MOD_ORDER = ["add", "sub"]
PERMUTATION_ORDER = ["row", "column"]


def encrypt_file(input_path, output_path, raw_key, public_key=None):
    """Encrypts a file using multi-threading for faster processing."""
    # Key Expansion
    primary_hash = key_utils.primary_hash(raw_key)
    seed1, seed2 = key_utils.extract_prng_seeds(primary_hash)
    file_size, num_chunks, last_chunk_size = utils.file_info(input_path)
    subkey_generator = key_utils.key_expansion_stream(primary_hash, raw_key, num_chunks)
    subkey_lock = threading.Lock()
    def next_subkey():
        with subkey_lock:
            return next(subkey_generator)
    # Optional RSA Encryption
    rsa_enc_key = key_utils.rsa_encrypt_key(raw_key, public_key) if public_key else None
    utils.write_file_header(output_path, last_chunk_size, rsa_enc_key)
    # Generate Operation Sequences
    op_order = determine_operation_sequence(seed1)
    row_swaps, col_swaps, permutation_order, mod_order = determine_sub_operations(seed2)
    def process_chunk(i, chunk):
        """Encrypts a single chunk."""
        chunk = utils.pad_chunk(chunk)
        chunk_matrix = utils.bytes_to_matrix(chunk)
        subkey_matrix = utils.bytes_to_matrix(next_subkey())
        # Apply Encryption Operations
        for op in op_order:
            if op == "xor":
                chunk_matrix = apply_xor(chunk_matrix, subkey_matrix)
            elif op == "modular":
                for t, mod_op in enumerate(mod_order):
                    chunk_matrix = apply_modular_operations(chunk_matrix, subkey_matrix, mod_op, t == 1)
            elif op == "permutation":
                chunk_matrix = apply_permutation(chunk_matrix, row_swaps, col_swaps, permutation_order)
        result = utils.matrix_to_bytes(chunk_matrix)
        # **Explicitly delete NumPy arrays after processing**
        del chunk_matrix, subkey_matrix
        return result
    # Read, Encrypt, and Write in Parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_chunk = {executor.submit(process_chunk, i, chunk): i for i, chunk in enumerate(utils.read_file_in_chunks(input_path))}
        results = {}  # Dictionary to store chunks that finish early
        next_index = 0  # Tracks the next chunk to write
        for future in as_completed(future_to_chunk):
            i = future_to_chunk[future]  # Get chunk index
            results[i] = future.result()  # Store in dictionary
            # Write chunks in correct order as soon as possible
            while next_index in results:
                utils.write_to_file(output_path, results[next_index])  # Write the next chunk
                del results[next_index]  # Free memory immediately
                next_index += 1  # Move to the next expected chunk
    gc.collect()

def decrypt_file(input_path, output_path, raw_key=None, private_key=None):
    """Decrypts a file encrypted with Kryptigma's encryption algorithm using parallel processing."""
    # Overwrite output file if it exists
    with open(output_path, "wb") as f:
        pass
    # Step 1: Read the Header (RSA flag, encrypted key, last chunk size)
    rsa_flag, rsa_enc_key, last_chunk_size = utils.read_file_header(input_path)
    # Step 2: Decrypt the RSA Key (if used) and retrieve raw key
    if rsa_flag:
        try:
            raw_key = key_utils.rsa_decrypt_key(rsa_enc_key, private_key)
        except ValueError:
            raise ValueError("Incorrect RSA key provided")
    # Step 3: Generate Subkeys
    primary_hash = key_utils.primary_hash(raw_key)
    seed1, seed2 = key_utils.extract_prng_seeds(primary_hash)
    # Get file size and adjust for header
    file_size, *_ = utils.file_info(input_path)
    # Calculate the correct pointer position to skip the header
    header_size = 1 + 8  # RSA flag (1 byte) + Last Chunk Size (8 bytes)
    if rsa_flag:
        header_size += 4 + len(rsa_enc_key)
    # Calculate number of chunks
    num_chunks = utils.calculate_num_chunks(file_size, header_size)
    subkey_generator = key_utils.key_expansion_stream(primary_hash, raw_key, num_chunks)
    subkey_lock = threading.Lock()
    def next_subkey():
        with subkey_lock:
            return next(subkey_generator)
    # Read encrypted chunks (generator)
    encrypted_chunks = utils.read_file_in_chunks(input_path, pointer=header_size)
    # Determine Operation Order
    op_order = determine_operation_sequence(seed1)
    row_swaps, col_swaps, permutation_order, mod_order = determine_sub_operations(seed2)
    def process_chunk(i, chunk):
        """Decrypts a single chunk by reversing encryption steps."""
        chunk_matrix = utils.bytes_to_matrix(chunk)
        subkey_matrix = utils.bytes_to_matrix(next_subkey())
        # Reverse Operations in the same order as encryption
        for op in reversed(op_order):
            if op == "permutation":
                chunk_matrix = reverse_permutation(chunk_matrix, row_swaps, col_swaps, permutation_order)
            elif op == "modular":
                for t, mod_op in enumerate(mod_order):
                    chunk_matrix = apply_modular_operations(chunk_matrix, subkey_matrix, mod_op, t == 0)
            elif op == "xor":
                chunk_matrix = apply_xor(chunk_matrix, subkey_matrix)
        chunk = utils.matrix_to_bytes(chunk_matrix)
        # Truncate Last Chunk if Needed
        if i == num_chunks - 1:
            chunk = utils.truncate_chunk(chunk, last_chunk_size)
        # **Explicitly delete NumPy arrays after processing**
        del chunk_matrix, subkey_matrix
        return chunk
    # Parallel Processing: Decrypt Chunks
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_chunk = {executor.submit(process_chunk, i, chunk): i for i, chunk in enumerate(encrypted_chunks)}
        results = {}  # Store decrypted chunks that finish early
        next_index = 0  # Tracks the next chunk to write
        for future in as_completed(future_to_chunk):
            i = future_to_chunk[future]  # Get chunk index
            results[i] = future.result()  # Store decrypted chunk in dictionary
            # Write chunks in correct order as soon as possible
            while next_index in results:
                utils.write_to_file(output_path, results[next_index])  # Write decrypted chunk
                del results[next_index]  # Free memory immediately
                next_index += 1  # Move to the next expected chunk
    gc.collect()

def apply_xor(matrix, subkey):
    """Applies XOR operation between matrix and subkey using NumPy."""
    return matrix ^ subkey

def apply_permutation(matrix, row_swaps, col_swaps, order):
    """Performs both row and column swaps on the matrix."""
    temp_matrix = matrix.copy()
    if order[0] == "row":
        for i, j in row_swaps:
            temp_matrix[[i, j], :] = temp_matrix[[j, i], :]
        for i, j in col_swaps:
            temp_matrix[:, [i, j]] = temp_matrix[:, [j, i]]
    else:
        for i, j in col_swaps:
            temp_matrix[:, [i, j]] = temp_matrix[:, [j, i]]
        for i, j in row_swaps:
            temp_matrix[[i, j], :] = temp_matrix[[j, i], :]
    return temp_matrix

def reverse_permutation(matrix, row_swaps, col_swaps, order):
    """Reverses both row and column swaps to restore the original matrix."""
    temp_matrix = matrix.copy()
    if order[0] == "row":
        for i, j in reversed(col_swaps):
            temp_matrix[:, [i, j]] = temp_matrix[:, [j, i]]
        for i, j in reversed(row_swaps):
            temp_matrix[[i, j], :] = temp_matrix[[j, i], :]
    else:
        for i, j in reversed(row_swaps):
            temp_matrix[[i, j], :] = temp_matrix[[j, i], :]
        for i, j in reversed(col_swaps):
            temp_matrix[:, [i, j]] = temp_matrix[:, [j, i]]
    return temp_matrix

def apply_modular_operations(matrix, subkey, mod_op, transpose=False):
    """Applies modular addition or subtraction to the entire matrix using NumPy."""
    temp_matrix = matrix.copy()
    temp_subkey = subkey.copy()
    if transpose:
        temp_subkey = temp_subkey.T
    if mod_op == "add":
        return ((temp_matrix.astype(np.uint16) + temp_subkey.astype(np.uint16)) % 256).astype(np.uint8)
    else:  # "sub"
        return ((temp_matrix.astype(np.uint16) - temp_subkey.astype(np.uint16)) % 256).astype(np.uint8)


def determine_operation_sequence(seed1):
    """Uses PRNG seed1 to decide the order of major encryption operations."""
    random.seed(seed1)
    operations = OPERATIONS.copy()
    random.shuffle(operations)
    return operations

def determine_sub_operations(seed2):
    """Uses PRNG seed2 to decide specific row/column swaps & modular operations."""
    random.seed(seed2)
    row_swaps = [(random.randint(0,MATRIX_SIZE-1), random.randint(0, MATRIX_SIZE-1)) for _ in range(SWAP_COUNT)]
    col_swaps = [(random.randint(0,MATRIX_SIZE-1), random.randint(0, MATRIX_SIZE-1)) for _ in range(SWAP_COUNT)]
    mod_order = MOD_ORDER.copy()
    permutation_order = PERMUTATION_ORDER.copy()
    random.shuffle(mod_order)
    random.shuffle(permutation_order)
    return row_swaps, col_swaps, permutation_order, mod_order

if __name__ == '__main__':
    import time
    t1 = time.time()
    encrypt_file("../Demo/Original/Need For Speed  Heat.mp4","../Demo/Encrypted/nfsh.enc","testing the thing".encode())
    t2 = time.time()
    print(f"enc: {t2 - t1:.6f} seconds")
    t2 = time.time()
    decrypt_file("../Demo/Encrypted/nfsh.enc","../Demo/Decrypted/nfsh.dec",raw_key="testing the thing".encode())
    t3 = time.time()
    print(f"dec: {t3-t2:.6f} seconds")
