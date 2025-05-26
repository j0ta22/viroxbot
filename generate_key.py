from cryptography.fernet import Fernet
import base64

# Generar una nueva key
key = Fernet.generate_key()

# Convertir a string para guardar en .env
key_string = key.decode()

print("\n=== Encryption Key Generada ===\n")
print(f"ENCRYPTION_KEY={key_string}")
print("\nCopia esta línea y pégala en tu archivo .env\n") 