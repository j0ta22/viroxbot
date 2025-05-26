import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
import logging

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

def get_db_connection():
    """Obtener conexión a la base de datos PostgreSQL"""
    try:
        # Intentar obtener la URL de la base de datos
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL no está configurada en las variables de entorno")
        
        # Establecer la conexión
        conn = psycopg2.connect(database_url)
        logger.info("Conexión a la base de datos establecida exitosamente")
        return conn
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        raise

def init_db():
    """Inicializar la base de datos"""
    try:
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
        logger.info("Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
        raise
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
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
        logger.info(f"Wallet guardada exitosamente para el usuario {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar wallet: {e}")
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def get_user_wallets(user_id):
    """Obtener las wallets de un usuario"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute('SELECT private_key, salt FROM wallets WHERE user_id = %s', (user_id,))
        results = cur.fetchall()
        logger.info(f"Wallets obtenidas para el usuario {user_id}")
        return results
    except Exception as e:
        logger.error(f"Error al obtener wallets: {e}")
        return []
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

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
        logger.info(f"Dirección de destino guardada para el usuario {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar dirección de destino: {e}")
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def get_user_destination(user_id):
    """Obtener la dirección de destino de un usuario"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT address FROM destinations WHERE user_id = %s', (user_id,))
        result = cur.fetchone()
        if result:
            logger.info(f"Dirección de destino obtenida para el usuario {user_id}")
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Error al obtener dirección de destino: {e}")
        return None
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def delete_user_wallets(user_id):
    """Eliminar todas las wallets de un usuario"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM wallets WHERE user_id = %s', (user_id,))
        conn.commit()
        logger.info(f"Wallets eliminadas para el usuario {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error al eliminar wallets: {e}")
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close() 