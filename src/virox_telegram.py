import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from web3 import Web3
from eth_account import Account
import os
from dotenv import load_dotenv
import json
import time
import sqlite3
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets

# Cargar variables de entorno
load_dotenv()

# Configuración de la red Base
BASE_RPC_URL = os.getenv('BASE_RPC_URL')
w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

# ABI del token ERC20
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

# Define tu token
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Configuración de la base de datos
DB_FILE = os.getenv('DB_PATH')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())

# Estados del usuario
user_states = {}

class UserState:
    IDLE = 'IDLE'
    WAITING_FOR_WALLET = 'WAITING_FOR_WALLET'
    WAITING_FOR_DESTINATION = 'WAITING_FOR_DESTINATION'

def init_db():
    """Inicializar la base de datos"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS wallets
        (user_id INTEGER,
         private_key TEXT,
         salt TEXT,
         PRIMARY KEY (user_id, private_key))
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS destinations
        (user_id INTEGER PRIMARY KEY,
         address TEXT)
    ''')
    conn.commit()
    conn.close()

def get_encryption_key(user_id, salt=None):
    """Generar una clave de encriptación única por usuario"""
    if salt is None:
        salt = secrets.token_bytes(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(str(user_id).encode()))
    return Fernet(key), salt

def encrypt_private_key(user_id, private_key):
    """Encriptar una clave privada"""
    f, salt = get_encryption_key(user_id)
    encrypted_data = f.encrypt(private_key.encode())
    return encrypted_data, salt

def decrypt_private_key(user_id, encrypted_data, salt):
    """Desencriptar una clave privada"""
    f, _ = get_encryption_key(user_id, salt)
    return f.decrypt(encrypted_data).decode()

def get_user_wallets(user_id):
    """Obtener las wallets de un usuario"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT private_key, salt FROM wallets WHERE user_id = ?', (user_id,))
    results = c.fetchall()
    conn.close()
    
    private_keys = []
    for encrypted_key, salt in results:
        try:
            private_key = decrypt_private_key(user_id, encrypted_key, base64.b64decode(salt))
            private_keys.append(private_key)
        except Exception as e:
            print(f"Error decrypting key: {e}")
    
    return private_keys

def get_user_destination(user_id):
    """Obtener la dirección de destino de un usuario"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT address FROM destinations WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def save_wallet(user_id, private_key):
    """Guardar una wallet en la base de datos"""
    try:
        encrypted_key, salt = encrypt_private_key(user_id, private_key)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO wallets (user_id, private_key, salt) VALUES (?, ?, ?)',
                 (user_id, encrypted_key, base64.b64encode(salt).decode()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving wallet: {e}")
        return False

def save_destination(user_id, address):
    """Guardar la dirección de destino en la base de datos"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO destinations (user_id, address) VALUES (?, ?)',
                 (user_id, address))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving destination: {e}")
        return False

