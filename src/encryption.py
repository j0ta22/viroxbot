import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

def get_encryption_key(salt=None):
    """
    Genera una clave de encriptación usando PBKDF2
    """
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

def encrypt_private_key(private_key, salt=None):
    """
    Encripta una clave privada usando Fernet
    """
    f, salt = get_encryption_key(salt)
    encrypted_data = f.encrypt(private_key.encode())
    return encrypted_data, salt

def decrypt_private_key(encrypted_data, salt):
    """
    Desencripta una clave privada usando Fernet
    """
    if isinstance(salt, str):
        salt = salt.encode()
    f, _ = get_encryption_key(salt)
    decrypted_data = f.decrypt(encrypted_data)
    return decrypted_data.decode() 