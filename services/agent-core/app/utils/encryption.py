"""API key encryption utilities using Fernet symmetric encryption."""

import base64
import os

from cryptography.fernet import Fernet

from app.config import settings

# Cache the generated key for dev mode (when no ENCRYPTION_KEY is set)
_cached_dev_key: str | None = None


def _get_fernet() -> Fernet:
    """Get Fernet instance with encryption key."""
    global _cached_dev_key

    key = settings.encryption_key

    if not key:
        # Generate a key for development (not recommended for production)
        # In production, set ENCRYPTION_KEY env var
        if _cached_dev_key is None:
            _cached_dev_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        key = _cached_dev_key

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

    Use this to generate a key for the ENCRYPTION_KEY env var::

        python -c "from app.utils.encryption import generate_encryption_key; \\
            print(generate_encryption_key())"
    """
    return Fernet.generate_key().decode()
