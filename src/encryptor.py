import utils
import numpy as np
import key_utils
import random
import gc
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
from cfg import *


OPERATIONS = ["permutation", "xor", "modular"]
MOD_ORDER = ["add", "sub"]
PERMUTATION_ORDER = ["row", "column"]

def encrypt_file(input_path, output_path, raw_key, public_key=None, cores=None, signals=None):
    """Encrypts a file using memory-efficient multi-threading with actual progress tracking."""
    file_size, num_blocks, last_block_size = utils.file_info(input_path)
    if signals:
        signals.time1.emit()
        signals.update_terminal.emit(f"Using {cores} cpu cores.\n")
    primary_hash = key_utils.primary_hash(raw_key)
    seed1, seed2 = key_utils.extract_prng_seeds(primary_hash)
    subkey_generator = key_utils.key_expansion_stream(primary_hash, raw_key, num_blocks)
    subkey_lock = threading.Lock()
    def next_subkey():
        with subkey_lock:
            return next(subkey_generator)
    rsa_enc_key = key_utils.rsa_encrypt_key(raw_key, public_key) if public_key else None
    utils.write_file_header(output_path, last_block_size, rsa_enc_key)
    op_order = determine_operation_sequence(seed1)
    row_swaps, col_swaps, permutation_order, mod_order = determine_sub_operations(seed2)
    processed_blocks = 0  # Track progress
    progress_lock = threading.Lock()  # Prevent race conditions
    def process_block(i, block):
        """Encrypts a single block but does NOT update progress here."""
        block = utils.pad_block(block)
        block_matrix = utils.bytes_to_matrix(block)
        subkey_matrix = utils.bytes_to_matrix(next_subkey())
        for op in op_order:
            if op == "xor":
                block_matrix = apply_xor(block_matrix, subkey_matrix)
            elif op == "modular":
                for t, mod_op in enumerate(mod_order):
                    block_matrix = apply_modular_operations(block_matrix, subkey_matrix, mod_op, t == 1)
            elif op == "permutation":
                block_matrix = apply_permutation(block_matrix, row_swaps, col_swaps, permutation_order)
        result = utils.matrix_to_bytes(block_matrix)
        del block_matrix, subkey_matrix
        return result
    # Process blocks with real-time progress tracking
    with ThreadPoolExecutor(max_workers=cores) as executor:
        block_iterator = enumerate(utils.read_file_in_blocks(input_path))
        futures = set()
        future_to_block = {}
        # Preload first `cores` blocks
        for _ in range(cores):
            try:
                i, block = next(block_iterator)
                future = executor.submit(process_block, i, block)
                futures.add(future)
                future_to_block[future] = i
            except StopIteration:
                break
        next_index = 0
        results = {}
        while futures:
            done, futures = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                i = future_to_block[future]
                results[i] = future.result()
                del future_to_block[future]
                while next_index in results:
                    utils.write_to_file(output_path, results[next_index])
                    del results[next_index]
                    next_index += 1
                    # Update progress AFTER writing a block
                    if signals:
                        with progress_lock:
                            processed_blocks += 1
                            progress_percent = int((processed_blocks / num_blocks) * 100)
                            if processed_blocks == num_blocks:
                                signals.time2.emit()
                            signals.progress_update.emit(progress_percent)
                            signals.nblock_update.emit(processed_blocks,num_blocks)
                            signals.terminal_progress.emit(processed_blocks,num_blocks)
                # Submit a new block
                try:
                    i, block = next(block_iterator)
                    new_future = executor.submit(process_block, i, block)
                    futures.add(new_future)
                    future_to_block[new_future] = i
                except StopIteration:
                    pass
    gc.collect()  # Final cleanup

