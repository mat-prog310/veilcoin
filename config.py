import os

class Config:
    COIN_NAME = "VeilCoin"
    SYMBOL = "VEIL"
    VERSION = "1.0.0"
    BLOCK_TIME = 120
    DIFFICULTY_ADJUSTMENT_INTERVAL = 10
    INITIAL_DIFFICULTY = 5
    MAX_SUPPLY = 1_000_000_000
    BASE_REWARD = 50
    HALVING_INTERVAL = 210_000
    P2P_PORT = 18444
    API_PORT = 5000
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # Utiliser le disque persistant si disponible
    DATA_DIR = os.environ.get('RENDER_DISK_PATH', os.path.join(BASE_DIR, "data"))
    BLOCKCHAIN_FILE = "blockchain.json"
    MEMPOOL_FILE = "mempool.json"
    SECRET_KEY = os.urandom(24).hex()
    DEBUG = False

    @classmethod
    def init_directories(cls):
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(cls.DATA_DIR, "wallets"), exist_ok=True)

Config.init_directories()
