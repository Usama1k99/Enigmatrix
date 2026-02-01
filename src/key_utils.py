import hashlib
import os
from cfg import *
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

algorithms = {
    "blake2b": hashlib.blake2b,
    "sha512": hashlib.sha512
}


def generate_rsa_keypair(key_name, path):
    private_key_file = os.path.join(path, f"{key_name}_private.pem")
    public_key_file = os.path.join(path, f"{key_name}_public.pem")

    key = RSA.generate(RSA_KEY_SIZE)
    private_key = key.export_key()
    public_key = key.publickey().export_key()

    with open(private_key_file, "wb") as priv_file:
        priv_file.write(private_key)

    with open(public_key_file, "wb") as pub_file:
        pub_file.write(public_key)


def detect_rsa_key(file_path):
    try:
        with open(file_path, "r") as file:
            first_line = file.readline().strip()
            if "PRIVATE KEY" in first_line:
                return "private"
            elif "PUBLIC KEY" in first_line:
                return "public"
    except:
        return None
    return None


def rsa_encrypt_key(raw_key, public_key):
    cipher = PKCS1_OAEP.new(public_key)
    encrypted_key = cipher.encrypt(raw_key)
    return encrypted_key


def rsa_decrypt_key(encrypted_key, private_key):
    cipher = PKCS1_OAEP.new(private_key)
    decrypted_key = cipher.decrypt(encrypted_key)
    return decrypted_key


def load_rsa_key(file_path):
    with open(file_path, "rb") as f:
        key = RSA.import_key(f.read())
    return key


def primary_hash(raw_key):
    return hashlib.sha512(raw_key).digest()


# ==========================================================
# Deterministic, index-based subkey derivation (NEW)
# ==========================================================

def derive_subkey(primary_hash, raw_key, block_index):
    """
    Deterministically derives a 1MB subkey for a given block index.
    This replaces the non-deterministic streaming generator for
    parallel-safe encryption/decryption.
    """
    index_bytes = block_index.to_bytes(8, "big")

    # Domain-separated seed for this block
    seed = hashlib.sha512(primary_hash + raw_key + index_bytes).digest()

    # Reuse existing expansion logic
    return expand_subkey(seed + raw_key, "sha512")


def key_expansion_stream(primary_hash, raw_key, num_blocks):
    """
    Legacy sequential key expansion generator.
    Retained for compatibility but NOT used in file encryption anymore.
    """
    algorithm_toggle = True
    temp_key = raw_key

    for _ in range(num_blocks):
        algorithm_name = "sha512" if algorithm_toggle else "blake2b"
        algorithm = algorithms[algorithm_name]

        initial_subkey = algorithm(primary_hash + temp_key).digest()
        sub_key = expand_subkey(initial_subkey + temp_key, algorithm_name)

        temp_key = initial_subkey
        algorithm_toggle = not algorithm_toggle

        yield sub_key


def expand_subkey(initial_seed, algorithm_name):
    """
    Expands an initial hash seed into a full 1MB subkey using XOR feedback.
    """
    hashing_algorithm = algorithms[algorithm_name]
    expanded_key = bytearray()

    prev_hash = hashing_algorithm(initial_seed).digest()

    while len(expanded_key) < BLOCK_SIZE:
        new_hash = hashing_algorithm(prev_hash).digest()
        xored_hash = bytes(a ^ b for a, b in zip(prev_hash, new_hash))
        expanded_key.extend(xored_hash)
        prev_hash = new_hash

    return expanded_key[:BLOCK_SIZE]


def extract_prng_seeds(primary_hash):
    half_len = len(primary_hash) // 2
    quarter_len = half_len // 2

    part1 = int.from_bytes(primary_hash[:quarter_len], "big")
    part2 = int.from_bytes(primary_hash[quarter_len:half_len], "big")
    part3 = int.from_bytes(primary_hash[half_len:half_len + quarter_len], "big")
    part4 = int.from_bytes(primary_hash[half_len + quarter_len:], "big")

    seed1 = part1 ^ part3
    seed2 = part2 ^ part4

    return seed1, seed2
