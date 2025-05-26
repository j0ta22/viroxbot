import os
from web3 import Web3
from dotenv import load_dotenv

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

def check_balances(private_key, token_address):
    """Verificar el balance de tokens en una wallet"""
    try:
        account = w3.eth.account.from_key(private_key)
        token_contract = w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        
        name = token_contract.functions.name().call()
        symbol = token_contract.functions.symbol().call()
        decimals = token_contract.functions.decimals().call()
        balance = token_contract.functions.balanceOf(account.address).call()
        readable_balance = balance / (10 ** decimals)
        
        return f"📍 {account.address}\n💰 {readable_balance:.4f} {symbol} ({name})"
    
    except Exception as e:
        return f"❌ Error al verificar balance: {str(e)}"

def transfer_tokens(private_key, token_address, destination):
    """Transferir tokens desde una wallet a la dirección de destino"""
    try:
        account = w3.eth.account.from_key(private_key)
        token_contract = w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        
        balance = token_contract.functions.balanceOf(account.address).call()
        decimals = token_contract.functions.decimals().call()
        readable_balance = balance / (10 ** decimals)
        
        if balance == 0:
            return f"📍 {account.address}\n❌ Sin tokens para transferir"
        
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
        
        return f"📍 {account.address}\n✅ Transferencia exitosa\n💰 {readable_balance:.4f} tokens\n🔗 Tx: {tx_hash.hex()}"
    
    except Exception as e:
        return f"❌ Error al transferir desde {account.address}: {str(e)}" 