def create_wallet_menu():
    """Crear el menú de gestión de wallets"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("➕ Agregar Wallet", callback_data="add_wallet"),
        InlineKeyboardButton("🎯 Establecer Destino", callback_data="set_destination")
    )
    markup.row(
        InlineKeyboardButton("📋 Mis Wallets", callback_data="list_wallets"),
        InlineKeyboardButton("❌ Borrar Wallets", callback_data="delete_wallets")
    )
    return markup

# Manejadores de comandos con alta prioridad
@bot.message_handler(commands=["start"])
def cmd_start(message):
    """Comando de inicio"""
    # Inicializar estado del usuario
    user_states[message.from_user.id] = UserState.IDLE
    
    # Enviar el logo
    logo_path = os.getenv('LOGO_PATH')
    with open(logo_path, 'rb') as photo:
        bot.send_photo(
            message.chat.id,
            photo,
            caption="🤖 Virox Bot 2.0 - Más virolo que nunca\n\n"
                   "Bienvenido al gestor de wallets. Por favor, selecciona una opción:",
            reply_markup=create_wallet_menu()
        )

@bot.message_handler(commands=["help"])
def cmd_help(message):
    help_text = "Comandos disponibles:\n" \
                "/start - Gestionar wallets\n" \
                "/check <dirección> - Verificar balance de tokens\n" \
                "/transfer <dirección> - Transferir tokens\n" \
                "/wallets - Ver billeteras y balances en ETH\n" \
                "/help - Mostrar esta ayuda"
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=["check"])
def cmd_check(message):
    args = message.text.split()
    if len(args) != 2:
        bot.send_message(message.chat.id, "Uso correcto: /check <dirección_del_token>")
        return
    token_address = args[1].strip()
    if not Web3.is_address(token_address):
        bot.send_message(message.chat.id, "Error: Dirección de token inválida")
        return
    
    balances = check_balances(token_address, message.from_user.id)
    bot.send_message(message.chat.id, balances, parse_mode="HTML")

@bot.message_handler(commands=["transfer"])
def cmd_transfer(message):
    args = message.text.split()
    if len(args) != 2:
        bot.send_message(message.chat.id, "Uso correcto: /transfer <dirección_del_token>")
        return
    token_address = args[1].strip()
    if not Web3.is_address(token_address):
        bot.send_message(message.chat.id, "Error: Dirección de token inválida")
        return
    
    private_keys = get_user_wallets(message.from_user.id)
    if not private_keys:
        bot.send_message(message.chat.id, "Error: No tienes wallets configuradas")
        return
    
    bot.send_message(message.chat.id, "Iniciando transferencias...", parse_mode="HTML")
    for i, private_key in enumerate(private_keys, 1):
        result = transfer_tokens(token_address, private_key, message.from_user.id)
        bot.send_message(message.chat.id, f"{i}:\n{result}", parse_mode="HTML")
        time.sleep(2)
    bot.send_message(message.chat.id, "✅ <b>Proceso completado!</b>", parse_mode="HTML")

@bot.message_handler(commands=["wallets"])
def cmd_wallets(message):
    info = get_wallets_info(message.from_user.id)
    bot.send_message(message.chat.id, info, parse_mode="HTML")

# Manejador de callbacks de botones
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    """Manejador de callbacks de botones"""
    user_id = call.from_user.id
    
    if call.data == "add_wallet":
        user_states[user_id] = UserState.WAITING_FOR_WALLET
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "📝 Por favor, envía la clave privada de la wallet que deseas agregar\n"
            "(La clave será almacenada de forma segura y encriptada)"
        )
    
    elif call.data == "set_destination":
        user_states[user_id] = UserState.WAITING_FOR_DESTINATION
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "📝 Por favor, envía la dirección de destino para las transferencias"
        )
    
    elif call.data == "list_wallets":
        bot.answer_callback_query(call.id)
        info = get_wallets_info(user_id)
        bot.send_message(call.message.chat.id, info, parse_mode="HTML")
    
    elif call.data == "delete_wallets":
        bot.answer_callback_query(call.id)
        delete_user_wallets(user_id)
        bot.send_message(
            call.message.chat.id,
            "🗑️ Todas tus wallets han sido eliminadas",
            reply_markup=create_wallet_menu()
        )

# Manejador de mensajes de texto con baja prioridad
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) in [UserState.WAITING_FOR_WALLET, UserState.WAITING_FOR_DESTINATION])
def handle_messages(message):
    """Manejador de mensajes de texto para estados específicos"""
    user_id = message.from_user.id
    state = user_states.get(user_id, UserState.IDLE)
    
    if state == UserState.WAITING_FOR_WALLET:
        private_key = message.text.strip()
        try:
            # Validar la clave privada
            account = Account.from_key(private_key)
            if save_wallet(user_id, private_key):
                bot.send_message(
                    message.chat.id,
                    f"✅ Wallet agregada exitosamente\nDirección: <code>{account.address}</code>",
                    parse_mode="HTML",
                    reply_markup=create_wallet_menu()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Error al guardar la wallet",
                    reply_markup=create_wallet_menu()
                )
        except Exception as e:
            bot.send_message(
                message.chat.id,
                "❌ Clave privada inválida",
                reply_markup=create_wallet_menu()
            )
        user_states[user_id] = UserState.IDLE
    
    elif state == UserState.WAITING_FOR_DESTINATION:
        address = message.text.strip()
        if Web3.is_address(address):
            if save_destination(user_id, address):
                bot.send_message(
                    message.chat.id,
                    "✅ Dirección de destino guardada exitosamente",
                    reply_markup=create_wallet_menu()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Error al guardar la dirección de destino",
                    reply_markup=create_wallet_menu()
                )
        else:
            bot.send_message(
                message.chat.id,
                "❌ Dirección inválida",
                reply_markup=create_wallet_menu()
            )
        user_states[user_id] = UserState.IDLE

def delete_user_wallets(user_id):
    """Eliminar todas las wallets de un usuario"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM wallets WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def check_balances(token_address, user_id):
    """Verificar el balance de tokens en todas las wallets del usuario"""
    try:
        private_keys = get_user_wallets(user_id)
        if not private_keys:
            return "❌ No tienes wallets configuradas"

        token_contract = w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        name = token_contract.functions.name().call()
        symbol = token_contract.functions.symbol().call()
        decimals = token_contract.functions.decimals().call()
        total_balance = 0
        balances_text = f"🔎 <b>Balance de Token</b> <code>{token_address}</code>\n"
        balances_text += f"<b>{name} ({symbol})</b>\n\n"

        for i, private_key in enumerate(private_keys, 1):
            account = Account.from_key(private_key)
            balance = token_contract.functions.balanceOf(account.address).call()
            readable_balance = balance / (10 ** decimals)
            total_balance += balance
            balances_text += f"{i}: Balance: <b>{readable_balance:.4f}</b>\n<code>{account.address}</code>\n"

        balances_text += f"\n<b>Total:</b> <b>{total_balance / (10 ** decimals):.4f}</b>\n"
        return balances_text

    except Exception as e:
        return f"Error al verificar balances: {str(e)}"

