"""API key encryption utilities using Fernet symmetric encryption."""

import os
import base64
from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    """Get Fernet instance with encryption key."""
    key = settings.encryption_key

    if not key:
        # Generate a key for development (not recommended for production)
        # In production, set ENCRYPTION_KEY env var
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()

    # Ensure key is proper format
    if isinstance(key, str):
        key = key.encode()

    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for storage.

    Args:
        api_key: The plaintext API key

    Returns:
        Base64-encoded encrypted key
    """
    fernet = _get_fernet()
    encrypted = fernet.encrypt(api_key.encode())
    return encrypted.decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt a stored API key.

    Args:
        encrypted_key: Base64-encoded encrypted key

    Returns:
        Plaintext API key
    """
    fernet = _get_fernet()
    decrypted = fernet.decrypt(encrypted_key.encode())
    return decrypted.decode()


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Use this to generate a key for the ENCRYPTION_KEY env var:
        python -c "from app.utils.encryption import generate_encryption_key; print(generate_encryption_key())"
    """
    return Fernet.generate_key().decode()
