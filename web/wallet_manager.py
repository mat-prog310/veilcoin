"""
Gestionnaire de wallets pour l'interface web
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.wallet import VeilWallet
from core.blockchain import Blockchain
from config import Config

class WalletManager:
    """Gestionnaire de wallets multiples"""
    
    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain
        self.wallets = {}
    
    def create_wallet(self, name: str) -> dict:
        """Crée un nouveau wallet"""
        if name in self.wallets:
            return {'error': 'Wallet déjà chargé'}
        
        wallet = VeilWallet(name)
        self.wallets[name] = wallet
        return wallet.get_info()
    
    def load_wallet(self, name: str) -> dict:
        """Charge un wallet existant"""
        try:
            wallet = VeilWallet(name)
            self.wallets[name] = wallet
            return wallet.get_info()
        except Exception as e:
            return {'error': str(e)}
    
    def get_wallet(self, name: str) -> VeilWallet:
        """Retourne un wallet par nom"""
        return self.wallets.get(name)
    
    def update_balances(self):
        """Met à jour tous les soldes"""
        for name, wallet in self.wallets.items():
            balance = self.blockchain.get_balance(wallet.address)
            wallet.balance = balance
            wallet.save()
    
    def get_all_info(self) -> list:
        """Retourne les infos de tous les wallets"""
        return [wallet.get_info() for wallet in self.wallets.values()]
    
    def list_available_wallets(self) -> list:
        """Liste les wallets disponibles"""
        wallets = []
        wallets_dir = Config.WALLETS_DIR
        
        if os.path.exists(wallets_dir):
            for file in os.listdir(wallets_dir):
                if file.endswith('.json'):
                    wallets.append(file.replace('.json', ''))
        
        return wallets
