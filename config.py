# Configuration de VeilCoin
class Config:
    # Identité du réseau
    COIN_NAME = "VeilCoin"
    SYMBOL = "VEIL"
    NETWORK_ID = b'\x12\x34\x56\x78'  # Magic bytes pour le réseau
    
    # Paramètres de minage
    BLOCK_TIME = 120  # secondes (2 minutes, plus rapide que Bitcoin)
    DIFFICULTY_ADJUSTMENT_INTERVAL = 10  # ajustement tous les 10 blocs
    INITIAL_DIFFICULTY = 100000
    MAX_SUPPLY = 21_000_000  # Comme Bitcoin, mais avec confidentialité
    
    # Récompenses de bloc (halving tous les 210 000 blocs)
    BASE_REWARD = 50  # Récompense initiale comme Bitcoin
    
    # Paramètres de confidentialité
    RING_SIZE = 11  # 1 vrai + 10 leurres (comme Monero par défaut)
    STEALTH_ADDRESS_PREFIX = b'\x36'  # Préfixe pour adresses furtives
    
    # Réseau
    P2P_PORT = 18444
    API_PORT = 18445
    
    # Chemins
    DATA_DIR = "data/"
    BLOCKCHAIN_FILE = "blockchain.json"
    MEMPOOL_FILE = "mempool.json"