def decrypt_file(input_path, output_path, raw_key=None, private_key=None, cores=None, signals=None):
    """Decrypts a file encrypted with Enigmatrix's encryption algorithm using memory-efficient parallel processing."""
    # Overwrite output file if it exists
    with open(output_path, "wb") as f:
        pass
    # Step 1: Read the Header (RSA flag, encrypted key, last block size)
    rsa_flag, rsa_enc_key, last_block_size = utils.read_file_header(input_path)
    # Step 2: Decrypt the RSA Key (if used) and retrieve raw key
    if rsa_flag:
        try:
            raw_key = key_utils.rsa_decrypt_key(rsa_enc_key, private_key)
        except ValueError:
            raise ValueError("Incorrect RSA key provided")
    if signals:
        signals.time1.emit()
        signals.update_terminal.emit(f"Using {cores} cpu cores.\n")
    # Step 3: Generate Subkeys
    primary_hash = key_utils.primary_hash(raw_key)
    seed1, seed2 = key_utils.extract_prng_seeds(primary_hash)
    # Get file size and adjust for header
    file_size, *_ = utils.file_info(input_path)
    # Calculate the correct pointer position to skip the header
    header_size = 1 + 8  # RSA flag (1 byte) + Last block Size (8 bytes)
    if rsa_flag:
        header_size += 4 + len(rsa_enc_key)
    # Calculate number of blocks
    num_blocks = utils.calculate_num_blocks(file_size, header_size)
    subkey_generator = key_utils.key_expansion_stream(primary_hash, raw_key, num_blocks)
    subkey_lock = threading.Lock()
    def next_subkey():
        with subkey_lock:
            return next(subkey_generator)
    # Determine Operation Order
    op_order = determine_operation_sequence(seed1)
    row_swaps, col_swaps, permutation_order, mod_order = determine_sub_operations(seed2)
    processed_blocks = 0  # Track progress
    progress_lock = threading.Lock()  # Prevent race conditions
    def process_block(i, block):
        """Decrypts a single block by reversing encryption steps."""
        block_matrix = utils.bytes_to_matrix(block)
        subkey_matrix = utils.bytes_to_matrix(next_subkey())
        # Reverse Operations in the same order as encryption
        for op in reversed(op_order):
            if op == "permutation":
                block_matrix = reverse_permutation(block_matrix, row_swaps, col_swaps, permutation_order)
            elif op == "modular":
                for t, mod_op in enumerate(mod_order):
                    block_matrix = apply_modular_operations(block_matrix, subkey_matrix, mod_op, t == 0)
            elif op == "xor":
                block_matrix = apply_xor(block_matrix, subkey_matrix)
        block = utils.matrix_to_bytes(block_matrix)
        # Truncate Last block if Needed
        if i == num_blocks - 1:
            block = utils.truncate_block(block, last_block_size)
        # Explicitly delete NumPy arrays after processing
        del block_matrix, subkey_matrix
        return block
    # Process blocks in memory-efficient way
    with ThreadPoolExecutor(max_workers=cores) as executor:
        block_iterator = enumerate(utils.read_file_in_blocks(input_path, pointer=header_size))
        futures = set()
        future_to_block = {}
        # Only load as many blocks as we have cores
        for _ in range(cores):
            try:
                i, block = next(block_iterator)
                future = executor.submit(process_block, i, block)
                futures.add(future)
                future_to_block[future] = i
            except StopIteration:
                break
        next_index = 0
        results = {}
        while futures:
            # Wait for the next completed future
            done, futures = concurrent.futures.wait(
                futures,
                return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in done:
                i = future_to_block[future]
                results[i] = future.result()
                del future_to_block[future]
                # Write blocks in order
                while next_index in results:
                    utils.write_to_file(output_path, results[next_index])
                    del results[next_index]
                    next_index += 1
                    # Update progress AFTER writing a block
                    if signals:
                        with progress_lock:
                            processed_blocks += 1
                            progress_percent = int((processed_blocks / num_blocks) * 100)
                            if processed_blocks == num_blocks:
                                signals.time2.emit()
                            signals.progress_update.emit(progress_percent)
                            signals.nblock_update.emit(processed_blocks,num_blocks)
                            signals.terminal_progress.emit(processed_blocks,num_blocks)
                # Add a new block to process
                try:
                    i, block = next(block_iterator)
                    new_future = executor.submit(process_block, i, block)
                    futures.add(new_future)
                    future_to_block[new_future] = i
                except StopIteration:
                    pass  # No more blocks to process
    gc.collect()  # Final cleanup

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
