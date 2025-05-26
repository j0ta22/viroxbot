import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv
from database import init_db, save_wallet, get_user_wallets, save_destination, get_user_destination, delete_user_wallets
from web3_utils import get_wallets_info, check_balances, transfer_tokens
from encryption import encrypt_private_key, decrypt_private_key
from web3 import Web3

# Configuración
load_dotenv()

# Variables de entorno
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("No se encontró el token del bot en las variables de entorno")

BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
DB_URL = os.getenv('DATABASE_URL')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

# Verificar variables críticas
if not all([TOKEN, DB_URL, ENCRYPTION_KEY]):
    missing_vars = []
    if not TOKEN:
        missing_vars.append('TELEGRAM_BOT_TOKEN')
    if not DB_URL:
        missing_vars.append('DATABASE_URL')
    if not ENCRYPTION_KEY:
        missing_vars.append('ENCRYPTION_KEY')
    raise ValueError(f"Faltan las siguientes variables de entorno: {', '.join(missing_vars)}")

# Configurar el logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Inicializar la base de datos
init_db()

# Estados de usuario
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar el comando /start"""
    # Enviar la imagen del logo
    try:
        with open('../assets/logo.png', 'rb') as logo:
            await update.message.reply_photo(
                photo=logo,
                caption="🤖 Virox Bot 2.0 - Más virolo que nunca"
            )
    except Exception as e:
        logger.error(f"Error al enviar el logo: {e}")
        # Si falla el envío de la imagen, continuamos con el mensaje de texto
    
    keyboard = [
        [InlineKeyboardButton("➕ Añadir Wallet", callback_data='add_wallet')],
        [InlineKeyboardButton("👛 Ver Wallets", callback_data='view_wallets')],
        [InlineKeyboardButton("🎯 Configurar Destino", callback_data='set_destination')],
        [InlineKeyboardButton("❌ Eliminar Wallets", callback_data='delete_wallets')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
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
    """Maneja los mensajes de texto"""
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # Si el mensaje es una clave privada
    if text.startswith('0x') and len(text) == 66:
        try:
            logger.info(f"Intentando procesar clave privada para usuario {user_id}")
            
            # Intentar crear una cuenta con la clave privada
            account = Web3().eth.account.from_key(text)
            logger.info(f"Cuenta creada con dirección: {account.address}")

            # Generar un nuevo salt para cada clave
            salt = os.urandom(16)
            logger.info("Salt generado correctamente")

            # Encriptar la clave
            encrypted_key = encrypt_private_key(text, salt)
            logger.info("Clave encriptada correctamente")

            # Guardar la wallet
            if save_wallet(user_id, encrypted_key, salt):
                logger.info(f"Wallet guardada correctamente para usuario {user_id}")
                await update.message.reply_text(
                    f"✅ Wallet añadida correctamente\n"
                    f"📍 Dirección: {account.address}\n"
                    f"🔑 Clave encriptada y guardada de forma segura"
                )
            else:
                logger.error(f"Error al guardar wallet para usuario {user_id}")
                await update.message.reply_text("❌ Error al guardar la wallet en la base de datos.")
        except ValueError as ve:
            logger.error(f"Error de valor al procesar clave: {ve}")
            await update.message.reply_text(
                "❌ Clave privada inválida.\n"
                "Por favor, asegúrate de que:\n"
                "- La clave comienza con '0x'\n"
                "- La clave tiene 64 caracteres hexadecimales\n"
                "- La clave es válida para la red Base"
            )
        except Exception as e:
            logger.error(f"Error inesperado al procesar wallet: {e}")
            await update.message.reply_text(
                "❌ Error al procesar la wallet.\n"
                "Por favor, intenta de nuevo o contacta al soporte."
            )
    else:
        logger.info(f"Mensaje recibido no válido: {text[:10]}...")
        await update.message.reply_text(
            "❌ Formato inválido. Por favor, envía una clave privada válida:\n"
            "- Debe comenzar con '0x'\n"
            "- Debe tener 66 caracteres (0x + 64 caracteres hexadecimales)\n"
            "- Debe ser una clave privada válida de Base"
        )

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
        await update.message.reply_text("❌ No tienes wallets guardadas.")
        return
    
    try:
        message = "🔍 Verificando balances...\n\n"
        for wallet in wallets:
            try:
                decrypted_key = decrypt_private_key(wallet['private_key'], wallet['salt'])
                address = Web3().eth.account.from_key(decrypted_key).address
                balance = check_balances(decrypted_key, token_address)
                message += f"📍 {address}\n💰 {balance}\n\n"
            except Exception as e:
                logger.error(f"Error al procesar wallet {address}: {e}")
                message += f"❌ Error al verificar balance: {str(e)}\n\n"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error en check_command: {e}")
        await update.message.reply_text(f"❌ Error al verificar balances: {str(e)}")

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
    try:
        wallets = get_user_wallets(update.message.from_user.id)
        if not wallets:
            await update.message.reply_text("❌ No tienes wallets guardadas.")
            return
        
        message = "📋 Tus Wallets:\n\n"
        for wallet in wallets:
            try:
                # Verificar que los datos estén en el formato correcto
                if not isinstance(wallet['private_key'], bytes):
                    logger.error(f"Formato inválido de private_key para wallet: {wallet}")
                    message += "❌ Error: Formato de wallet inválido\n\n"
                    continue

                decrypted_key = decrypt_private_key(wallet['private_key'], wallet['salt'])
                address = Web3().eth.account.from_key(decrypted_key).address
                balance_wei = Web3().eth.get_balance(address)
                balance_eth = Web3().from_wei(balance_wei, 'ether')
                message += f"📍 {address}\n💰 {balance_eth:.4f} ETH\n\n"
            except Exception as e:
                logger.error(f"Error al procesar wallet: {e}")
                message += f"❌ Error al obtener balance: {str(e)}\n\n"
        
        destination = get_user_destination(update.message.from_user.id)
        if destination:
            try:
                balance_wei = Web3().eth.get_balance(destination)
                balance_eth = Web3().from_wei(balance_wei, 'ether')
                message += f"🎯 Destino: {destination}\n💰 {balance_eth:.4f} ETH"
            except Exception as e:
                logger.error(f"Error al obtener balance de destino: {e}")
                message += f"\n❌ Error al obtener balance de destino: {str(e)}"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error en wallets_command: {e}")
        await update.message.reply_text(f"❌ Error al obtener información de wallets: {str(e)}")

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar el comando /delete"""
    try:
        user_id = update.message.from_user.id
        if delete_user_wallets(user_id):
            await update.message.reply_text("✅ Todas tus wallets han sido eliminadas correctamente.")
        else:
            await update.message.reply_text("❌ No tienes wallets guardadas para eliminar.")
    except Exception as e:
        logger.error(f"Error en delete_command: {e}")
        await update.message.reply_text(f"❌ Error al eliminar wallets: {str(e)}")

