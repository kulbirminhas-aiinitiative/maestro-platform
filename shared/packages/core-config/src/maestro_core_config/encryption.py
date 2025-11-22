"""
Configuration encryption utilities.

Provides encryption/decryption for sensitive configuration values.
"""

import base64
import os
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet, InvalidToken
from maestro_core_logging import get_logger

def _get_logger():
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except:
        import logging
        return logging.getLogger(__name__)

logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


class ConfigEncryption:
    """
    Encrypt and decrypt configuration values.

    Uses Fernet (symmetric encryption) from the cryptography library.

    Example:
        >>> encryption = ConfigEncryption()
        >>> encrypted = encryption.encrypt("my-secret-password")
        >>> print(encrypted)
        gAAAAABh...
        >>> decrypted = encryption.decrypt(encrypted)
        >>> print(decrypted)
        my-secret-password
    """

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize encryption handler.

        Args:
            key: Encryption key (32 url-safe base64-encoded bytes).
                 If not provided, reads from MAESTRO_ENCRYPTION_KEY env var.
                 If env var not set, generates a new key (not recommended for production).

        Example:
            >>> # With explicit key
            >>> key = Fernet.generate_key()
            >>> encryption = ConfigEncryption(key=key)
            >>>
            >>> # From environment variable
            >>> # Set MAESTRO_ENCRYPTION_KEY=<your-key>
            >>> encryption = ConfigEncryption()
        """
        if key is None:
            # Try to load from environment
            key_str = os.getenv("MAESTRO_ENCRYPTION_KEY")
            if key_str:
                key = key_str.encode()
                logger.info("Loaded encryption key from environment")
            else:
                # Generate new key (warn in production)
                key = Fernet.generate_key()
                logger.warning(
                    "Generated new encryption key - set MAESTRO_ENCRYPTION_KEY for production",
                    key=key.decode()
                )

        self.cipher = Fernet(key)
        self.key = key

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a new encryption key.

        Returns:
            32 url-safe base64-encoded bytes

        Example:
            >>> key = ConfigEncryption.generate_key()
            >>> print(key.decode())
            abc123...
        """
        return Fernet.generate_key()

    def encrypt(self, value: str) -> str:
        """
        Encrypt a string value.

        Args:
            value: Plain text value to encrypt

        Returns:
            Base64-encoded encrypted value

        Example:
            >>> encryption = ConfigEncryption()
            >>> encrypted = encryption.encrypt("secret123")
        """
        if not value:
            return value

        try:
            encrypted_bytes = self.cipher.encrypt(value.encode())
            encrypted_str = encrypted_bytes.decode()
            logger.debug("Encrypted configuration value")
            return encrypted_str
        except Exception as e:
            logger.error("Failed to encrypt value", error=str(e))
            raise ValueError(f"Encryption failed: {e}")

    def decrypt(self, encrypted_value: str) -> str:
        """
        Decrypt an encrypted string value.

        Args:
            encrypted_value: Base64-encoded encrypted value

        Returns:
            Decrypted plain text value

        Raises:
            ValueError: If decryption fails (invalid key or corrupted data)

        Example:
            >>> encryption = ConfigEncryption()
            >>> decrypted = encryption.decrypt("gAAAAABh...")
        """
        if not encrypted_value:
            return encrypted_value

        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_value.encode())
            decrypted_str = decrypted_bytes.decode()
            logger.debug("Decrypted configuration value")
            return decrypted_str
        except InvalidToken:
            logger.error("Failed to decrypt value - invalid key or corrupted data")
            raise ValueError("Decryption failed: Invalid key or corrupted data")
        except Exception as e:
            logger.error("Failed to decrypt value", error=str(e))
            raise ValueError(f"Decryption failed: {e}")

    def encrypt_dict(self, data: Dict[str, Any], keys_to_encrypt: list[str]) -> Dict[str, Any]:
        """
        Encrypt specific keys in a dictionary.

        Args:
            data: Dictionary to process
            keys_to_encrypt: List of keys to encrypt

        Returns:
            Dictionary with specified keys encrypted

        Example:
            >>> config = {
            ...     "database_host": "localhost",
            ...     "database_password": "secret123"
            ... }
            >>> encrypted = encryption.encrypt_dict(config, ["database_password"])
            >>> print(encrypted["database_password"])
            gAAAAABh...
        """
        result = data.copy()

        for key in keys_to_encrypt:
            if key in result and isinstance(result[key], str):
                result[key] = self.encrypt(result[key])
                logger.debug(f"Encrypted dictionary key", key=key)

        return result

    def decrypt_dict(self, data: Dict[str, Any], keys_to_decrypt: list[str]) -> Dict[str, Any]:
        """
        Decrypt specific keys in a dictionary.

        Args:
            data: Dictionary to process
            keys_to_decrypt: List of keys to decrypt

        Returns:
            Dictionary with specified keys decrypted

        Example:
            >>> encrypted_config = {"database_password": "gAAAAABh..."}
            >>> decrypted = encryption.decrypt_dict(encrypted_config, ["database_password"])
            >>> print(decrypted["database_password"])
            secret123
        """
        result = data.copy()

        for key in keys_to_decrypt:
            if key in result and isinstance(result[key], str):
                try:
                    result[key] = self.decrypt(result[key])
                    logger.debug(f"Decrypted dictionary key", key=key)
                except ValueError:
                    # Key might not be encrypted, leave as-is
                    logger.debug(f"Key not encrypted, leaving as-is", key=key)

        return result

    def rotate_key(self, new_key: bytes, data: Dict[str, Any], keys_to_rotate: list[str]) -> Dict[str, Any]:
        """
        Rotate encryption key for specific keys in a dictionary.

        Decrypts with old key and re-encrypts with new key.

        Args:
            new_key: New encryption key
            data: Dictionary to process
            keys_to_rotate: List of keys to rotate

        Returns:
            Dictionary with keys re-encrypted using new key

        Example:
            >>> old_encryption = ConfigEncryption(old_key)
            >>> new_key = ConfigEncryption.generate_key()
            >>> encrypted_config = {"password": "gAAAAABh..."}
            >>> rotated = old_encryption.rotate_key(new_key, encrypted_config, ["password"])
        """
        # Decrypt with old key
        decrypted = self.decrypt_dict(data, keys_to_rotate)

        # Create new cipher with new key
        new_cipher = ConfigEncryption(key=new_key)

        # Encrypt with new key
        result = new_cipher.encrypt_dict(decrypted, keys_to_rotate)

        logger.info(f"Rotated encryption key for {len(keys_to_rotate)} keys")
        return result

    def get_key(self) -> str:
        """
        Get the encryption key as a string.

        Returns:
            Encryption key as base64-encoded string

        Example:
            >>> encryption = ConfigEncryption()
            >>> key = encryption.get_key()
            >>> print(key)
            abc123...
        """
        return self.key.decode()


