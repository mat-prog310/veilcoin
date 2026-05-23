import hashlib
import os
import json
from typing import Tuple, List
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from .stealth_address import StealthAddress

class VeilWallet:
    """Wallet VeilCoin avec support des adresses furtives"""
    
    def __init__(self, wallet_name: str = "default"):
        self.wallet_name = wallet_name
        self.private_key: bytes = None
        self.public_key: bytes = None
        self.stealth_private_key: bytes = None
        self.stealth_public_key: bytes = None
        self.address: str = None
        
        # Charger ou créer le wallet
        self.load_or_create_wallet()
    
    def load_or_create_wallet(self) -> None:
        """Charge un wallet existant ou en crée un nouveau"""
        wallet_path = f"data/wallet_{self.wallet_name}.json"
        
        if os.path.exists(wallet_path):
            with open(wallet_path, 'r') as f:
                data = json.load(f)
                self.private_key = bytes.fromhex(data['private_key'])
                self.public_key = bytes.fromhex(data['public_key'])
                self.stealth_private_key = bytes.fromhex(data['stealth_private_key'])
                self.stealth_public_key = bytes.fromhex(data['stealth_public_key'])
                self.address = data['address']
            print(f"🔑 Wallet '{self.wallet_name}' chargé : {self.address[:16]}...")
        else:
            self.create_new_wallet()
    
    def create_new_wallet(self) -> None:
        """Crée un nouveau wallet avec adresse furtive"""
        # Génération des clés principales
        private_key = ec.generate_private_key(ec.SECP256K1())
        public_key = private_key.public_key()
        
        self.private_key = private_key.private_numbers().private_value.to_bytes(32, 'big')
        self.public_key = public_key.public_numbers().x.to_bytes(32, 'big')
        
        # Génération des clés pour les adresses furtives
        self.stealth_private_key, self.stealth_public_key = StealthAddress.generate_keypair()
        
        # Génération de l'adresse publique
        self.address = self.generate_address()
        
        # Sauvegarde
        self.save_wallet()
        print(f"✨ Nouveau wallet créé : {self.address[:16]}...")
    
    def generate_address(self) -> str:
        """Génère une adresse VeilCoin à partir de la clé publique"""
        hash1 = hashlib.sha3_256(self.public_key).digest()
        hash2 = hashlib.sha3_256(hash1).hexdigest()
        return f"V1{hash2[:40]}"  # Adresse de 42 caractères commençant par V1
    
    def save_wallet(self) -> None:
        """Sauvegarde le wallet"""
        wallet_data = {
            'private_key': self.private_key.hex(),
            'public_key': self.public_key.hex(),
            'stealth_private_key': self.stealth_private_key.hex(),
            'stealth_public_key': self.stealth_public_key.hex(),
            'address': self.address
        }
        
        os.makedirs('data', exist_ok=True)
        wallet_path = f"data/wallet_{self.wallet_name}.json"
        with open(wallet_path, 'w') as f:
            json.dump(wallet_data, f, indent=2)
    
    def sign_transaction(self, tx_data: dict) -> dict:
        """Signe une transaction avec la clé privée"""
        from cryptography.hazmat.primitives.asymmetric import utils
        from cryptography.hazmat.primitives import hashes
        
        # Reconstruction de la clé privée
        private_key = ec.derive_private_key(
            int.from_bytes(self.private_key, 'big'),
            ec.SECP256K1()
        )
        
        # Signature
        message = json.dumps(tx_data, sort_keys=True).encode()
        signature = private_key.sign(
            message,
            ec.ECDSA(hashes.SHA256())
        )
        
        tx_data['signature'] = signature.hex()
        return tx_data
    
    def get_public_key_hex(self) -> str:
        """Retourne la clé publique en hexadécimal"""
        return self.public_key.hex()
    
    def get_stealth_pubkey_hex(self) -> str:
        """Retourne la clé publique furtive en hexadécimal"""
        return self.stealth_public_key.hex()