def transfer_tokens(token_address, private_key, user_id):
    """Transferir tokens desde una wallet a la dirección de destino"""
    try:
        destination = get_user_destination(user_id)
        if not destination:
            return "❌ No has configurado una dirección de destino"

        token_contract = w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        account = Account.from_key(private_key)
        balance = token_contract.functions.balanceOf(account.address).call()
        decimals = token_contract.functions.decimals().call()
        readable_balance = balance / (10 ** decimals)

        if balance == 0:
            return f"Balance: <b>0</b>\n<code>{account.address}</code>\n❌ Sin tokens para transferir"

        nonce = w3.eth.get_transaction_count(account.address)
        gas_price = w3.eth.gas_price

        tx = token_contract.functions.transfer(
            Web3.to_checksum_address(destination),
            balance
        ).build_transaction({
            'chainId': 8453,
            'gas': 100000,
            'gasPrice': gas_price,
            'nonce': nonce,
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)

        return f"Balance transferido: <b>{readable_balance:.4f}</b>\n<code>{account.address}</code>\n✅ Transferencia exitosa\nTx: <code>{tx_hash.hex()}</code>"

    except Exception as e:
        return f"❌ Error al transferir desde <code>{account.address}</code>:\n{str(e)}"

def get_wallets_info(user_id):
    """Obtener información de las wallets y sus balances en ETH"""
    try:
        private_keys = get_user_wallets(user_id)
        destination = get_user_destination(user_id)
        if not private_keys:
            return "❌ No tienes wallets configuradas"

        info_text = "🛠️ <b>Configuración > Billeteras (🪙BASE)</b>\n"
        info_text += "📊 <b>Valor de la Cartera:</b> (solo ETH)\n\n"
        info_text += "<b>Tus billeteras actualmente agregadas:</b>\n"

        for i, private_key in enumerate(private_keys, 1):
            account = Account.from_key(private_key)
            balance_wei = w3.eth.get_balance(account.address)
            balance_eth = w3.from_wei(balance_wei, 'ether')
            info_text += f"{i}: Balance: <b>{balance_eth:.3f}Ξ</b>\n<code>{account.address}</code>\n"

        if destination:
            balance_wei = w3.eth.get_balance(destination)
            balance_eth = w3.from_wei(balance_wei, 'ether')
            info_text += f"\n<b>Destino:</b> <code>{destination}</code>\nBalance: <b>{balance_eth:.3f}Ξ</b>\n"

        info_text += "\n<i>Usa /check &lt;token&gt; o /transfer &lt;token&gt; para operar.</i>"
        return info_text

    except Exception as e:
        return f"Error al obtener información de wallets: {str(e)}"

if __name__ == '__main__':
    init_db()
    print('Iniciando el bot')
    bot.polling()
    print('Fin')