import hashlib
import os
from cfg import *
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

algorithms = {
    "blake2b": hashlib.blake2b,
    "sha512": hashlib.sha512
}

def generate_rsa_keypair(key_name,path):
    """Generates an RSA key pair and saves them to files."""
    # File naming logic
    private_key_file = os.path.join(path, f"{key_name}_private.pem")
    public_key_file = os.path.join(path, f"{key_name}_public.pem")
    # RSA key pair generation
    key = RSA.generate(RSA_KEY_SIZE)
    private_key = key.export_key()
    public_key = key.publickey().export_key()
    with open(private_key_file, "wb") as priv_file:
        priv_file.write(private_key)
    with open(public_key_file, "wb") as pub_file:
        pub_file.write(public_key)

def detect_rsa_key(file_path):
    """Determines whether an RSA key file is private or public."""
    try:
        with open(file_path, "r") as file:
            first_line = file.readline().strip()  # Read the first line
            if "PRIVATE KEY" in first_line:
                return "private"
            elif "PUBLIC KEY" in first_line:
                return "public"
    except :
        return None
    return None

def rsa_encrypt_key(raw_key, public_key):
    """Encrypts the raw key using RSA public key."""
    cipher = PKCS1_OAEP.new(public_key)
    encrypted_key = cipher.encrypt(raw_key)
    return encrypted_key

def rsa_decrypt_key(encrypted_key, private_key):
    """Decrypts the RSA-encrypted key using the private key."""
    cipher = PKCS1_OAEP.new(private_key)
    decrypted_key = cipher.decrypt(encrypted_key)
    return decrypted_key

def load_rsa_key(file_path):
    """Loads an RSA key from a file."""
    with open(file_path, "rb") as f:
        key = RSA.import_key(f.read())
    return key

def primary_hash(raw_key):
    return hashlib.sha512(raw_key).digest()

def key_expansion_stream(primary_hash, raw_key, num_chunks):
    """Yields one 1MB subkey at a time instead of storing all at once."""
    algorithm_toggle = True
    temp_key = raw_key
    for _ in range(num_chunks):
        algorithm_name = "sha512" if algorithm_toggle else "blake2b"
        algorithm = algorithms[algorithm_name]
        # Generate initial subkey using hash of primary_hash + temp_key
        initial_subkey = algorithm(primary_hash + temp_key).digest()
        # Expand to 1MB subkey
        sub_key = expand_subkey(initial_subkey + temp_key, algorithm_name)
        # Update temp_key for next round
        temp_key = initial_subkey
        algorithm_toggle = not algorithm_toggle
        yield sub_key

def expand_subkey(initial_seed,algorithm_name):
    """Expands an initial hash seed into a full 1MB subkey using XOR feedback."""
    hashing_algorithm = algorithms[algorithm_name]
    expanded_key = bytearray()
    prev_hash = hashing_algorithm(initial_seed).digest()  # H0
    while len(expanded_key) < CHUNK_SIZE:
        new_hash = hashing_algorithm(prev_hash).digest()  # H1, H2, ...
        xored_hash = bytes(a ^ b for a, b in zip(prev_hash, new_hash))  # XOR H(n) with H(n-1)
        expanded_key.extend(xored_hash)  # Append to the expanded key
        prev_hash = new_hash  # Update for next iteration
    return expanded_key[:CHUNK_SIZE]  # Ensure exactly 1MB

def extract_prng_seeds(primary_hash):
    """Extracts two PRNG seeds by XORing sections of the hash."""
    half_len = len(primary_hash) // 2
    quarter_len = half_len // 2
    # Split into four parts
    part1 = int.from_bytes(primary_hash[:quarter_len], "big")
    part2 = int.from_bytes(primary_hash[quarter_len:half_len], "big")
    part3 = int.from_bytes(primary_hash[half_len:half_len + quarter_len], "big")
    part4 = int.from_bytes(primary_hash[half_len + quarter_len:], "big")
    # XOR overlapping sections
    seed1 = part1 ^ part3
    seed2 = part2 ^ part4
    return seed1, seed2
