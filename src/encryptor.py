import utils
import numpy as np
import key_utils
import random
import gc
import threading
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from cfg import *


OPERATIONS = ["permutation", "xor", "modular"]
MOD_ORDER = ["add", "sub"]
PERMUTATION_ORDER = ["row", "column"]


def encrypt_file(input_path, output_path, raw_key, public_key=None, cores=None, signals=None):
    """Encrypts a file using memory-efficient multi-threading with deterministic subkeys."""
    file_size, num_blocks, last_block_size = utils.file_info(input_path)

    if signals:
        signals.time1.emit()
        signals.update_terminal.emit(f"Using {cores} cpu cores.\n")

    primary_hash = key_utils.primary_hash(raw_key)
    seed1, seed2 = key_utils.extract_prng_seeds(primary_hash)

    rsa_enc_key = key_utils.rsa_encrypt_key(raw_key, public_key) if public_key else None
    utils.write_file_header(output_path, last_block_size, rsa_enc_key)

    op_order = determine_operation_sequence(seed1)
    row_swaps, col_swaps, permutation_order, mod_order = determine_sub_operations(seed2)

    processed_blocks = 0
    progress_lock = threading.Lock()

    def process_block(i, block):
        block = utils.pad_block(block)
        block_matrix = utils.bytes_to_matrix(block)

        # 🔑 Deterministic, index-based subkey derivation
        subkey = key_utils.derive_subkey(primary_hash, raw_key, i)
        subkey_matrix = utils.bytes_to_matrix(subkey)

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

    with ThreadPoolExecutor(max_workers=cores) as executor:
        block_iterator = enumerate(utils.read_file_in_blocks(input_path))
        futures = set()
        future_to_block = {}

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
            done, futures = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED
            )

            for future in done:
                i = future_to_block[future]
                results[i] = future.result()
                del future_to_block[future]

                while next_index in results:
                    utils.write_to_file(output_path, results[next_index])
                    del results[next_index]
                    next_index += 1

                    if signals:
                        with progress_lock:
                            processed_blocks += 1
                            progress_percent = int((processed_blocks / num_blocks) * 100)
                            if processed_blocks == num_blocks:
                                signals.time2.emit()
                            signals.progress_update.emit(progress_percent)
                            signals.nblock_update.emit(processed_blocks, num_blocks)
                            signals.terminal_progress.emit(processed_blocks, num_blocks)

                try:
                    i, block = next(block_iterator)
                    new_future = executor.submit(process_block, i, block)
                    futures.add(new_future)
                    future_to_block[new_future] = i
                except StopIteration:
                    pass

    gc.collect()


def decrypt_file(input_path, output_path, raw_key=None, private_key=None, cores=None, signals=None):
    """Decrypts a file encrypted with Enigmatrix using deterministic subkeys."""

    with open(output_path, "wb"):
        pass

    rsa_flag, rsa_enc_key, last_block_size = utils.read_file_header(input_path)

    if rsa_flag:
        try:
            raw_key = key_utils.rsa_decrypt_key(rsa_enc_key, private_key)
        except ValueError:
            raise ValueError("Incorrect RSA key provided")

    if signals:
        signals.time1.emit()
        signals.update_terminal.emit(f"Using {cores} cpu cores.\n")

    primary_hash = key_utils.primary_hash(raw_key)
    seed1, seed2 = key_utils.extract_prng_seeds(primary_hash)

    file_size, *_ = utils.file_info(input_path)

    header_size = 1 + 8
    if rsa_flag:
        header_size += 4 + len(rsa_enc_key)

    num_blocks = utils.calculate_num_blocks(file_size, header_size)

    op_order = determine_operation_sequence(seed1)
    row_swaps, col_swaps, permutation_order, mod_order = determine_sub_operations(seed2)

    processed_blocks = 0
    progress_lock = threading.Lock()

    def process_block(i, block):
        block_matrix = utils.bytes_to_matrix(block)

        # 🔑 Deterministic, index-based subkey derivation
        subkey = key_utils.derive_subkey(primary_hash, raw_key, i)
        subkey_matrix = utils.bytes_to_matrix(subkey)

        for op in reversed(op_order):
            if op == "permutation":
                block_matrix = reverse_permutation(block_matrix, row_swaps, col_swaps, permutation_order)
            elif op == "modular":
                for t, mod_op in enumerate(mod_order):
                    block_matrix = apply_modular_operations(block_matrix, subkey_matrix, mod_op, t == 0)
            elif op == "xor":
                block_matrix = apply_xor(block_matrix, subkey_matrix)

        block = utils.matrix_to_bytes(block_matrix)

        if i == num_blocks - 1:
            block = utils.truncate_block(block, last_block_size)

        del block_matrix, subkey_matrix
        return block

    with ThreadPoolExecutor(max_workers=cores) as executor:
        block_iterator = enumerate(utils.read_file_in_blocks(input_path, pointer=header_size))
        futures = set()
        future_to_block = {}

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
            done, futures = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED
            )

            for future in done:
                i = future_to_block[future]
                results[i] = future.result()
                del future_to_block[future]

                while next_index in results:
                    utils.write_to_file(output_path, results[next_index])
                    del results[next_index]
                    next_index += 1

                    if signals:
                        with progress_lock:
                            processed_blocks += 1
                            progress_percent = int((processed_blocks / num_blocks) * 100)
                            if processed_blocks == num_blocks:
                                signals.time2.emit()
                            signals.progress_update.emit(progress_percent)
                            signals.nblock_update.emit(processed_blocks, num_blocks)
                            signals.terminal_progress.emit(processed_blocks, num_blocks)

                try:
                    i, block = next(block_iterator)
                    new_future = executor.submit(process_block, i, block)
                    futures.add(new_future)
                    future_to_block[new_future] = i
                except StopIteration:
                    pass

    gc.collect()


# === unchanged helpers below ===

def apply_xor(matrix, subkey):
    return matrix ^ subkey


def apply_permutation(matrix, row_swaps, col_swaps, order):
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
    temp_matrix = matrix.copy()
    temp_subkey = subkey.copy()
    if transpose:
        temp_subkey = temp_subkey.T
    if mod_op == "add":
        return ((temp_matrix.astype(np.uint16) + temp_subkey.astype(np.uint16)) % 256).astype(np.uint8)
    else:
        return ((temp_matrix.astype(np.uint16) - temp_subkey.astype(np.uint16)) % 256).astype(np.uint8)


def determine_operation_sequence(seed1):
    rng = random.Random(seed1)
    operations = OPERATIONS.copy()
    rng.shuffle(operations)
    return operations


def determine_sub_operations(seed2):
    rng = random.Random(seed2)
    row_swaps = [(rng.randint(0, MATRIX_SIZE - 1), rng.randint(0, MATRIX_SIZE - 1)) for _ in range(SWAP_COUNT)]
    col_swaps = [(rng.randint(0, MATRIX_SIZE - 1), rng.randint(0, MATRIX_SIZE - 1)) for _ in range(SWAP_COUNT)]
    mod_order = MOD_ORDER.copy()
    permutation_order = PERMUTATION_ORDER.copy()
    rng.shuffle(mod_order)
    rng.shuffle(permutation_order)
    return row_swaps, col_swaps, permutation_order, mod_order