def encrypt_config_file(
    input_file: str,
    output_file: str,
    keys_to_encrypt: list[str],
    encryption_key: Optional[bytes] = None
) -> None:
    """
    Encrypt specific keys in a configuration file.

    Supports JSON and YAML files.

    Args:
        input_file: Path to input configuration file
        output_file: Path to output encrypted configuration file
        keys_to_encrypt: List of keys to encrypt
        encryption_key: Encryption key (generates new if not provided)

    Example:
        >>> encrypt_config_file(
        ...     "config.yaml",
        ...     "config.encrypted.yaml",
        ...     ["database_password", "api_key"]
        ... )
    """
    import json
    import yaml
    from pathlib import Path

    # Determine file format
    input_path = Path(input_file)
    suffix = input_path.suffix.lower()

    # Load configuration
    if suffix == ".json":
        with open(input_file, 'r') as f:
            config = json.load(f)
    elif suffix in (".yaml", ".yml"):
        with open(input_file, 'r') as f:
            config = yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    # Encrypt keys
    encryption = ConfigEncryption(key=encryption_key)
    encrypted_config = encryption.encrypt_dict(config, keys_to_encrypt)

    # Save encrypted configuration
    output_path = Path(output_file)
    output_suffix = output_path.suffix.lower()

    if output_suffix == ".json":
        with open(output_file, 'w') as f:
            json.dump(encrypted_config, f, indent=2)
    elif output_suffix in (".yaml", ".yml"):
        with open(output_file, 'w') as f:
            yaml.safe_dump(encrypted_config, f, default_flow_style=False)
    else:
        raise ValueError(f"Unsupported output format: {output_suffix}")

    logger.info(
        "Encrypted configuration file",
        input_file=input_file,
        output_file=output_file,
        encrypted_keys=len(keys_to_encrypt)
    )


# Export all
__all__ = [
    "ConfigEncryption",
    "encrypt_config_file",
]
