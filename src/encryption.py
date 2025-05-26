import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

def get_encryption_key(salt=None):
    """Generar una clave de encriptación"""
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(os.getenv('ENCRYPTION_KEY').encode()))
    return Fernet(key), salt

def encrypt_private_key(private_key, salt=None):
    """Encriptar una clave privada"""
    f, salt = get_encryption_key(salt)
    encrypted_data = f.encrypt(private_key.encode())
    return encrypted_data, salt

def decrypt_private_key(encrypted_data, salt):
    """Desencriptar una clave privada"""
    f, _ = get_encryption_key(salt)
    return f.decrypt(encrypted_data).decode() 