async def destination_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar el comando /destination"""
    try:
        user_id = update.message.from_user.id
        
        if not context.args or len(context.args) != 1:
            await update.message.reply_text(
                "❌ Uso incorrecto. Por favor usa: /destination <dirección>\n"
                "Ejemplo: /destination 0x1234..."
            )
            return
        
        destination = context.args[0]
        if not Web3().is_address(destination):
            await update.message.reply_text("❌ Dirección inválida. Por favor, envía una dirección válida de Base.")
            return
        
        if save_destination(user_id, destination):
            await update.message.reply_text(
                f"✅ Dirección de destino guardada correctamente:\n"
                f"🎯 {destination}"
            )
        else:
            await update.message.reply_text("❌ Error al guardar la dirección de destino.")
    except Exception as e:
        logger.error(f"Error en destination_command: {e}")
        await update.message.reply_text(f"❌ Error al configurar destino: {str(e)}")

def main():
    """Función principal para iniciar el bot"""
    try:
        # Crear la aplicación
        application = Application.builder().token(TOKEN).build()

        # Añadir manejadores
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("wallets", wallets_command))
        application.add_handler(CommandHandler("check", check_command))
        application.add_handler(CommandHandler("delete", delete_command))
        application.add_handler(CommandHandler("destination", destination_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
        application.add_handler(CallbackQueryHandler(button_handler))

        # Añadir manejador de errores
        application.add_error_handler(error_handler)

        # Iniciar el bot
        logger.info("Iniciando bot...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,  # Ignorar actualizaciones pendientes al iniciar
            close_loop=False  # No cerrar el loop al detener
        )
    except Exception as e:
        logger.error(f"Error al iniciar el bot: {e}")
        raise

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar errores del bot"""
    logger.error(f"Error en el bot: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Ha ocurrido un error inesperado.\n"
            "Por favor, intenta de nuevo más tarde."
        )

if __name__ == '__main__':
    main()