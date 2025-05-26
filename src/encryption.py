import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging
from typing import Union

logger = logging.getLogger(__name__)

def get_encryption_key(salt: Union[str, bytes]) -> bytes:
    """Generar una clave de encriptación usando el salt y la clave de encriptación"""
    try:
        # Asegurarse de que el salt sea bytes
        if isinstance(salt, str):
            salt = salt.encode()
        
        # Asegurarse de que la clave de encriptación sea bytes
        key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
        
        # Generar la clave usando PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(key))
    except Exception as e:
        logger.error(f"Error al generar clave de encriptación: {e}")
        raise

def encrypt_private_key(private_key: str, salt: Union[str, bytes]) -> bytes:
    """Encriptar una clave privada usando Fernet"""
    try:
        # Asegurarse de que la clave privada sea string
        if not isinstance(private_key, str):
            raise ValueError("La clave privada debe ser un string")
            
        # Asegurarse de que el salt sea bytes
        if isinstance(salt, str):
            salt = salt.encode()
            
        # Generar la clave de encriptación
        key = get_encryption_key(salt)
        
        # Crear el cifrador Fernet
        f = Fernet(key)
        
        # Encriptar la clave privada
        encrypted_data = f.encrypt(private_key.encode())
        return encrypted_data
    except Exception as e:
        logger.error(f"Error al encriptar clave privada: {e}")
        raise

def decrypt_private_key(encrypted_data: bytes, salt: Union[str, bytes]) -> str:
    """Desencriptar una clave privada usando Fernet"""
    try:
        # Asegurarse de que los datos encriptados sean bytes
        if not isinstance(encrypted_data, bytes):
            raise ValueError("Los datos encriptados deben ser bytes")
            
        # Asegurarse de que el salt sea bytes
        if isinstance(salt, str):
            salt = salt.encode()
            
        # Generar la clave de encriptación
        key = get_encryption_key(salt)
        
        # Crear el cifrador Fernet
        f = Fernet(key)
        
        # Desencriptar la clave privada
        decrypted_data = f.decrypt(encrypted_data)
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Error al desencriptar clave privada: {e}")
        raise 