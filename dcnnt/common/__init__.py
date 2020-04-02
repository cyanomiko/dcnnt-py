from Crypto.Hash import SHA256
from Crypto.Cipher import AES

from .jsonrpc import *
from .jsonconf import *


def derive_key(password: str) -> bytes:
    """Create 256 bit device key from password - not really secure"""
    return SHA256.new(password.encode()).digest()


def encrypt(data: bytes, key: bytes) -> bytes:
    """Encrypt data using AES in GCM mode, nonce and digest included"""
    cipher = AES.new(key, AES.MODE_GCM)
    encrypted, digest = cipher.encrypt_and_digest(data)
    return b''.join((cipher.nonce, encrypted, digest))


def decrypt(data: bytes, key: bytes) -> Optional[bytes]:
    """Decrypt data using AES in GCM mode, also check integrity"""
    cipher = AES.new(key, AES.MODE_GCM, nonce=data[:16])
    try:
        return cipher.decrypt_and_verify(data[16:-16], data[-16:])
    except (ValueError, KeyError):
        return
