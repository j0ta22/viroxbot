import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging

logger = logging.getLogger(__name__)

def get_encryption_key(salt=None):
    """
    Genera una clave de encriptación usando PBKDF2
    """
    try:
        if salt is None:
            salt = os.urandom(16)
        elif isinstance(salt, str):
            salt = salt.encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(os.getenv('ENCRYPTION_KEY').encode()))
        return Fernet(key), salt
    except Exception as e:
        logger.error(f"Error al generar clave de encriptación: {e}")
        raise

def encrypt_private_key(private_key: str, salt: str) -> bytes:
    """Encriptar una clave privada usando Fernet"""
    try:
        f = Fernet(get_encryption_key(salt))
        # Asegurarnos de que la clave privada esté en bytes
        if isinstance(private_key, str):
            private_key = private_key.encode()
        encrypted_data = f.encrypt(private_key)
        logger.info("Clave encriptada correctamente")
        return encrypted_data
    except Exception as e:
        logger.error(f"Error al encriptar clave privada: {e}")
        raise

def decrypt_private_key(encrypted_data: bytes, salt: str) -> str:
    """Desencriptar una clave privada usando Fernet"""
    try:
        f = Fernet(get_encryption_key(salt))
        # Asegurarnos de que los datos encriptados estén en bytes
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        decrypted_data = f.decrypt(encrypted_data)
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Error al desencriptar clave privada: {e}")
        raise 