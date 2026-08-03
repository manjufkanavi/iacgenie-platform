"""

Encryption utilities for secure API key storage

"""

import os

import base64

from cryptography.fernet import Fernet

from cryptography.hazmat.primitives import hashes

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from typing import Optional

from dotenv import load_dotenv

# Load environment variables

load_dotenv()


def generate_fernet_key() -> str:
    """Generate a new Fernet key for encryption"""
    return Fernet.generate_key().decode()


def get_fernet_key() -> bytes:
    """Get the Fernet key from environment or generate a new one"""
    fernet_key = os.getenv("FERNET_KEY")
    if not fernet_key:
        # Generate a new key if not exists
        fernet_key = generate_fernet_key()
        print(
            f"⚠️  FERNET_KEY not found in environment. Generated new key: {fernet_key}"
        )
        print("Please add FERNET_KEY to your .env file for production use.")
        # Store the generated key in environment for this session
        os.environ["FERNET_KEY"] = fernet_key
    # Ensure the key is in bytes format
    if isinstance(fernet_key, str):
        return fernet_key.encode()
    return fernet_key


def encrypt_key(key: str) -> str:
    """Encrypt an API key using Fernet"""
    if not key:
        raise ValueError("API key cannot be empty")
    try:
        fernet = Fernet(get_fernet_key())
        encrypted = fernet.encrypt(key.encode())
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        raise ValueError(f"Failed to encrypt API key: {str(e)}")


def decrypt_key(encrypted_key: str) -> str:
    """Decrypt an API key using Fernet"""
    if not encrypted_key:
        raise ValueError("Encrypted key cannot be empty")
    try:
        fernet = Fernet(get_fernet_key())
        # Decode from base64 first
        encrypted_bytes = base64.b64decode(encrypted_key.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt API key: {str(e)}")


def derive_key_from_password(
    password: str, salt: Optional[bytes] = None
) -> tuple[bytes, bytes]:
    """Derive a key from a password using PBKDF2"""
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def encrypt_with_password(data: str, password: str) -> str:
    """Encrypt data with a password"""
    key, salt = derive_key_from_password(password)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data.encode())
    # Combine salt and encrypted data
    combined = salt + encrypted
    return base64.b64encode(combined).decode()


def decrypt_with_password(encrypted_data: str, password: str) -> str:
    """Decrypt data with a password"""
    try:
        combined = base64.b64decode(encrypted_data.encode())
        salt = combined[:16]
        encrypted = combined[16:]
        key, _ = derive_key_from_password(password, salt)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt data: {str(e)}")
