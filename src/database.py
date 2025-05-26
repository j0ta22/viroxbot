import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Obtener conexión a la base de datos PostgreSQL"""
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def init_db():
    """Inicializar la base de datos"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Crear tabla de wallets
    cur.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            user_id BIGINT,
            private_key TEXT,
            salt TEXT,
            PRIMARY KEY (user_id, private_key)
        )
    ''')
    
    # Crear tabla de destinos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS destinations (
            user_id BIGINT PRIMARY KEY,
            address TEXT
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

def save_wallet(user_id, private_key, salt):
    """Guardar una wallet en la base de datos"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO wallets (user_id, private_key, salt) VALUES (%s, %s, %s)',
            (user_id, private_key, salt)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving wallet: {e}")
        return False

def get_user_wallets(user_id):
    """Obtener las wallets de un usuario"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute('SELECT private_key, salt FROM wallets WHERE user_id = %s', (user_id,))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
    except Exception as e:
        print(f"Error getting wallets: {e}")
        return []

def save_destination(user_id, address):
    """Guardar la dirección de destino en la base de datos"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO destinations (user_id, address) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET address = %s',
            (user_id, address, address)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving destination: {e}")
        return False

def get_user_destination(user_id):
    """Obtener la dirección de destino de un usuario"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT address FROM destinations WHERE user_id = %s', (user_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting destination: {e}")
        return None

def delete_user_wallets(user_id):
    """Eliminar todas las wallets de un usuario"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM wallets WHERE user_id = %s', (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting wallets: {e}")
        return False 