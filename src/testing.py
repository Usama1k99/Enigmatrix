import os

def read_file_in_chunks(file_path):
    """Reads a file in chunks and returns a generator."""
    with open(file_path, "rb") as file:
        while chunk := file.read(CHUNK_SIZE):
            yield chunk  # Yield each chunk for processing

def write_to_file(output_path, chunks):
    """Writes processed chunks to a new file."""
    with open(output_path, "wb") as file:
        for chunk in chunks:
            file.write(chunk)

# Example usage
input_file = "./Demo/Original/rdr2 main files.png"
output_file = "./Demo/Encrypted/rewrite.enc"

# Read and write file without modification (just copying for now)
chunks = read_file_in_chunks(input_file)
write_to_file(output_file, chunks)