import hashlib


def file_hash(file) -> str:
    pos = file.tell()
    file.seek(0)
    hasher = hashlib.sha256()
    while True:
        chunk = file.read(8192)
        if not chunk:
            break
        hasher.update(chunk)
    file.seek(pos)
    return hasher.hexdigest()
