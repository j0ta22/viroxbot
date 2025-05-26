# Virox Bot

Bot de Telegram para gestionar y transferir tokens ERC20 en la red Base.

## Características

- Gestión de múltiples wallets
- Verificación de balances de tokens
- Transferencia de tokens a una dirección de destino
- Almacenamiento seguro de claves privadas
- Interfaz intuitiva con botones

## Instalación

1. Clonar el repositorio:
```bash
git clone <url-del-repositorio>
cd Telegram
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
Crear un archivo `.env` con las siguientes variables:
```
TELEGRAM_TOKEN=tu_token_de_telegram
BASE_RPC_URL=https://mainnet.base.org
ENCRYPTION_KEY=tu_clave_de_encriptacion
LOGO_PATH=ruta/al/logo.png
DB_PATH=ruta/a/wallets.db
```

## Uso

1. Iniciar el bot:
```bash
python src/virox_telegram.py
```

2. En Telegram, usar los siguientes comandos:
- `/start` - Iniciar el bot y mostrar el menú de gestión
- `/help` - Mostrar ayuda
- `/check <dirección>` - Verificar balance de tokens
- `/transfer <dirección>` - Transferir tokens
- `/wallets` - Ver billeteras y balances en ETH

## Estructura del Proyecto

```
Telegram/
├── src/
│   └── virox_telegram.py
├── data/
│   └── wallets.db
├── assets/
│   └── logo.png
├── .env
├── requirements.txt
└── README.md
```

## Seguridad

- Las claves privadas se almacenan encriptadas en la base de datos
- Cada usuario tiene su propia clave de encriptación
- Las claves privadas nunca se muestran en los mensajes
- Se utiliza PBKDF2 con salt único por wallet

## Licencia

Este proyecto está bajo la Licencia MIT. 