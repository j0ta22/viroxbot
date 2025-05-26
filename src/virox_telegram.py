import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv
from database import init_db, save_wallet, get_user_wallets, save_destination, get_user_destination, delete_user_wallets
from web3_utils import get_wallets_info, check_balances, transfer_tokens
from encryption import encrypt_private_key, decrypt_private_key
from web3 import Web3

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configuración del bot
TOKEN = os.getenv('TELEGRAM_TOKEN')
BASE_RPC_URL = os.getenv('BASE_RPC_URL')

# Inicializar la base de datos
init_db()

# Estados de usuario
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar el comando /start"""
    keyboard = [
        [InlineKeyboardButton("➕ Añadir Wallet", callback_data='add_wallet')],
        [InlineKeyboardButton("👛 Ver Wallets", callback_data='view_wallets')],
        [InlineKeyboardButton("🎯 Configurar Destino", callback_data='set_destination')],
        [InlineKeyboardButton("❌ Eliminar Wallets", callback_data='delete_wallets')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 Virox Bot 2.0 - Más virolo que nunca\n\n"
        "Bienvenido al gestor de wallets. Por favor, selecciona una opción:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar el comando /help"""
    help_text = (
        "Comandos disponibles:\n"
        "/start - Gestionar wallets\n"
        "/check <dirección> - Verificar balance de tokens\n"
        "/transfer <dirección> - Transferir tokens\n"
        "/wallets - Ver billeteras y balances en ETH\n"
        "/help - Mostrar esta ayuda"
    )
    await update.message.reply_text(help_text)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar los botones inline"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'add_wallet':
        user_states[query.from_user.id] = 'waiting_private_key'
        await query.message.reply_text(
            "Por favor, envía la private key de tu wallet.\n"
            "⚠️ Asegúrate de que sea una private key válida de Base."
        )
    
    elif query.data == 'view_wallets':
        wallets = get_user_wallets(query.from_user.id)
        if not wallets:
            await query.message.reply_text("No tienes wallets guardadas.")
            return
        
        message = "📋 Tus Wallets:\n\n"
        for wallet in wallets:
            decrypted_key = decrypt_private_key(wallet['private_key'], wallet['salt'])
            address = Web3().eth.account.from_key(decrypted_key).address
            message += f"📍 {address}\n"
        
        await query.message.reply_text(message)
    
    elif query.data == 'set_destination':
        user_states[query.from_user.id] = 'waiting_destination'
        await query.message.reply_text(
            "Por favor, envía la dirección de destino para las transferencias.\n"
            "⚠️ Asegúrate de que sea una dirección válida de Base."
        )
    
    elif query.data == 'delete_wallets':
        if delete_user_wallets(query.from_user.id):
            await query.message.reply_text("✅ Todas tus wallets han sido eliminadas.")
        else:
            await query.message.reply_text("❌ Error al eliminar las wallets.")

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes de texto"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    if user_id not in user_states:
        await update.message.reply_text(
            "Por favor, usa los botones del menú para interactuar con el bot."
        )
        return
    
    if user_states[user_id] == 'waiting_private_key':
        if not Web3().is_address(Web3().eth.account.from_key(text).address):
            await update.message.reply_text("❌ Private key inválida. Por favor, intenta de nuevo.")
            return
        
        salt = os.urandom(16).hex()
        encrypted_key = encrypt_private_key(text, salt)
        
        if save_wallet(user_id, encrypted_key, salt):
            await update.message.reply_text("✅ Wallet guardada exitosamente!")
        else:
            await update.message.reply_text("❌ Error al guardar la wallet.")
        
        del user_states[user_id]
    
    elif user_states[user_id] == 'waiting_destination':
        if not Web3().is_address(text):
            await update.message.reply_text("❌ Dirección inválida. Por favor, intenta de nuevo.")
            return
        
        if save_destination(user_id, text):
            await update.message.reply_text("✅ Dirección de destino guardada exitosamente!")
        else:
            await update.message.reply_text("❌ Error al guardar la dirección de destino.")
        
        del user_states[user_id]

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar el comando /check"""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Uso incorrecto. Por favor usa: /check <dirección_del_token>"
        )
        return
    
    token_address = context.args[0]
    if not Web3().is_address(token_address):
        await update.message.reply_text("❌ Dirección de token inválida.")
        return
    
    wallets = get_user_wallets(update.message.from_user.id)
    if not wallets:
        await update.message.reply_text("No tienes wallets guardadas.")
        return
    
    message = "🔍 Verificando balances...\n\n"
    for wallet in wallets:
        decrypted_key = decrypt_private_key(wallet['private_key'], wallet['salt'])
        balance = check_balances(decrypted_key, token_address)
        message += f"💰 Balance: {balance}\n"
    
    await update.message.reply_text(message)

async def transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar el comando /transfer"""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Uso incorrecto. Por favor usa: /transfer <dirección_del_token>"
        )
        return
    
    token_address = context.args[0]
    if not Web3().is_address(token_address):
        await update.message.reply_text("❌ Dirección de token inválida.")
        return
    
    destination = get_user_destination(update.message.from_user.id)
    if not destination:
        await update.message.reply_text(
            "❌ No has configurado una dirección de destino.\n"
            "Usa el botón '🎯 Configurar Destino' para establecerla."
        )
        return
    
    wallets = get_user_wallets(update.message.from_user.id)
    if not wallets:
        await update.message.reply_text("No tienes wallets guardadas.")
        return
    
    message = "🔄 Iniciando transferencias...\n\n"
    for wallet in wallets:
        decrypted_key = decrypt_private_key(wallet['private_key'], wallet['salt'])
        result = transfer_tokens(decrypted_key, token_address, destination)
        message += f"📝 {result}\n"
    
    await update.message.reply_text(message)

async def wallets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar el comando /wallets"""
    wallets = get_user_wallets(update.message.from_user.id)
    if not wallets:
        await update.message.reply_text("No tienes wallets guardadas.")
        return
    
    message = "📋 Tus Wallets:\n\n"
    for wallet in wallets:
        decrypted_key = decrypt_private_key(wallet['private_key'], wallet['salt'])
        address = Web3().eth.account.from_key(decrypted_key).address
        balance_wei = Web3().eth.get_balance(address)
        balance_eth = Web3().from_wei(balance_wei, 'ether')
        message += f"📍 {address}\n💰 {balance_eth:.4f} ETH\n\n"
    
    destination = get_user_destination(update.message.from_user.id)
    if destination:
        balance_wei = Web3().eth.get_balance(destination)
        balance_eth = Web3().from_wei(balance_wei, 'ether')
        message += f"🎯 Destino: {destination}\n💰 {balance_eth:.4f} ETH"
    
    await update.message.reply_text(message)

def main():
    """Función principal"""
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("transfer", transfer_command))
    application.add_handler(CommandHandler("wallets", wallets_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    
    # Iniciar el bot
    application.run_polling()

if __name__ == '__main__':
    main()